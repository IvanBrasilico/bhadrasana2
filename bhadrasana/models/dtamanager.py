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
