import fitz
import os

RAIZ = '/home/ivan/Downloads'


def pegaarquivo_dirTG(dirpath, extensoes: list, nome_contem: str = None):
    listaarquivos = os.listdir(dirpath)
    extensoes = [extensao.lower() for extensao in extensoes]
    for arquivo in listaarquivos:
        if arquivo[-3:].lower() in extensoes:
            if nome_contem is not None:
                if not (nome_contem in arquivo):
                    continue
            return arquivo
    return None


listadir = os.listdir(RAIZ)
# print(listadir)
for arq in listadir:
    if arq[:2] == 'TG':
        # print(caminho)
        caminho_tgs = os.path.join(RAIZ, arq)
        for subarq in sorted(os.listdir(caminho_tgs)):
            caminho_tg = os.path.join(caminho_tgs, subarq)
            if os.path.isdir(caminho_tg):
                pdf = pegaarquivo_dirTG(caminho_tg, ['pdf'], 'CE')
                planilha = pegaarquivo_dirTG(caminho_tg, ['ods', 'xls', 'xlsx'])
                print(caminho_tg, pdf, planilha)


doc = fitz.open(os.path.join(caminho_tg, pdf))
doc.gettext()
