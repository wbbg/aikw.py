import base64
import re
import os
import signal
import sys
import argparse
import http.client
from PIL import Image, ImageOps
from exiftool import ExifToolHelper
from langchain_ollama import OllamaLLM
from threading import Thread
from io import BytesIO
from time import time, sleep
import logging

OLLAMA_MODEL = "llava:v1.6"
KW_NUM = 15
FORCE_REGEN = False
ET_PARAMS = []
logger = logging.getLogger(__name__)
llm_timeout = 1800.0
llm_thread = None
llm_result = None


def getArgs():
    global args
    parser = argparse.ArgumentParser(prog="aikw.py",
                                     description="get descriptions and keywords for pictures from a locally running AI")
    parser.add_argument('filename', nargs='+')
    parser.add_argument('-O', '--ollama', dest='srv', action='append',
                        default=[], metavar=('server:port'), help='IPAddress and port for the AI [127.0.0.1:11434]')
    parser.add_argument('-f', '--force', action='store_true', help='force retry on previously handled files [False]')
    parser.add_argument('-o', '--overwrite', action='store_true', help='don\'t create *_backup files [%(default)s]')
    parser.add_argument('-p', '--preserve', action='store_true')
    parser.add_argument('-kw', '--keywords', type=int, default=15, help='number of keywords to generate [%(default)s]')
    parser.add_argument('-L', '--logfile', default='log', help='logfile name [%(default)s]')
    parser.add_argument('-r', '--fileregex', default=r'.*', help='filter file names by regex [%(default)s]')    # r'(?i).*\.orf\.xmp$'
    parser.add_argument('-v', action='count', default=0, help='log level [%(default)s]')
    parser.add_argument('-t', '--type', default="", help='filter file names by file type [%(default)s]')
    args = parser.parse_args()


def initApp():
    global logger, KW_NUM, FORCE_REGEN, ET_PARAMS, file_regex
    if len(args.logfile) > 0:
        logging.basicConfig(filename=args.logfile, level=logging.ERROR,
                            format='%(asctime)s %(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.ERROR,
                            format='%(levelname)s: %(message)s')
    if args.v == 0:
        pass
    elif args.v == 1:
        logger.setLevel(logging.WARNING)
    elif args.v == 2:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)
    logger.debug(f"Loglevel is {logger.level}")
    KW_NUM = args.keywords
    if args.force:
        FORCE_REGEN = True
        logger.info("Force regeneration")
    if args.overwrite:
        ET_PARAMS.append("-overwrite_original")
        logger.info("Overwrite original file")
    if args.preserve:
        ET_PARAMS.append("-P")
        logger.info("Preserve modification time")
    file_regex = re.compile(args.fileregex)


def getOllamaSrv(servers):
    for srv in servers:
        conn = http.client.HTTPConnection(srv, timeout=3)
        try:
            conn.request("GET", "/")
            res = conn.getresponse().read()
        except:               # Verbindungsfehler
            srv = ""
        else:  # Server ist erreichbar
            if res == b'Ollama is running':
                break
        finally:
            conn.close()
    if srv == "":
        return None
    else:
        return srv


def llmInvoke(ctx, prompt):
    global logger, llm_result
    logger.debug("Invoking LLM request...")
    llm_result = None
    try:
        llm_result = ctx.invoke(prompt)
        logger.debug(f"Received \"{llm_result}\" from LLM.")
    except Exception as e:
        logger.warning(f"Communication error with LLM: {e}")


def getImage(et, fname):
    basename, ext = os.path.splitext(fname)
    if ext.upper() == '.XMP':
        fname = basename
        _, ext = os.path.splitext(fname)
    if ext.upper() in ['.CR2', '.ORF']:
        imageBase64 = et.execute_json("-b", '-MakerNotes:PreviewImage',
                                      fname)[0]["MakerNotes:PreviewImage"][7:]
        img_data = BytesIO(base64.b64decode(imageBase64))
        image = Image.open(img_data)
    else:
        image = Image.open(fname)
    return image


