from typing import Callable, List

from bson import ObjectId
from gridfs import GridFS, NoFile
from sqlalchemy import and_

from ajna_commons.flask.log import logger
from ajna_commons.models.bsonimage import BsonImage
from bhadrasana.models import handle_datahora, ESomenteMesmoUsuario, \
    get_usuario_logado, gera_objeto
from bhadrasana.models.ovr import Marca, TipoEventoOVR, EventoEspecial, OVR
from bhadrasana.models.ovrmanager import get_ovr, gera_eventoovr
from bhadrasana.models.rvf import RVF, Infracao, ImagemRVF, Lacre


def get_infracoes(session):
    infracoes = session.query(Infracao).all()
    return [infracao for infracao in infracoes]


def get_infracoes_choice(session):
    infracoes = session.query(Infracao).all()
    return [(infracao.id, infracao.nome) for infracao in infracoes]


def get_rvfs_filtro(session, pfiltro):
    filtro = and_()
    if pfiltro.get('numeroCEmercante'):
        filtro = and_(RVF.numeroCEmercante.ilike(
            pfiltro.get('numeroCEmercante') + '%'), filtro)
    if pfiltro.get('numerolote'):
        filtro = and_(RVF.numerolote.ilike(
            pfiltro.get('numerolote') + '%'), filtro)
    if pfiltro.get('datainicio'):
        filtro = and_(RVF.datahora >= pfiltro.get('datainicio'), filtro)
    rvfs = session.query(RVF).filter(filtro).all()
    return [rvf for rvf in rvfs]


def get_rvf(session, rvf_id: int = None) -> RVF:
    if rvf_id is None:
        return RVF()
    return session.query(RVF).filter(RVF.id == rvf_id).one_or_none()


def get_imagemrvf_or_none(session, rvf_id: int, _id: str):
    return session.query(ImagemRVF).filter(
        ImagemRVF.rvf_id == rvf_id).filter(
        ImagemRVF.imagem == _id).one_or_none()


def lista_rvfovr(session, ovr_id: int) -> List[RVF]:
    try:
        ovr_id = int(ovr_id)
    except (ValueError, TypeError):
        return None
    return session.query(RVF).filter(RVF.ovr_id == ovr_id).all()


def gera_evento_rvf(session, rvf):
    tipoevento = session.query(TipoEventoOVR).filter(
        TipoEventoOVR.eventoespecial == EventoEspecial.RVF.value).first()
    params = {'tipoevento_id': tipoevento.id,
              'motivo': 'RVF %s' % rvf.id,
              'user_name': rvf.user_name,
              'ovr_id': rvf.ovr_id
              }
    evento = gera_eventoovr(session, params, commit=False)
    session.add(evento)
    return evento


def cadastra_rvf(session,
                 user_name: str,
                 params: dict = None,
                 ovr_id: int = None) -> RVF:
    rvf = None
    if ovr_id:
        ovr = get_ovr(session, ovr_id)
        if not ovr:
            return None
        rvf = cadastra_rvf(session, user_name,
                           {'ovr_id': ovr.id,
                            'numeroCEmercante': ovr.numeroCEmercante}
                           )
        session.refresh(rvf)
        gera_evento_rvf(session, rvf)
    elif params:
        rvf = get_rvf(session, params.get('id'))
        usuario = get_usuario_logado(session, user_name)
        if rvf.user_name and rvf.user_name != usuario.cpf:
            ovr = get_ovr(session, rvf.ovr_id)
            if ovr.responsavel_cpf != usuario.cpf:
                raise ESomenteMesmoUsuario()
        if not rvf.user_name:  # RVF criada agora ou programada por outro usuário
            rvf.user_name = usuario.cpf
        for key, value in params.items():
            setattr(rvf, key, value)
        rvf.datahora = handle_datahora(params)
    if rvf is not None:
        try:
            session.add(rvf)
            session.commit()
        except Exception as err:
            session.rollback()
            logger.error(err, exc_info=True)
            raise err
    return rvf


