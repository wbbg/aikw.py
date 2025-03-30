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
# import pylibmagic
import magic
import datetime
import socket
import json

import dataWriter

OLLAMA_MODEL = "llava:v1.6"
KW_NUM = 10
FORCE_REGEN = False
ET_PARAMS = []
logger = logging.getLogger(__name__)
llm_timeout = 1800.0
llm_thread = None
llm_result = None
hostname = socket.gethostname()

prompts = {
    "headline": "Your role is a senior editor of a photo magazine. Describe the subject and the overall mood of the image in a headline with less than 12 words.",
    "abstract": "Your role is a travel phptographer. Create a very precise summary about the image with less than 400 characters.",
    "keywords": f"Your role is a photographer. Find a list of {KW_NUM} comma seperated single keywords describing the image and the overall mood of the image"
}


def getArgs():
    global args
    parser = argparse.ArgumentParser(prog="aikw.py",
                                     description="get descriptions and keywords for pictures from a locally running AI")
    parser.add_argument('filename', nargs='+')
    parser.add_argument('-O', '--ollama', dest='srv', action='append',
                        default=[], metavar=('server:port'),
                        help='IPAddress and port for the AI [127.0.0.1:11434]')
    parser.add_argument('-M', '--model', default=OLLAMA_MODEL,
                        help='ollama model [%(default)s')
    parser.add_argument('-f', '--force', action='store_true',
                        help='force retry on previously handled files [False]')
    parser.add_argument('-o', '--overwrite', action='store_true',
                        help='don\'t create *_backup files [%(default)s]')
    parser.add_argument('-p', '--preserve', action='store_true')
    parser.add_argument('-kw', '--keywords', type=int, default=15,
                        help='number of keywords to generate [%(default)s]')
    parser.add_argument('-t', '--temperature', type=float, default=0,
                        help='model temperature [%(default)s]')
    parser.add_argument('-L', '--logfile', default='log',
                        help='logfile name [%(default)s]')
    parser.add_argument('-r', '--fileregex', default=r'.*', metavar='REGEX',
                        help='filter file names by regex [%(default)s]')    # r'(?i).*\.orf\.xmp$'
    parser.add_argument('-v', action='count', default=0,
                        help='log level [%(default)s]')
    parser.add_argument('-m', '--mimetype', default="",
                        help='filter files by file (partial) mimetype [%(default)s]')
    parser.add_argument('-n', '--dryrun', action='store_true',
                        help='dryrun, don\'t ask the AI [%(default)s]')
    parser.add_argument('-P', '--prompts', default="", metavar='FILE',
                        help='read prompts from JSON- file')
    args = parser.parse_args()


def initApp():
    global logger, prompts, KW_NUM, FORCE_REGEN, ET_PARAMS, file_regex
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
    if args.prompts:
        try:
            with open(args.prompts) as pf:
                prompts = json.load(pf)
            for k in prompts:
                prompts[k] = prompts[k] % {'KW_NUM': KW_NUM}
        except Exception as e:
            logger.critical('ERROR reading prompts: {}'.format(e))
            sys.exit(2)
    file_regex = re.compile(args.fileregex)


def getOllamaSrv(servers: [str]) -> str:
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


def fixOrientation(et, img: Image, fname) -> Image:
    oTag = 'EXIF:Orientation'
    res = et.execute_json('-' + oTag, "-n", fname)[0]
    if oTag in res:
        match res[oTag]:
            case 2:
                image = img.transpose(Image.FLIP_LEFT_RIGHT)
            case 3:
                image = img.transpose(Image.ROTATE_180)
            case 4:
                image = img.transpose(Image.FLIP_TOP_BOTTOM)
            case 5:
                image = img.transpose(Image.TRANSPOSE)
            case 6:
                image = img.transpose(Image.ROTATE_270)
            case 7:
                image = img.transpose(Image.TRANSVERSE)
            case 8:
                image = img.transpose(Image.ROTATE_90)
            case _:
                image = img
    else:
        image = img
    return image


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
    return fixOrientation(et, image, fname)


def getAiHost(srv: str) -> str:
    try:
        return socket.gethostbyaddr(srv.split(':')[0])[0]
    except:
        return srv


