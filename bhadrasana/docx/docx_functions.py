from docx import Document
from docx.text.paragraph import Paragraph


def paragraph_text_replace(paragraph: Paragraph, conteudo: dict):
    text = paragraph.text
    if text and text.find('{') != -1:
        inicio = text.find('{')
        fim = text.find('}')
        tag = text[inicio + 1:fim].strip()
        print('*' + tag + '*')
        valor = conteudo.get(tag)
        if valor is not None:
            new_text = text[:inicio] + str(valor) + text[fim + 1:]
            paragraph.text = new_text


def docx_replacein(document: Document, conteudo: dict):
    for paragraph in document.paragraphs:
        paragraph_text_replace(paragraph, conteudo)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph_text_replace(paragraph, conteudo)


def gera_OVR(rvf):
    conteudo = {'unidade': 'ALFSTS', **rvf}
    document = Document('OVR.docx')
    docx_replacein(document, conteudo)
    return document
    # document.save('testes_docx/OVR_RVF{}.docx'.format(rvf.id))

def gera_taseda(rvf):
    conteudo = {'unidade': 'ALFSTS', **rvf}
    document = Document('taseda.docx')
    docx_replacein(document, conteudo)
    return document
    # document.save('testes_docx/taseda_RVF{}.docx'.format(rvf.id))
