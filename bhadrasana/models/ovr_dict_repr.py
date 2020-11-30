import io
from typing import List, Union

from ajna_commons.utils.images import mongo_image
from bhadrasana.forms.exibicao_ovr import ExibicaoOVR
from bhadrasana.models import get_usuario
from bhadrasana.models.laudo import get_empresa
from bhadrasana.models.ovr import FonteDocx
from bhadrasana.models.ovrmanager import get_ovr_one, MarcaManager, get_tgovr_one
from bhadrasana.models.rvf import RVF
from bhadrasana.models.rvfmanager import get_rvf_one
from bhadrasana.models.virasana_manager import get_due


def not_implemented():
    raise NotImplementedError()


class OVRDict():

    def __init__(self, formato: Union[int, FonteDocx]):
        if isinstance(formato, str):
            formato = int(formato)
        if isinstance(formato, int):
            formato = FonteDocx(formato)
        self.formato = formato
        self.formatos = {
            FonteDocx.Ficha: self.monta_ovr_dict,
            FonteDocx.RVF: self.monta_rvf_dict,
            FonteDocx.Marcas: self.monta_marcas_dict,
            FonteDocx.TG_Ficha: self.monta_tgovr_dict,
        }

    def get_dict(self, **kwargs):
        method = self.formatos[self.formato]
        result = method(**kwargs)
        return result

    def monta_ovr_dict(self, db, session, id: int,
                       explode=True, rvfs=True, imagens=True) -> dict:
        """Retorna um dicionário com conteúdo do OVR, inclusive imagens."""
        ovr = get_ovr_one(session, id)
        ovr_dict = ovr.dump(explode=explode)
        if rvfs:
            lista_rvfs = session.query(RVF).filter(RVF.ovr_id == id).all()
            rvfs_dicts = [rvf.dump(explode=True) for rvf in lista_rvfs]
            ovr_dict['rvfs'] = rvfs_dicts
            try:
                empresa = get_empresa(session, ovr.cnpj_fiscalizado)
                ovr_dict['nome_fiscalizado'] = empresa.nome
            except ValueError:
                ovr_dict['nome_fiscalizado'] = ''
            usuario = get_usuario(session, ovr.cpfauditorresponsavel)
            if usuario:
                ovr_dict['nome_auditorresponsavel'] = usuario.nome
                ovr_dict['auditor_responsavel'] = usuario.nome
            ovr_dict['marcas'] = []
            for rvf_dict in rvfs_dicts:
                ovr_dict['marcas'].extend(rvf_dict['marcasencontradas'])
            if imagens:
                lista_imagens = []
                for rvf_dict in rvfs_dicts:
                    # Garantir que as imagens sigam a ordem definida pelo usuário na exbibição
                    imagens_rvf = sorted(rvf_dict['imagens'], key=lambda x: x['ordem'])
                    for imagem_dict in imagens_rvf:
                        image = mongo_image(db, imagem_dict['imagem'])
                        imagem_dict['content'] = io.BytesIO(image)
                        lista_imagens.append(imagem_dict)
                ovr_dict['imagens'] = lista_imagens
            for processo in ovr.processos:
                ovr_dict['processo_%s' % processo.tipoprocesso.descricao] = processo.numero
        return ovr_dict

    def monta_rvf_dict(self, db, session, id: int,
                       explode=True, imagens=True) -> dict:
        """Retorna um dicionário com conteúdo do RVF, inclusive imagens."""
        rvf = get_rvf_one(session, id)
        rvf_dump = rvf.dump(explode=explode, imagens=imagens)
        ovr = rvf.ovr
        if ovr.cpfauditorresponsavel:
            usuario = get_usuario(session, ovr.cpfauditorresponsavel)
            if usuario:
                rvf_dump['auditor_responsavel'] = usuario.nome
        if ovr.responsavel:
            rvf_dump['responsavel'] = ovr.responsavel.nome
        if ovr.recinto:
            rvf_dump['recinto'] = ovr.recinto.nome
        if ovr.setor:
            rvf_dump['setor'] = ovr.setor.nome
        exibicao = ExibicaoOVR(session, 1, '')
        if ovr.numerodeclaracao:
            rvf_dump['resumo_due'] = get_due(db, ovr.numerodeclaracao)
        if ovr.numeroCEmercante:
            rvf_dump['resumo_mercante'] = exibicao.get_mercante_resumo(ovr)
        return rvf_dump

    def monta_tgovr_dict(self, db, session, id: int) -> dict:
        """Monta dict com dados do OVR e número deste TG.

        Útil para preenchimento de autos e representações
        """
        tgovr = get_tgovr_one(session, id)
        ovr_dict = self.monta_ovr_dict(db, session, tgovr.ovr_id)
        # print('OVR DICT IMAGENS', ovr_dict.get('imagens'))
        # print('OVR DICT', [(k, v) for k, v in ovr_dict.items() if not isinstance(v, list)])
        # print('OVR DICT RVFs', ovr_dict.get('rvfs'))
        ovr_dict['numerotg'] = tgovr.numerotg
        ovr_dict['valor'] = tgovr.valor
        ovr_dict['datatg'] = tgovr.create_date
        return ovr_dict

    def monta_marcas_dict(self, db, session, id: int) -> List[dict]:
        """Monta vários dicts com dados da Ficha, com marcas separados por representante.

        Útil para preenchimento de retirada de amostras
        """
        ovr_dump = self.monta_ovr_dict(db, session, id, imagens=False)
        marca_manager = MarcaManager(session)
        marcas_dict = {}
        for rvf in ovr_dump['rvfs']:
            marca_dict = marca_manager.get_marcas_rvf_por_representante(rvf['id'])
            marcas_dict.update(marca_dict)
        ovr_dicts = []
        for representante, marcas in marcas_dict.items():
            ovr_dict = ovr_dump.copy()
            if representante:
                ovr_dict['representante'] = representante.dump()
            ovr_dict['marcas'] = ', '.join([marca.nome for marca in marcas])
            ovr_dicts.append(ovr_dict)
        return ovr_dicts
