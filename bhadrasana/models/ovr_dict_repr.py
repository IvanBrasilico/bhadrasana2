import io
from typing import List

from ajna_commons.utils.images import mongo_image
from bhadrasana.models.laudo import get_empresa
from bhadrasana.models.ovr import FonteDocx
from bhadrasana.models.ovrmanager import get_ovr, get_tgovr, get_ovr_one
from bhadrasana.models.rvf import RVF
from bhadrasana.models.rvfmanager import get_rvf


def not_implemented():
    raise NotImplementedError()


class OVRDict():

    def __init__(self, formato: [int, FonteDocx]):
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
        return method(**kwargs)

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
            ovr_dict['marcas'] = []
            for rvf_dict in rvfs_dicts:
                ovr_dict['marcas'].extend(rvf_dict['marcasencontradas'])
            if imagens:
                lista_imagens = []
                for rvf_dict in rvfs_dicts:
                    for imagem_dict in rvf_dict['imagens']:
                        image = mongo_image(db, imagem_dict['imagem'])
                        imagem_dict['content'] = io.BytesIO(image)
                        lista_imagens.append(imagem_dict)
                ovr_dict['imagens'] = lista_imagens
        return ovr_dict

    def monta_rvf_dict(self, db, session, id: int,
                       explode=True, imagens=True) -> dict:
        """Retorna um dicionário com conteúdo do RVF, inclusive imagens."""
        rvf = get_rvf(session, id)
        rvf_dump = rvf.dump()
        return rvf_dump

    def monta_tgovr_dict(self, db, session, id: int) -> dict:
        """Monta dict com dados do OVR e número deste TG.

        Útil para preenchimento de autos e representações
        """
        tgovr = get_tgovr(session, id)
        ovr_dict = self.monta_ovr_dict(db, session, tgovr.ovr_id)
        # print('OVR DICT IMAGENS', ovr_dict.get('imagens'))
        # print('OVR DICT', [(k, v) for k, v in ovr_dict.items() if not isinstance(v, list)])
        # print('OVR DICT RVFs', ovr_dict.get('rvfs'))
        ovr_dict['numerotg'] = tgovr.numerotg
        ovr_dict['valor'] = tgovr.valor
        ovr_dict['datatg'] = tgovr.create_date
        return ovr_dict

    def monta_marcas_dict(self, db, session, id: int) -> List[dict]:
        """Monta vários dicts com dados do OVR, com marcas separados por representante.

        Útil para preenchimento de retirada de amostras
        """
        ovr_dicts = []
        ovr = get_ovr(session, id)
        ovr_dict = ovr.dump()
        lista_rvfs = session.query(RVF).filter(RVF.ovr_id == ovr.id).all()
        rvfs_dicts = [rvf.dump(explode=True) for rvf in lista_rvfs]
        # TODO: Separar marcas e RVFs por representante
        for rvf_dict in rvfs_dicts:
            ovr_dict['marcas'].extend(rvf_dict['marcasencontradas'])
        return ovr_dicts
