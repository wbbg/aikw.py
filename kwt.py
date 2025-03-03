import base64
import glob
import os
import signal
import sys
import argparse
import http.client
from io import BytesIO
from PIL import Image, ImageOps
from exiftool import ExifToolHelper
from langchain_ollama import OllamaLLM
from threading import Thread
from time import time, sleep
import logging

OLLAMA_MODEL = "llava:v1.6"
KW_NUM = 15
FORCE_REGEN = False
ET_PARAMS = [ ]
logger = logging.getLogger(__name__)
llm_timeout = 1800.0
llm_thread = None
llm_result = None

def getOllamaSrv(servers):
    for srv in servers:
        conn = http.client.HTTPConnection(srv, timeout=3)
        try:
            conn.request("GET", "/")
            res = conn.getresponse().read()
        except: # Verbindungsfehler
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
    logger.info("Invoking LLM request...")
    llm_result = None
    try:
        llm_result = ctx.invoke(prompt)
        logger.info(f"Received \"{llm_result}\" from LLM.")
    except:
        logger.warning(f"Communication error with LLM.")

def genMetaData(srv, filename):
    global logger, KW_NUM, FORCE_REGEN, ET_PARAMS
    global llm_timeout, llm_thread, llm_context, llm_prompt, llm_result
    llm_inst = OllamaLLM(model=OLLAMA_MODEL, base_url="http://"+srv, temperature=0)
    prompt_headline = "Your role is a newspaper editor. Describe the subject of the image in a headline with less than 8 words."
    prompt_abstract = "Your role is a phptographer. Create a very precise summary about the image with less than 300 characters."
    prompt_keywords = f"Your role is a photographer. Find {KW_NUM} single keywords describing the image."

    try:
        image = Image.open(filename)
    except:
        logger.warning(f"Can't load {filename}, skipping...")
        return False

    if image.format != 'JPEG':
        logger.info(f"{filename} is no JPEG, skipping...")
        return False

    with ExifToolHelper() as et:
        etags = et.get_metadata(filename)[0]
        for k, v in etags.items():
            logger.debug(f"METADATA: {k} = {v}")
        if 'IPTC:Writer-Editor' in etags and etags['IPTC:Writer-Editor'] == "llava:v1.6":
            if FORCE_REGEN == True:
                logger.info(f"Processed {filename} before, regenerating...")
            else:
                logger.warning(f"Processed {filename} before, skipping...")
                return False

    logger.info(f"Processing image {filename} ...")
    ImageOps.exif_transpose(image, in_place=True)
    image.thumbnail((672, 672))
    image_b64 = convert2Base64(image)

    llm_context = llm_inst.bind(images=[image_b64])

    llm_thread = Thread(target=llmInvoke, args=[llm_context, prompt_headline])
    llm_start  = time()
    llm_thread.start()
    while llm_thread.is_alive():
        logger.info("Waiting for LLM to finish...")
        sleep(1)
        if time() - llm_start > llm_timeout:
            logger.error("Timeout while waiting for LLM")
            break
    if llm_thread.is_alive():
        writeMetaData(filename, "", "", [])
        logger.error("LLM is not responding, killing thead...")
        signal.pthread_kill(llm_thread.ident, signal.SIGKILL)
        #os.kill(0, signal.SIGKILL)
    headline = llm_result.strip()
    logger.info(f"Headline: {headline}")

    llm_thread = Thread(target=llmInvoke, args=[llm_context, prompt_abstract], name="llmInvoke")
    llm_start  = time()
    llm_thread.start()
    while llm_thread.is_alive():
        logger.info("Waiting for LLM to finish...")
        sleep(1)
        if time() - llm_start > llm_timeout:
            logger.error("Timeout while waiting for LLM")
            break
    if llm_thread.is_alive():
        writeMetaData(filename, headline, "", [])
        logger.error("LLM is not responding, killing thead...")
        signal.pthread_kill(llm_thread.ident, signal.SIGKILL)
        #os.kill(0, signal.SIGKILL)
    abstract = llm_result.strip()
    logger.info(f"Abstract: {abstract}")

    llm_thread = Thread(target=llmInvoke, args=[llm_context, prompt_keywords], name="llmInvoke")
    llm_start  = time()
    llm_thread.start()
    while llm_thread.is_alive():
        logger.info("Waiting for LLM to finish...")
        sleep(1)
        if time() - llm_start > llm_timeout:
            logger.error("Timeout while waiting for LLM")
            break

    if llm_thread.is_alive():
        writeMetaData(filename, headline, abstract, [])
        logger.error("LLM is not responding, killing thead...")
        signal.pthread_kill(llm_thread.ident, signal.SIGKILL)
        #os.kill(0, signal.SIGKILL)
    else:
        keywords = llm_result.splitlines()
        keywords = [k.lstrip('0123456789. ') for k in keywords]
        logger.info(f"Keywords: {keywords}")
        writeMetaData(filename, headline, abstract, keywords)
    return True

def writeMetaData(filename, headline, abstract, keywords):
    global OLLAMA_MODEL, ET_PARAMS
    # Headline: [ 'Iptc.Application2.Headline', 'Exif.Image.ImageDescription', 'Xmp.dc.title' ]
    # Abstract: [ 'Exif.Photo.UserComment', 'Iptc.Application2.Caption', 'Xmp.dc.description' ]
    # Keywords: [ 'Iptc.Application2.Keywords', 'Xmp.dc.subject' ]

    with ExifToolHelper() as et:
    	et.set_tags(filename, 
    	    tags = { "IPTC:Writer-Editor": OLLAMA_MODEL,
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

def workFiles(srv, pattern):
    global logger
    
    for item in pattern:
        logger.info("Processing %s", item)
        if os.path.isfile(item):
            s = getOllamaSrv(srv)
            if s is None:
                logger.critical("No ollama server found.")
                sys.exit(1)
            else:
                logger.info(f"Using Ollama server {s}")
                genMetaData(s, item)
        elif os.path.isdir(item):
            if os.path.isfile(item+"/.notag"):
                logger.warning("Skipping %s as requested by .notag file", item)
                continue
            workFiles(srv, glob.glob(f"{item}/*"))
        else:
            workFiles(srv, glob.glob(f"{item}"))

def convert2Base64(image):
    buffered = BytesIO()
    rgb_im = image.convert('RGB')
    rgb_im.save(buffered, format="JPEG") 
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

def main():
    global logger, KW_NUM, FORCE_REGEN, ET_PARAMS
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', nargs='+')
    parser.add_argument('-O', '--ollama', dest='srv', action='append', default=[ ], metavar=('server:port'))
    parser.add_argument('-f', '--force', action='store_true')
    parser.add_argument('-o', '--overwrite', action='store_true')
    parser.add_argument('-p', '--preserve', action='store_true')
    parser.add_argument('-kw', '--keywords', type=int, default=15)
    parser.add_argument('-L', '--logfile', default='log')
    parser.add_argument('-v', action='count', default=0)
    args = parser.parse_args()

    if len(args.logfile) > 0:
        logging.basicConfig(filename=args.logfile, level=logging.ERROR, format='%(asctime)s %(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')

    if args.v == 0:
        pass
    elif args.v == 1:
        logger.setLevel(logging.WARNING)
    elif args.v == 2:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)

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

    if len(args.srv) > 0:
        workFiles(args.srv, args.filename)
    else:
        workFiles(["127.0.0.1:11434"], args.filename)

if __name__ == "__main__":
    main()