def programa_rvf_container(mongodb, mongodb_risco, session,
                           ovr: OVR, container: str, id_imagem: str) -> RVF:
    rvf = RVF()
    rvf.ovr_id = ovr.id
    rvf.numeroCEmercante = ovr.numeroCEmercante
    rvf.numerolote = container
    try:
        session.add(rvf)
        session.commit()
        session.refresh(rvf)
    except Exception as err:
        session.rollback()
        logger.error(err, exc_info=True)
        raise err
    # copia imagem do Banco virasana para bhadrasana e gera objeto ImagemRVF
    fs = GridFS(mongodb)
    try:
        grid_out = fs.get(ObjectId(id_imagem))
        inclui_imagemrvf(mongodb_risco, session, grid_out.read(),
                         grid_out.filename, rvf.id)
    except NoFile as err:
        logger.error(err)
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


def gerencia_lacre_verificado(session, rvf_id, lacre_id, inclui=True):
    rvf = session.query(RVF).filter(RVF.id == rvf_id).one_or_none()
    if rvf:
        lacre = session.query(Lacre).filter(
            Lacre.id == lacre_id).one_or_none()
        if lacre:
            if inclui:
                if lacre not in rvf.lacresverificados:
                    rvf.lacresverificados.append(lacre)
            else:
                rvf.lacresverificados.remove(lacre)
            session.commit()
            return rvf.lacresverificados
    return None


def inclui_lacre_verificado(session, rvf_id, lacre_numero):
    lacre = session.query(Lacre).filter(
        Lacre.numero == lacre_numero).one_or_none()
    if not lacre:
        lacre = Lacre()
        lacre.numero = lacre_numero
        session.add(lacre)
        session.commit()
    return gerencia_lacre_verificado(session, rvf_id,
                                     lacre.id,
                                     inclui=True)


def exclui_lacre_verificado(session, rvf_id, lacre_id):
    return gerencia_lacre_verificado(session, rvf_id, lacre_id, inclui=False)


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


def get_imagemrvf(session, rvf_id: int, _id: str):
    imagemrvf = session.query(ImagemRVF).filter(
        ImagemRVF.rvf_id == rvf_id).filter(
        ImagemRVF.imagem == _id).one_or_none()
    if imagemrvf is None:
        return ImagemRVF()
    return imagemrvf


def get_imagemrvf_ordem_or_none(session, rvf_id: int, ordem: int):
    return session.query(ImagemRVF).filter(
        ImagemRVF.rvf_id == rvf_id).filter(
        ImagemRVF.ordem == ordem).one_or_none()


def get_imagemrvf_imagem_or_none(session, _id: str):
    return session.query(ImagemRVF).filter(
        ImagemRVF.imagem == _id).one_or_none()


def swap_ordem(session, imagem_rvf: ImagemRVF, ordem_nova: int):
    """ Quando editar campo ordem, se existir imagem na posição, trocar

    :param imagem_rvf: Imagem a modificar ordem
    :param ordem_nova: ordem nova

    """
    imagem_rvf_ordem = get_imagemrvf_ordem_or_none(session,
                                                   imagem_rvf.rvf_id, ordem_nova)
    if imagem_rvf_ordem:
        imagem_rvf_ordem.ordem = imagem_rvf.ordem
        imagem_rvf.ordem = ordem_nova
        try:
            session.add(imagem_rvf_ordem)
            session.add(imagem_rvf)
            session.commit()
        except Exception as err:
            session.rollback()
            logger.error(err, exc_info=True)
            raise err


def inclui_imagemrvf(mongodb, session, image, filename, rvf_id):
    bson_img = BsonImage()
    bson_img.set_campos(filename, image, rvf_id=rvf_id)
    fs = GridFS(mongodb)
    _id = bson_img.tomongo(fs)
    print(rvf_id, filename)
    rvf = get_rvf(session, rvf_id)
    imagem = ImagemRVF()
    imagem.rvf_id = rvf_id
    imagem.imagem = str(_id)
    imagem.descricao = filename
    imagem.ordem = len(rvf.imagens) + 1
    try:
        session.add(imagem)
        session.commit()
    except Exception as err:
        session.rollback()
        logger.error(err, exc_info=True)
        raise err


