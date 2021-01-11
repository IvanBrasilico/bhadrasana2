from datetime import timedelta
from typing import Callable, List, Tuple, Optional

from bson import ObjectId
from gridfs import GridFS, NoFile
from sqlalchemy import and_

from ajna_commons.flask.log import logger
from ajna_commons.models.bsonimage import BsonImage
from bhadrasana.models import handle_datahora, get_usuario_validando, EBloqueado, gera_objeto
from bhadrasana.models.ovr import Marca, TipoEventoOVR, EventoEspecial, OVR, EventoOVR
from bhadrasana.models.ovrmanager import get_ovr, gera_eventoovr, \
    valida_mesmo_responsavel_ovr_user_name
from bhadrasana.models.rvf import RVF, Infracao, ImagemRVF, Lacre, \
    TipoApreensao, ApreensaoRVF
from virasana.integracao.mercante.mercantealchemy import Item


def get_peso(session, numeroCE, conteiner) -> float:
    try:
        item = session.query(Item). \
            filter(Item.numeroCEmercante == numeroCE). \
            filter(Item.codigoConteiner == conteiner).one_or_none()
        if item:
            try:
                peso = float(item.pesoBruto)
                return peso
            except Exception as err:
                logger.error(err)
    except Exception as err:
        logger.error(err, exc_info=True)
    return 0.


def get_infracoes(session):
    infracoes = session.query(Infracao).all()
    return [infracao for infracao in infracoes]


def get_infracoes_choice(session):
    infracoes = session.query(Infracao).all()
    return [(infracao.id, infracao.nome) for infracao in infracoes]


def get_rvfs_filtro(session, pfiltro) -> List[RVF]:
    filtro = and_()
    if pfiltro.get('numeroCEmercante'):
        filtro = and_(RVF.numeroCEmercante.like(
            pfiltro.get('numeroCEmercante').strip() + '%'), filtro)
    if pfiltro.get('numerolote'):
        filtro = and_(RVF.numerolote.ilike(
            pfiltro.get('numerolote').strip() + '%'), filtro)
    if pfiltro.get('datainicio'):
        filtro = and_(RVF.datahora >= pfiltro.get('datainicio'), filtro)
    datafim = pfiltro.get('datafim')
    if datafim:
        datafim = datafim + timedelta(days=1)
        filtro = and_(RVF.datahora <= datafim, filtro)
    rvfs = session.query(RVF).filter(filtro).all()
    return [rvf for rvf in rvfs]


def get_rvf(session, rvf_id: int = None) -> RVF:
    if rvf_id is None:
        return RVF()
    return session.query(RVF).filter(RVF.id == rvf_id).one_or_none()


def get_rvf_one(session, rvf_id: int = None) -> RVF:
    return session.query(RVF).filter(RVF.id == rvf_id).one()


def lista_rvfovr(session, ovr_id: int) -> Optional[List[RVF]]:
    try:
        ovr_id = int(ovr_id)
    except (ValueError, TypeError):
        return None
    return session.query(RVF).filter(RVF.ovr_id == ovr_id).all()


def gera_evento_rvf(session, rvf, user_name) -> Optional[EventoOVR]:
    """Gera Evento de RVF.

    Regras:
        - Se já existe EventoEspecial.RVF para o RVF, não cria mais
        - Somente cria se RVF tiver ao menos 3 imagens
        - Pode ser uma RVF marcada como inspecaonaoinvasiva. Neste caso é criado, caso não
        exista, o EventoEspecial.InspecaoNaoInvasiva, se não existir, mesmo sem imagens anexadas
    """
    print(rvf.inspecaonaoinvasiva)
    if rvf.inspecaonaoinvasiva:
        tipoevento = session.query(TipoEventoOVR).filter(
            TipoEventoOVR.eventoespecial == EventoEspecial.InspecaoNaoInvasiva.value).first()
    else:
        tipoevento = session.query(TipoEventoOVR).filter(
            TipoEventoOVR.eventoespecial == EventoEspecial.RVF.value).first()
    if not tipoevento:
        if rvf.inspecaonaoinvasiva:
            logger.error('Tipo Evento InspecaoNaoInvasiva não cadastrado!!!')
        else:
            logger.error('Tipo Evento RVF não cadastrado!!!')
        return None
    if (not rvf.inspecaonaoinvasiva) and (len(rvf.imagens) < 3):
        return None
    evento = session.query(EventoOVR).filter(EventoOVR.ovr_id == rvf.ovr_id). \
        filter(EventoOVR.motivo == 'RVF %s' % rvf.id). \
        filter(EventoOVR.tipoevento_id == tipoevento.id).one_or_none()
    if not evento:
        params = {'tipoevento_id': tipoevento.id,
                  'motivo': 'RVF %s' % rvf.id,
                  'user_name': rvf.user_name,
                  'ovr_id': rvf.ovr_id
                  }
        evento = gera_eventoovr(session, params, user_name=user_name)
    return evento


