import os

import fitz

caminho = r'C:\Users\25052288840\Downloads\pdfs'

filelist = os.listdir(caminho)
for file in filelist:
    doc = fitz.open(os.path.join(caminho, file))
    for i, page in enumerate(doc):
        pix = page.get_pixmap()
        pix.writePNG('imgs/p%s-%s.png' % (file, i))
    """
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
    """