def cadastra_imagemrvf(session, params=None):
    imagemrvf = get_imagemrvf(session,
                              params.get('rvf_id'),
                              params.get('imagem'))
    if imagemrvf is not None:
        if imagemrvf.ordem != params.get('ordem'):
            swap_ordem(session, imagemrvf, params.get('ordem'))
        return gera_objeto(imagemrvf, session, params)
    return imagemrvf


def delete_imagemrvf(mongodb, session, _id: str):
    imagemrvf = get_imagemrvf_imagem_or_none(session, _id)
    grid_out = mongodb['fs.files'].find_one({'_id': ObjectId(_id)})
    if imagemrvf:
        rvf_id = imagemrvf.rvf_id
    elif grid_out.get('metadata'):
        rvf_id = grid_out.get('metadata').get('rvf_id')
    session.delete(imagemrvf)
    session.commmit()
    mongodb['fs.files'].delete_one({'_id': ObjectId(_id)})
    return rvf_id


def get_ids_anexos_ordenado(rvf):
    imagens = [(imagem.imagem, imagem.ordem or 999) for imagem in rvf.imagens]
    imagens = sorted(imagens, key=lambda x: x[1])
    anexos = [imagem[0] for imagem in imagens]
    return anexos


def get_ids_anexos_mongo(db, rvf):
    filtro = {'metadata.rvf_id': str(rvf.id)}
    count = db['fs.files'].count_documents(filtro)
    result = [str(row['_id']) for row in db['fs.files'].find(filtro)]
    # print(filtro, result, count)
    return result


def ressuscita_anexos_perdidos(db, session, rvf):
    # TODO: Temporário - para recuperar imagens "perdidas" na transição
    anexos_mongo = get_ids_anexos_mongo(db, rvf)
    anexos_mysql = [imagem.imagem for imagem in rvf.imagens]
    imagens_perdidas = set(anexos_mongo) - set(anexos_mysql)
    if len(imagens_perdidas) > 0:
        for ind, _id in enumerate(imagens_perdidas, 1):
            imagem = ImagemRVF()
            imagem.rvf_id = rvf.id
            imagem.imagem = _id
            imagem.ordem = len(anexos_mysql) + ind
            session.add(imagem)
        session.commit()
        session.refresh(rvf)


def make_and_save_transformation(mongodb, session, imagemrvf: ImagemRVF,
                                 transformation: Callable):
    """Aplica função no conteúdo de GridFS, salva em novo registro, atualiza ponteiro.

    :param mongodb: conexão com MongoDB (conteúdo da imagem)
    :param session: conexão com MySQL
    :param imagemrvf: instância do objeto ImagemRVF (dados mapeamento)
    :param transformation: função que recebe conteúdo do fs.files e retorna este
    conteúdo transformado.
    :return:
    """
    fs = GridFS(mongodb)
    old_id = ObjectId(imagemrvf.imagem)
    grid_out = fs.get(old_id)
    imagem_bytes = grid_out.read()
    imagem_bytes = transformation(imagem_bytes)
    new_id = fs.put(imagem_bytes, filename=grid_out.filename,
                    metadata=grid_out.metadata)
    imagemrvf.imagem = str(new_id)
    session.add(imagemrvf)
    session.commit()
    fs.delete(old_id)
    return new_id


def inclui_nova_ordem_arquivo(session, imagem, ordem):
    # print(f'inclui_nova_ordem_arquivo.... '
    # 'imagem.rvf_id: {imagem.rvf_id} e imagem: {imagem.imagem}')
    arquivo = session.query(ImagemRVF).filter(
        ImagemRVF.rvf_id == imagem.rvf_id).filter(
        ImagemRVF.imagem == imagem.imagem).one_or_none()
    # print(f'ordem antes: {arquivo.ordem}')
    arquivo.ordem = ordem
    # print(f'ordem depois: {arquivo.ordem}')
