import os

import docx

from ajna_commons.utils.docx_utils import docx_replacein


def gera_OVR(rvf: dict, user_name: str):
    conteudo = {'unidade': 'ALFSTS', **rvf}
    basepath = os.path.dirname(__file__)
    document = docx.Document(os.path.join(basepath, 'Termo de Verificação.docx'))
    docx_replacein(document, conteudo, user_name)
    return document


def gera_taseda(rvf: dict, user_name: str):
    conteudo = {'unidade': 'ALFSTS', **rvf}
    basepath = os.path.dirname(__file__)
    document = docx.Document(os.path.join(basepath, 'taseda.docx'))
    docx_replacein(document, conteudo, user_name)
    return document


def gera_taseda(rvf: dict, user_name: str):
    conteudo = {'unidade': 'ALFSTS', **rvf}
    basepath = os.path.dirname(__file__)
    document = docx.Document(os.path.join(basepath, 'taseda.docx'))
    docx_replacein(document, conteudo, user_name)
    return document


def gera_comunicado_contrafacao(ovr: dict, user_name: str):
    conteudo = {'unidade': 'ALFSTS', **ovr}
    basepath = os.path.dirname(__file__)
    document = docx.Document(os.path.join(basepath, 'comunicado_contrafacao.docx'))
    docx_replacein(document, conteudo, user_name)
    return document
