import io
from typing import List

from ajna_commons.utils.images import mongo_image
from bhadrasana.models.laudo import get_empresa
from bhadrasana.models.ovr import FonteDocx, OVR
from bhadrasana.models.ovrmanager import get_ovr_one, MarcaManager, get_tgovr_one
from bhadrasana.models.rvf import RVF
from bhadrasana.models.rvfmanager import get_rvf_one


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
        rvf = get_rvf_one(session, id)
        rvf_dump = rvf.dump()
        ovr = rvf.ovr
        rvf_dump['responsavel'] = ovr.responsavel.nome
        rvf_dump['recinto'] = ovr.recinto.nome
        rvf_dump['setor'] = ovr.setor.nome
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
        """Monta vários dicts com dados da RVF, com marcas separados por representante.

        Útil para preenchimento de retirada de amostras
        """
        rvf_dump = self.monta_rvf_dict(db, session, id, imagens=False)
        marcas_por_representante = MarcaManager(session).get_marcas_rvf_por_representante(id)
        rvf_dicts = []
        for representante, marcas in marcas_por_representante.items():
            rvf_dict = rvf_dump.copy()
            rvf_dict.update(representante.dump())
            rvf_dict['marcas'] = ''.join([marca.nome for marca in marcas])
            rvf_dicts.append(rvf_dict)
        return rvf_dicts
