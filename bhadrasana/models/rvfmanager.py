from ajna_commons.flask.log import logger
from bhadrasana.models import handle_datahora, ESomenteMesmoUsuario, \
    get_usuario_logado, gera_objeto
from bhadrasana.models.ovr import Marca, TipoEventoOVR, EventoEspecial
from bhadrasana.models.ovrmanager import get_ovr, gera_eventoovr
from bhadrasana.models.rvf import RVF, Infracao, ImagemRVF
from sqlalchemy import and_


def get_infracoes(session):
    infracoes = session.query(Infracao).all()
    return [infracao for infracao in infracoes]


def get_infracoes_choice(session):
    infracoes = session.query(Infracao).all()
    return [(infracao.id, infracao.nome) for infracao in infracoes]


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


def get_imagemrvf_or_none(session, rvf_id: str, _id: str):
    return session.query(ImagemRVF).filter(
        ImagemRVF.rvf_id == rvf_id).filter(
        ImagemRVF.imagem == _id).one_or_none()


def get_imagemrvf(session, rvf_id: str, _id: str):
    imagemrvf = session.query(ImagemRVF).filter(
        ImagemRVF.rvf_id == rvf_id).filter(
        ImagemRVF.imagem == _id).one_or_none()
    if imagemrvf is None:
        return ImagemRVF()


def cadastra_imagemrvf(session, params=None):
    imagemrvf = get_imagemrvf(session,
                              params.get('rvf_id'),
                              params.get('imagem'))
    if imagemrvf is not None:
        return gera_objeto(imagemrvf, session, params)
    return imagemrvf

def lista_rvfovr(session, ovr_id):
    try:
        ovr_id = int(ovr_id)
    except (ValueError, TypeError):
        return None
    return session.query(RVF).filter(RVF.ovr_id == ovr_id).all()


def cadastra_rvf(session,
                 user_name: str,
                 params: dict = None,
                 ovr_id: int = None):
    rvf = None
    if ovr_id:
        ovr = get_ovr(session, ovr_id)
        if not ovr:
            return None
        rvf = RVF()
        rvf.ovr_id = ovr.id
        rvf.numeroCEmercante = ovr.numeroCEmercante
    elif params:
        rvf = get_rvf(session, params.get('id'))
        usuario = get_usuario_logado(session, user_name)
        if rvf.user_name and rvf.user_name != usuario.cpf:
            raise ESomenteMesmoUsuario()
        for key, value in params.items():
            setattr(rvf, key, value)
        rvf.datahora = handle_datahora(params)
    if rvf is not None:
        try:
            if rvf.ovr_id is not None:
                tipoevento = session.query(TipoEventoOVR).filter(
                    TipoEventoOVR.eventoespecial == EventoEspecial.RVF.value).first()
                params = {'tipoevento_id': tipoevento.id,
                          'motivo': 'RVF %s' % rvf.id,
                          'user_name': rvf.user_name,
                          'ovr_id': rvf.ovr_id
                          }
                evento = gera_eventoovr(session, params, commit=False)
                session.add(evento)
            session.add(rvf)
            session.commit()
        except Exception as err:
            session.rollback()
            logger.error(err, exc_info=True)
            raise err
    return rvf


def gerencia_infracao_encontrada(session, rvf_id, infracao_id, inclui=True):
    rvf = session.query(RVF).filter(RVF.id == rvf_id).one_or_none()
    if rvf:
        infracao = session.query(Infracao).filter(
            Infracao.id == infracao_id).one_or_none()
        if infracao:
            if inclui:
                rvf.infracoesencontradas.append(infracao)
            else:
                rvf.infracoesencontradas.remove(infracao)
            session.commit()
            return rvf.infracoesencontradas
    return None


def inclui_infracao_encontrada(session, rvf_id, infracao_nome):
    infracao = session.query(Infracao).filter(
        Infracao.nome == infracao_nome).one_or_none()
    if infracao:
        return gerencia_infracao_encontrada(session, rvf_id,
                                            infracao.id,
                                            inclui=True)
    return None


def exclui_infracao_encontrada(session, rvf_id, infracao_id):
    return gerencia_infracao_encontrada(session, rvf_id, infracao_id, inclui=False)


def gerencia_marca_encontrada(session, rvf_id, marca_id, inclui=True):
    rvf = session.query(RVF).filter(RVF.id == rvf_id).one_or_none()
    if rvf:
        marca = session.query(Marca).filter(Marca.id == marca_id).one_or_none()
        if marca:
            if inclui:
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