def verifica_permissao_rvf(session, ovr, user_name):
    if ovr and ovr.fase > 2:
        raise EBloqueado()
    get_usuario_validando(session, user_name)
    valida_mesmo_responsavel_ovr_user_name(session, ovr, user_name)


def cadastra_rvf(session,
                 user_name: str,
                 params: dict = None,
                 ovr_id: int = None) -> Optional[RVF]:
    rvf = None
    if ovr_id:
        ovr = get_ovr(session, ovr_id)
        if not ovr:
            return None
        if params is None:
            params = {}
        params['ovr_id'] = ovr.id
        params['numeroCEmercante'] = ovr.numeroCEmercante
        rvf = cadastra_rvf(session, user_name, params)
    elif params:
        rvf = get_rvf(session, params.get('id'))
        ovr_id = rvf.ovr_id if rvf.ovr_id else params.get('ovr_id')
        ovr = get_ovr(session, ovr_id)
        verifica_permissao_rvf(session, ovr, user_name)
        for key, value in params.items():
            setattr(rvf, key, value)
        rvf.user_name = user_name
        rvf.datahora = handle_datahora(params)
    if rvf is not None:
        try:
            session.add(rvf)
            session.commit()
            session.refresh(rvf)
            gera_evento_rvf(session, rvf, user_name)
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
    try:
        if mongodb:
            fs = GridFS(mongodb)
            grid_out = fs.get(ObjectId(id_imagem))
            inclui_imagemrvf(mongodb_risco, session, grid_out.read(),
                             grid_out.filename, rvf.id)
    except (TypeError, NoFile) as err:
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
            try:
                session.commit()
            except Exception as err:
                session.rollback()
                raise err
            return rvf.infracoesencontradas
    return []


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
            try:
                session.commit()
            except Exception as err:
                session.rollback()
                raise err
            return rvf.lacresverificados
    return []


def inclui_lacre_verificado(session, rvf_id, lacre_numero):
    lacre = session.query(Lacre).filter(
        Lacre.numero == lacre_numero).one_or_none()
    try:
        if not lacre:
            lacre = Lacre()
            lacre.numero = lacre_numero
            session.add(lacre)
            session.commit()
    except Exception as err:
        session.rollback()
        raise err
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
    return []


def exclui_infracao_encontrada(session, rvf_id, infracao_id):
    return gerencia_infracao_encontrada(session, rvf_id, infracao_id, inclui=False)


def gerencia_marca_encontrada(session, rvf_id, marca_id, inclui=True) -> List[Marca]:
    rvf = session.query(RVF).filter(RVF.id == rvf_id).one_or_none()
    if rvf:
        marca = session.query(Marca).filter(Marca.id == marca_id).one_or_none()
        if marca:
            if inclui:
                rvf.marcasencontradas.append(marca)
            else:
                rvf.marcasencontradas.remove(marca)
            try:
                session.commit()
            except Exception as err:
                session.rollback()
                raise err
            return rvf.marcasencontradas
    return []


def inclui_marca_encontrada(session, rvf_id, marca_nome) -> List[Marca]:
    marca = session.query(Marca).filter(Marca.nome == marca_nome).one_or_none()
    if marca:
        return gerencia_marca_encontrada(session, rvf_id, marca.id, inclui=True)
    return []


def exclui_marca_encontrada(session, rvf_id, marca_id) -> List[Marca]:
    return gerencia_marca_encontrada(session, rvf_id, marca_id, inclui=False)


def get_imagemrvf(session, rvf_id: int, _id: str):
    imagemrvf = get_imagemrvf_or_none(session, rvf_id, _id)
    if imagemrvf is None:
        return ImagemRVF()
    return imagemrvf


def get_imagemrvf_por_data(session, rvf_id: int, _id: str):
    imagemrvf = get_imagemrvf_data_modificacao(session, rvf_id, _id)
    if imagemrvf is None:
        return ImagemRVF()
    return imagemrvf


def get_imagemrvf_or_none(session, rvf_id: int, _id: str):
    return session.query(ImagemRVF).filter(
        ImagemRVF.rvf_id == rvf_id).filter(
        ImagemRVF.imagem == _id).first()


def get_imagemrvf_data_modificacao(session, rvf_id: int, _id: str):
    return session.query(ImagemRVF).filter(
        ImagemRVF.rvf_id == rvf_id).filter(
        ImagemRVF.dataModificacao == _id).first()


def get_imagemrvf_imagem_or_none(session, _id: str) -> RVF:
    return session.query(ImagemRVF).filter(
        ImagemRVF.imagem == _id).first()


