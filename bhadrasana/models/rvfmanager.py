from bhadrasana.models.ovrmanager import get_ovr
from bhadrasana.models.rvf import Marca, RVF
from bhadrasana.models import handle_datahora
from sqlalchemy import and_


def get_marcas(session):
    marcas = session.query(Marca).all()
    return [marca for marca in marcas]

def get_marcas_choice(session):
    marcas = session.query(Marca).all()
    return [(marca.id, marca.nome) for marca in marcas]


def get_rvfs_filtro(session, pfiltro):
    filtro = and_()
    if pfiltro.get('datainicio'):
        filtro = and_(RVF.datahora >= pfiltro.get('datainicio'))
    rvfs = session.query(RVF).filter(filtro).all()
    return [rvf for rvf in rvfs]


def get_rvf(session, id=None):
    if id is None:
        return RVF()
    return session.query(RVF).filter(RVF.id == id).one_or_none()


def get_rvf_ovr(session, ovr_id):
    return session.query(RVF).filter(RVF.ovr_id == ovr_id).one_or_none()


def cadastra_rvf(session, params=None,
                 ovr_id=None):
    if ovr_id:
        ovr = get_ovr(session, ovr_id)
        if not ovr:
            return None
        rvf = RVF()
        rvf.ovr_id = ovr.id
        rvf.numeroCEmercante = ovr.numeroCEmercante
        print(ovr.id, ovr.numeroCEmercante)
    elif params:
        rvf = get_rvf(session, params.get('id'))
        for key, value in params.items():
            setattr(rvf, key, value)
        rvf.datahora = handle_datahora(params)
    if rvf is not None:
        try:
            session.add(rvf)
            session.commit()
            print(rvf)
        except Exception as err:
            session.rollback()
            raise err
            print(rvf)
    return rvf


def gerencia_marca_encontrada(session, rvf_id, marca_id, inclui=True):
    rvf = session.query(RVF).filter(RVF.id == rvf_id).one_or_none()
    if rvf:
        marca = session.query(Marca).filter(Marca.id == marca_id).one_or_none()
        if marca:
            if inclui:
                print('Incluindo MARCA...', marca)
                rvf.marcasencontradas.append(marca)
            else:
                rvf.marcasencontradas.remove(marca)
            session.commit()
            return rvf.marcasencontradas
    return None


def inclui_marca_encontrada(session, rvf_id, marca_nome):
    marca = session.query(Marca).filter(Marca.nome == marca_nome).one_or_none()
    if marca:
        return gerencia_marca_encontrada(session, rvf_id, marca.id, inclui=True)
    return None


def exclui_marca_encontrada(session, rvf_id, marca_id):
    return gerencia_marca_encontrada(session, rvf_id, marca_id, inclui=False)


def get_ids_anexos(db, rvf):
    filtro = {'metadata.rvf_id': str(rvf.id)}
    count = db['fs.files'].count_documents(filtro)
    result = [str(row['_id']) for row in db['fs.files'].find(filtro)]
    print(filtro, result, count)
    return result
