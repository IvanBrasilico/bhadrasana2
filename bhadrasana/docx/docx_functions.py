import os

from docx.document import Document

from ajna_commons.utils.docx_utils import docx_replacein


def gera_OVR(rvf: dict, user_name: str):
    conteudo = {'unidade': 'ALFSTS', **rvf}
    basepath = os.path.dirname(__file__)
    document = Document(os.path.join(basepath, 'Termo de Verificação.docx'))
    docx_replacein(document, conteudo, user_name)
    return document


def gera_taseda(rvf: dict, user_name: str):
    conteudo = {'unidade': 'ALFSTS', **rvf}
    basepath = os.path.dirname(__file__)
    document = Document(os.path.join(basepath, 'taseda.docx'))
    docx_replacein(document, conteudo, user_name)
    return document