def get_imagemrvf_rvf_imagem_or_none(session, rvf_id: int, _id: str) -> RVF:
    return session.query(ImagemRVF).filter(
        ImagemRVF.rvf_id == rvf_id).filter(
        ImagemRVF.imagem == _id).one_or_none()


def get_imagemrvf_ordem_or_none(session, rvf_id: int, ordem: int):
    return session.query(ImagemRVF).filter(
        ImagemRVF.rvf_id == rvf_id).filter(
        ImagemRVF.ordem == ordem).one_or_none()


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


def inclui_imagemrvf(mongodb, session, image, filename, dataModificacao, rvf_id: int):
    bson_img = BsonImage()
    bson_img.set_campos(filename, image, rvf_id=str(rvf_id))
    fs = GridFS(mongodb)
    _id = bson_img.tomongo(fs)
    # print(rvf_id, filename)
    rvf = get_rvf(session, rvf_id)
    # imagem = get_imagemrvf_rvf_imagem_or_none(session, rvf_id, str(_id))
    imagem = get_imagemrvf_imagem_or_none(session, str(_id))
    if imagem is None:  # Não existe, incluir
        imagem = ImagemRVF()
        imagem.rvf_id = rvf_id
        imagem.imagem = str(_id)
        imagem.descricao = filename
        imagem.ordem = len(rvf.imagens) + 1
        imagem.dataModificacao = dataModificacao
        try:
            session.add(imagem)
            session.commit()
        except Exception as err:
            session.rollback()
            logger.error(err, exc_info=True)
            raise err
    return imagem


def rvf_ordena_imagensrvf_por_data_criacao(session, rvf_id):
    rvf = get_rvf(session, rvf_id)
    imagens = sorted(rvf.imagens, key=lambda x: x.get_data_modificacao)
    for ind, imagem in enumerate(imagens):
        imagem.ordem = ind
        session.add(imagem)
    try:
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
    elif grid_out:
        if grid_out.get('metadata'):
            rvf_id = grid_out.get('metadata').get('rvf_id')
    session.delete(imagemrvf)
    session.commit()
    mongodb['fs.files'].delete_one({'_id': ObjectId(_id)})
    return rvf_id


def get_ids_anexos_ordenado(rvf):
    """Retorna lista de ids das imagens, ordenado pelo campo ordem"""
    imagens = [(imagem.imagem, imagem.ordem if imagem.ordem is not None else 9999)
               for imagem in rvf.imagens]
    imagens = sorted(imagens, key=lambda x: x[1])
    print(imagens)
    anexos = [imagem[0] for imagem in imagens]
    print(anexos)
    return anexos


def get_anexos_ordenado(rvf):
    """Retorna lista de imagemRVF, ordenado pelo campo ordem"""
    imagens = [(imagem, imagem.ordem if imagem.ordem is not None else 9999)
               for imagem in rvf.imagens]
    imagens = sorted(imagens, key=lambda x: x[1])
    anexos = [item[0] for item in imagens]
    return anexos


def get_ids_anexos_mongo(db, rvf):
    filtro = {'metadata.rvf_id': str(rvf.id)}
    # count = db['fs.files'].count_documents(filtro)
    result = [str(row['_id']) for row in db['fs.files'].find(filtro)]
    # print(filtro, result, count)
    return result


def get_anexos_mongo(db, rvf):
    filtro = {'metadata.rvf_id': str(rvf.id)}
    # count = db['fs.files'].count_documents(filtro)
    result = [[str(row['_fileName']), str(row['_data'])] for row in db['fs.files'].find(filtro)]
    # result = [str(row['_id']) for row in db['fs.files'].find(filtro)]
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
    arquivo = session.query(ImagemRVF).filter(
        ImagemRVF.rvf_id == imagem.rvf_id).filter(
        ImagemRVF.imagem == imagem.imagem).one_or_none()
    # print(f'...........................ordem antes: {arquivo.ordem}')
    arquivo.ordem = ordem
    session.commit()
    return True
    # print(f'...........................ordem depois: {arquivo.ordem}')


def get_tiposapreensao_choice(session) -> List[Tuple[int, str]]:
    tiposapreensao = session.query(TipoApreensao).all()
    return [(tipo.id, tipo.descricao) for tipo in tiposapreensao]


def gera_apreensao_rvf(session, params) -> ApreensaoRVF:
    return gera_objeto(ApreensaoRVF(),
                       session, params)


def exclui_apreensao_rvf(session, apreensao_id) -> List[ApreensaoRVF]:
    apreensao = session.query(ApreensaoRVF). \
        filter(ApreensaoRVF.id == apreensao_id).one_or_none()
    if apreensao:
        rvf = apreensao.rvf
        rvf.apreensoes.remove(apreensao)
        try:
            session.commit()
        except Exception as err:
            session.rollback()
            raise err
        return rvf.apreensoes
    return []