def genMetaData(srv, filename):
    tagsToRead = ["IPTC:Writer-Editor"]
    global logger, KW_NUM, FORCE_REGEN, ET_PARAMS
    global llm_timeout, llm_thread, llm_context, llm_prompt, llm_result
    llm_inst = OllamaLLM(model=OLLAMA_MODEL, base_url="http://" + srv,
                         temperature=0)
    prompts = {
        "headline": "Your role is a editor of a photo magazine. Describe the subject and the overall mood of the image in a headline with less than 12 words.",
        "abstract": "Your role is a phptographer. Create a very precise summary about the image with less than 300 characters.",
        "keywords": f"Your role is a photographer. Find a list of {KW_NUM} comma seperated single keywords describing the image and the overall mood of the image"
    }
    responses = {}
    with ExifToolHelper() as et:
        try:
            image = getImage(et, filename)
        except Exception as e:
            logger.warning(f"Can't load {filename}: {str(e)}, skipping...")
            return False

        etags = et.get_tags(filename, tagsToRead)[0]
        if 'IPTC:Writer-Editor' in etags and etags['IPTC:Writer-Editor'] == "llava:v1.6":
            if FORCE_REGEN:
                logger.info(f"Processed {filename} before, regenerating...")
            else:
                logger.warning(f"Processed {filename} before, skipping...")
                return False

        logger.debug(f"getting image from {filename} ...")
        ImageOps.exif_transpose(image, in_place=True)
        # image.thumbnail((672, 672))
        image = ImageOps.fit(image, (672, 672))
        image_b64 = convert2Base64(image)

        llm_context = llm_inst.bind(images=[image_b64])
        for key, prompt in prompts.items():
            llm_thread = Thread(target=llmInvoke, args=[llm_context, prompt])
            llm_start = time()
            llm_thread.start()
            logger.info("Waiting for LLM to finish...")
            while llm_thread.is_alive():
                sleep(1)
                if time() - llm_start > llm_timeout:
                    logger.error("Timeout while waiting for LLM")
                    break
            if llm_thread.is_alive():
                # writeMetaData(filename, "", "", [])
                logger.error("LLM is not responding, killing thead...")
                signal.pthread_kill(llm_thread.ident, signal.SIGKILL)
                # os.kill(0, signal.SIGKILL)
            responses[key] = llm_result.strip()
            logger.info(f"{key}: {responses[key]}")
    return True


def convert2Base64(image):
    buffered = BytesIO()
    rgb_im = image.convert('RGB')
    rgb_im.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str


def writeMetaData(filename, headline, abstract, keywords):
    global OLLAMA_MODEL, ET_PARAMS
    # Headline: [ 'Iptc.Application2.Headline', 'Exif.Image.ImageDescription', 'Xmp.dc.title' ]
    # Abstract: [ 'Exif.Photo.UserComment', 'Iptc.Application2.Caption', 'Xmp.dc.description' ]
    # Keywords: [ 'Iptc.Application2.Keywords', 'Xmp.dc.subject' ]

    with ExifToolHelper() as et:
        et.set_tags(filename,
                    tags={"IPTC:Writer-Editor": OLLAMA_MODEL,
                          "IPTC:Headline": headline,
                          "EXIF:ImageDescription": headline,
                          "XMP-dc:Title": headline,
                          "IPTC:Caption-Abstract": abstract,
                          "EXIF:UserComment": abstract,
                          "XMP-dc:Description": abstract,
                          "IPTC:Keywords": keywords,
                          "XMP-dc:Subject": keywords
                          }, params=ET_PARAMS
                    )
    return


def filterFile(fname):
    global file_regex
    return file_regex.search(fname)


def workFiles(srv, flist):
    global logger
    for item in flist:
        logger.info("Processing %s", item)
        if os.path.isfile(item) and filterFile(item):
            s = getOllamaSrv(srv)
            if s is None:
                logger.critical("No ollama server found.")
                sys.exit(1)
            else:
                logger.info(f"Using Ollama server {s}")
                genMetaData(s, item)
        elif os.path.isdir(item):
            if os.path.isfile(item + "/.notag"):
                logger.warning("Skipping %s as requested by .notag file", item)
                continue
            workFiles(srv, map(lambda i: os.path.join(os.path.abspath(item), i), os.listdir(item)))
        else:
            logger.info(f"Skipping {item}")


def main():
    global file_regex
    getArgs()
    initApp()
    if len(args.srv) > 0:
        workFiles(args.srv, args.filename)
    else:
        workFiles(["127.0.0.1:11434"], args.filename)


if __name__ == "__main__":
    main()

