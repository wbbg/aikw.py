from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus.flowables import BalancedColumns

import json
import base64
import argparse
from io import BytesIO
# from pprint import pp


def getArgs():
    global args
    parser = argparse.ArgumentParser(prog="generateReport.py",
                                     description="generate a PDF from *.ai.json files")
    parser.add_argument('filename', nargs='+')
    parser.add_argument('-o', '--outfile', default='aikw.pdf',
                        help='output file name [%(default)s]')
    args = parser.parse_args()


def getData(fName: str) -> {}:
    with open(fName, "r") as f:
        jData = json.load(f)
    return jData


def getImage(data: {}) -> Image:
    img_bytes = BytesIO(base64.b64decode(data['image_b64']))
    return Image(img_bytes,
                 width=7 * cm,
                 height=7 * cm,
                 kind='bound'
                 )


def formatResult(data: {}) -> str:
    return '{} [{:.1f}sec]'.format(data['result'], data['time'])


def getDataStr(data: {}, key: str) -> str:
    if key in data:
        return data[key]
    else:
        return ""


def create_document():
    global args
    doc = SimpleDocTemplate(
        args.outfile,
        pagesize=A4
    )
    styles = getSampleStyleSheet()
    flowables = []
    for f in sorted(args.filename):
        data = getData(f)
        img = getImage(data)
        flowables.extend([
            Paragraph(getDataStr(data, 'filename'),
                      styles['Code']),
            Paragraph(formatResult(getDataStr(data, 'headline')), styles['Heading3']),
            BalancedColumns([img, Paragraph(formatResult(data['abstract']),
                                            styles['Normal'])
                             ]),
            Spacer(0.5 * cm, 0.5 * cm),
            Paragraph(formatResult(data['keywords'])),
            Paragraph("Model <strong>{}</strong> (temp: {}) on {}, script runing on {}".format(
                                        getDataStr(data, 'model'),
                                        getDataStr(data, 'temp'),
                                        getDataStr(data, 'aihost'),
                                        getDataStr(data, 'host')
                                        ), 
                      styles['Italic']),
            Paragraph(getDataStr(data, 'when'), styles['Normal']),
            Paragraph("Prompts: ", styles['Heading5']),
        ])
        for k in ['headline', 'abstract', 'keywords']:
            flowables.extend([
                Paragraph(k, styles['Heading6']),
                Paragraph(data[k]['prompt'], styles['Definition'])
            ])
        flowables.append(PageBreak())
    doc.build(flowables)


if __name__ == '__main__':
    getArgs()
    create_document()
