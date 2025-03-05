import os
from exiftool import ExifToolHelper
import json
import sys
from pprint import pprint

exifFilter = """
    {
      "XMP:Rating": [4, 5], 
      "XMP:Colorlabels": [3]
    }
"""

def checkExifFilter(etags, filter):
    inList = True
    for k, v in filter.items():
        if k in etags:
            if not (etags[k] in v):
                inList=False
                break
        else:
            inList=False
            break
    return inList

def filterFileList (fileList, filter):
    filteredList = []
    with ExifToolHelper() as et:
        for fname in fileList:
            etags = et.get_metadata(fname)[0]
            if checkExifFilter(etags, filter):
                filteredList.append(fname)
    return filteredList

def main ():
    filter = json.loads(exifFilter)
    fileList = sys.argv[1:]
    pprint( filterFileList(fileList, filter))

if __name__ == "__main__":
    main()

