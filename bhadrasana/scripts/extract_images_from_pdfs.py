import os

import fitz

filelist = os.listdir('pdfs')
for file in filelist:
    doc = fitz.open(os.path.join('pdfs', file))
    for i in range(len(doc)):
        for img in doc.getPageImageList(i):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            if pix.n < 5:  # this is GRAY or RGB
                pix.writePNG('imgs/p%s-%s.png' % (i, xref))
            else:  # CMYK: convert to RGB first
                pix1 = fitz.Pixmap(fitz.csRGB, pix)
                pix1.writePNG('imgs/p%s-%s.png' % (i, xref))
                pix1 = None
            pix = None