def genMetaData(srv: str, filename: str, prompts: {}) -> {}:
    tagsToRead = ["IPTC:Writer-Editor"]
    global logger, KW_NUM, FORCE_REGEN, ET_PARAMS
    global llm_timeout, llm_thread, llm_context, llm_prompt, llm_result
    llm_inst = OllamaLLM(model=args.model, base_url="http://" + srv,
                         temperature=args.temperature)
    data = {
        'filename': filename,
        'image_b64': "",
        'model': args.model,
        'temp': args.temperature,
        'host': hostname,
        'when': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
        'aihost': getAiHost(srv),
    }

    with ExifToolHelper() as et:
        try:
            image = getImage(et, filename)
        except Exception as e:
            logger.warning(f"Can't load {filename}: {str(e)}, skipping...")
            return None

        etags = et.get_tags(filename, tagsToRead)[0]
        if 'IPTC:Writer-Editor' in etags and etags['IPTC:Writer-Editor'] == "llava:v1.6":
            if FORCE_REGEN:
                logger.info(f"Processed {filename} before, regenerating...")
            else:
                logger.warning(f"Processed {filename} before, skipping...")
                return None

        logger.debug(f"getting image from {filename} ...")
        # ImageOps.exif_transpose(image, in_place=True)
        # image.thumbnail((672, 672))
        image = ImageOps.fit(image, (672, 672))
        image_b64 = convert2Base64(image)
        data['image_b64'] = image_b64
        if not args.dryrun:
            llm_context = llm_inst.bind(images=[image_b64])
            for key, prompt in sorted(prompts.items()):
                response = {}

                llm_thread = Thread(target=llmInvoke, args=[llm_context, prompt])
                llm_start = time()
                llm_thread.start()
                logger.info(f"Waiting for LLM to finish {key}...")
                while llm_thread.is_alive():
                    sleep(1)
                    if time() - llm_start > llm_timeout:
                        logger.error("Timeout while waiting for LLM")
                        break
                if llm_thread.is_alive():
                    logger.error("LLM is not responding, killing thead...")
                    signal.pthread_kill(llm_thread.ident, signal.SIGKILL)
                    # os.kill(0, signal.SIGKILL)
                data[key] = {
                    'result': llm_result.strip(),
                    'prompt': prompt,
                    'time': time() - llm_start
                }
                logger.debug(f"{key}: {data[key]['result']}")
        else:
            logger.info("dryrun: AI not consulted")
    return data


def convert2Base64(image: Image) -> str:
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

    if not args.dryrun:
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
    else:
        logger.info("dryrun: no data written to file")
    return


def filterMagic(fname: str) -> bool:
    """test if args.mimetype is contained in fname's mimetype

    i.e.: fname's mimetype is image/jpeg, args.mimetype is image --> True
    """
    if args.mimetype:
        ftype = magic.from_file(fname, mime=True)
        mimetest = re.search(args.mimetype.upper(), ftype.upper())
        logger.debug(f'{fname}: mime type {ftype}, test result: {mimetest}')
        return bool(mimetest)
    else:
        return True


def filterRegex(fname: str) -> bool:
    """ test if args.regex matches fname"""
    global file_regex
    return file_regex.search(fname)


def workFiles(srv, flist):
    global logger
    data = {}
    for item in flist:
        logger.info("Processing %s", item)
        if os.path.isfile(item) and filterRegex(item) and filterMagic(item):

            server = getOllamaSrv(srv)
            if server is None:
                if args.dryrun:
                    logger.warning("No ollama server found.")
                    continue    # for item
                else:
                    logger.critical("No ollama server found.")
                    sys.exit(1)
            else:
                logger.info(f"Using Ollama server {server}")
                data = genMetaData(server, item, prompts)
                jsonFName = item + "." + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '.ai.json'
                logger.info(f'writing JSON to {jsonFName}')
                dataWriter.JsonWriter(data, {'filename': jsonFName}).write()
        elif os.path.isdir(item):
            if os.path.isfile(item + "/.notag"):
                logger.warning("Skipping %s as requested by .notag file", item)
                continue    # for item
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

