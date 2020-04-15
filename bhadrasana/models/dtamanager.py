import io
from _md5 import md5

import fitz
from PIL import Image
from gridfs import GridFS
from pymongo import MongoClient

import sys
sys.path.insert(0, '../ajna_docs/commons')
from ajna_commons.flask.log import logger

from bhadrasana.models.dta import Anexo


def edita_anexo(session, params):
    anexo = session.query(Anexo).filter(Anexo.id == params['id']).one()
    return gera_objeto(anexo,
                       session, params)


def lista_anexos(session, dta_id):
    try:
        dta_id = int(dta_id)
    except (ValueError, TypeError):
        return None
    return session.query(Anexo).filter(Anexo.dta_id == dta_id).all()


def get_anexo(session, id: int = None):
    if id is None or id == 'None':
        anexo = Anexo()
        return anexo
    return session.query(Anexo).filter(Anexo.id == id).one_or_none()


def gera_objeto(object, session, params):
    for key, value in params.items():
        if value and value != 'None':
            setattr(object, key, value)
    try:
        session.add(object)
        session.commit()
    except Exception as err:
        session.rollback()
        raise err
    return object


def insert_pagina(mongodb, png_image: bytes,
                  numero_dta: str, filename: str, npagina: int):
    fs = GridFS(mongodb)
    content = png_image
    m = md5()
    m.update(content)
    grid_out = fs.find_one({'md5': m.hexdigest()})
    if grid_out:
        if grid_out.filename == filename:
            logger.warning(
                ' Arquivo %s Pagina %s MD5 %s ' +
                ' tentativa de inserir pela segunda vez!!' %
                (filename, npagina, m.hexdigest())
            )
            # File exists, abort!
            return grid_out._id
    # Insert File
    params = {'numero_dta': numero_dta, 'pagina': npagina}
    return fs.put(content, filename=filename,
                  metadata=params)


def get_npaginas(mongodb, numero_dta: str, filename: str, npagina: int):
    params = {'filename': filename,
              'numero_dta': numero_dta}
    return mongodb.fs.files.count_documents(params)

def get_pagina(mongodb, numero_dta: str, filename: str, npagina: int):
    params = {'filename': filename,
              'numero_dta': numero_dta,
              'pagina': npagina}
    _id = mongodb.fs.files.find(params, {'_id': 1})
    if _id is None:
        raise KeyError('Página não encontrada com os parâmetros: ' % params)
    fs = GridFS(mongodb)
    return Image.open(fs.get(_id))

def processa_pdf(mongodb, numero_dta: str, filename: str):
    pdf = fitz.open(filename)
    for npagina, page in enumerate(pdf, 1):
        pix = page.getPixmap()
        insert_pagina(mongodb, pix.getPNGData(),
                      numero_dta, filename, npagina)
    return npagina



if __name__ == '__main__':
    filename = 'C:/Users/25052288840/Downloads/MapearUnidadeN.pdf'
    mongodb = MongoClient('10.68.64.10')
    conn = mongodb['transito']
    npaginas = processa_pdf(conn, '1234', filename)
    npaginas = get_npaginas(conn, '1234', filename)
    for i in range(1, npaginas + 1):
        image = get_pagina(conn, '1234', filename, i)
        image.save('%s.png' % i)