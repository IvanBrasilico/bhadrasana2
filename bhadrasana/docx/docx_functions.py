import os

from docx import Document
from docx.text.paragraph import Paragraph


def move_table_after(table, paragraph):
    tbl, p = table._tbl, paragraph._p
    p.addnext(tbl)


def edit_text_tag(text: str, paragraph: Paragraph, conteudo: dict):
    inicio = text.find('{')
    fim = text.find('}')
    tag = text[inicio + 1:fim].strip()
    # print('*' + tag + '*')
    valor = conteudo.get(tag)
    if valor is not None:
        new_text = text[:inicio] + str(valor) + text[fim + 1:]
        paragraph.text = new_text


def edit_table_tag(text: str, paragraph: Paragraph, conteudo: dict, document: Document):
    tags = text[1:-1].split(':')
    print(tags)
    valor = conteudo.get(tags[0])
    if valor is not None:
        paragraph.text = ' '
        table = document.add_table(rows=1, cols=len(tags) - 1)
        try:
            table.style = document.styles['Tabela']
        except Exception as err:
            print(list(document.styles))
            print(err)
        move_table_after(table, paragraph)
        hdr_cells = table.rows[0].cells
        for ind_col, key in enumerate(tags[1:]):
            hdr_cells[ind_col].text = key.capitalize()
        for row in valor:
            row_cells = table.add_row().cells
            # print(row)
            for ind_col, key in enumerate(tags[1:]):
                content = row.get(key)
                row_cells[ind_col].text = content


def paragraph_text_replace(paragraph: Paragraph, conteudo: dict, document: Document):
    text = paragraph.text
    if text and text.find('{') != -1:
        edit_text_tag(text, paragraph, conteudo)
    if text and \
            text.find('<') != -1:
        edit_table_tag(text, paragraph, conteudo, document)


def docx_replacein(document: Document, conteudo: dict):
    for paragraph in document.paragraphs:
        try:
            paragraph_text_replace(paragraph, conteudo, document)
        except Exception as err:
            print(err)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph_text_replace(paragraph, conteudo, document)


def gera_OVR(rvf: dict):
    conteudo = {'unidade': 'ALFSTS', **rvf}
    basepath = os.path.dirname(__file__)
    document = Document(os.path.join(basepath, 'OVR.docx'))
    docx_replacein(document, conteudo)
    return document
    # document.save('testes_docx/OVR_RVF{}.docx'.format(rvf.id))


def gera_taseda(rvf: dict):
    conteudo = {'unidade': 'ALFSTS', **rvf}
    basepath = os.path.dirname(__file__)
    document = Document(os.path.join(basepath, 'taseda.docx'))
    docx_replacein(document, conteudo)
    return document
    # document.save('testes_docx/taseda_RVF{}.docx'.format(rvf.id))