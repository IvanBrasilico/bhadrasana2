import io
from _md5 import md5

import fitz
from PIL import Image
from ajna_commons.flask.log import logger
from gridfs import GridFS

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


def insert_pagina(mongodb, image: Image,
                  numero_dta: str, filename: str, pagina: int):
    fs = GridFS(mongodb)
    content = io.BytesIO(image)
    m = md5()
    m.update(content)
    grid_out = fs.find_one({'md5': m.hexdigest()})
    if grid_out:
        if grid_out.filename == filename:
            logger.warning(
                ' Arquivo %s Pagina %s MD5 %s ' +
                ' tentativa de inserir pela segunda vez!!' %
                (filename, pagina, m.hexdigest())
            )
            # File exists, abort!
            return grid_out._id
    # Insert File
    params = {'numero_dta': numero_dta, 'pagina': pagina}
    return fs.put(content, filename=filename,
                  metadata=params)


def get_pagina(mongodb, numero_dta: str, filename: str, pagina: int):
    params = {'filename': filename,
              'numero_dta': numero_dta,
              'pagina': pagina}
    _id = mongodb.fs.files.find(params, {'_id': 1})
    fs = GridFS(mongodb)
    return fs.get(_id)

def processa_pdf(filename:str):
    for pagina in
