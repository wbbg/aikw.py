# Tag picture files with an AI 

Generate keywords, headline and title for files on your HDD without uploading anything to the Internet.

Original idea and starting code from [c't magazine](https://ct.de/y9ey)

## Programming Language

python3

## Prerequisites

a running AI model in [Ollama](https://ollama.com/)

## Installation

see [INSTALL.md](./INSTALL.md)

## Usage

start with 
```bash
$ cd <AIKW DIR>
$ source .venv/bin/activate
$ python3 ./aikw.py [...]
```

```
usage: aikw.py [-h] [-O server:port] [-M MODEL] [-f] [-o] [-p] [-kw KEYWORDS]
               [-t TEMPERATURE] [-L LOGFILE] [-r REGEX] [-v] [-m MIMETYPE]
               [-n] [-P FILE]
               FILE|DIR [FILE|DIR ...]

get descriptions and keywords for pictures from a locally running AI

positional arguments:
  FILE|DIR              files and/or directories to process

options:
  -h, --help            show this help message and exit
  -O, --ollama server:port
                        IPAddress and port for the AI [127.0.0.1:11434]
  -M, --model MODEL     ollama model [llava:v1.6]
  -f, --force           force retry on previously handled files [False]
  -o, --overwrite       don't create *_backup files [False]
  -p, --preserve
  -kw, --keywords KEYWORDS
                        number of keywords to generate [15]
  -t, --temperature TEMPERATURE
                        model temperature [0]
  -L, --logfile LOGFILE
                        logfile name []
  -r, --fileregex REGEX
                        filter file names by regex [.*]
  -v                    log level [0]
  -m, --mimetype MIMETYPE
                        filter files by file (partial) mimetype []
  -n, --dryrun          dryrun, don't ask the AI [False]
  -P, --prompts FILE    read prompts from JSON- file
```

- defaults in []
- currently all data is written to a json file (<input-filename>.<time>.ai.json)
- '-o', '-f' and '-p' have no function because aikw.py is currently not writing to metadata directly
- use generateReport.py to generate a PDF- file from *.ai.json files

## Examples 

- with verbosity 3 against local ai server for .jpg (case insensitive), files in subdir:
```bash
python3 ./aikw.py -vvv -r '(?i)\.jpg$' <subdir>:
```
- with verbosity 2 against remote ai server at 192.168.1.1:11434 for .ORF.xmp (case sensitive), files in subdir
```bash
python3 ./aikw.py -vv -O 192.168.1.1:11434 -r '\.ORF\.xmp$' <subdir>
```
- verbosity 2, remote ai server, mimetyp image/*, model gemma3 (you have to load it into the server, see [INSTALL.md](./INSTALL.md)), read prompts from [file](./prompts-gemma3.json)
```bash
python3 ./aikw.py -v 2 -O 192.168.1.1:11434 -m image -kw 10 -m gemma3 -P prompts-gemma3.json -t 0.5 <subdir>
```
- get help
```bash
python3 ./aikw.py --help
```

