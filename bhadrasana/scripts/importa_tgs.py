import os
import sys
from datetime import datetime

import fitz

sys.path.append('.')
sys.path.append('../ajna_docs/commons')
sys.path.append('../virasana')

from bhadrasana.models import db_session
from bhadrasana.models.ovr import OVR, TGOVR
from bhadrasana.models.ovrmanager import importa_planilha_tg

RAIZ = '/home/ivan/Downloads'
RAIZ = 'C:\\Users\\25052288840\\Desktop\\Casos'


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


def processa_PDF_CE(arquivo, encode='utf8'):
    doc = fitz.open(arquivo)
    page = doc.loadPage(0)
    text = page.getText()
    ce_pos = text.find('do CE-Mercante N') + 18
    ce = text[ce_pos:ce_pos + 15]
    cnpj_pos = text.find('CNPJ/CPF') + 11
    cnpj = text[cnpj_pos:cnpj_pos + 18]
    return ce, cnpj


def processa_dirs():
    listadir = os.listdir(RAIZ)
    # print(listadir)
    validos = 0
    invalidos = 0
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
                    if not pdf:
                        continue
                    ce = ''
                    ce, cnpj = processa_PDF_CE(os.path.join(caminho_tg, pdf))
                    print(ce, cnpj)
                    if not ce.isnumeric():
                        print(f'Erro para processar CE no caminho: {caminho_tg} CE: {ce}')
                        invalidos += 1
                        ce = f'Inválido {invalidos}'
                    # Cria Ficha e TG
                    tgovr = db_session.query(TGOVR).filter(TGOVR.numerolote == ce).one_or_none()
                    if not tgovr:
                        ovr = db_session.query(OVR).filter(OVR.numeroCEmercante == ce). \
                            one_or_none()
                        if not ovr:
                            ovr = OVR()
                            ovr.numeroCEmercante = ce
                            ovr.cnpj_fiscalizado = ''.join([s for s in cnpj if s.isnumeric()])
                            db_session.add(ovr)
                            create_time = datetime.fromtimestamp(os.path.getmtime(
                                os.path.join(caminho_tg, pdf)))
                            ovr.datahora = create_time
                            ovr.create_date = create_time
                            ovr.setor_id = '1'
                            db_session.commit()
                            db_session.refresh(ovr)
                        tgovr = TGOVR()
                        tgovr.ovr_id = ovr.id
                        tgovr.numerolote = ce
                        create_time = datetime.fromtimestamp(os.path.getmtime(
                            os.path.join(caminho_tg, planilha)))
                        tgovr.create_date = create_time
                        tgovr.descricao = 'Importado automaticamente'
                        db_session.add(tgovr)
                        db_session.commit()
                        db_session.refresh(tgovr)
                    if len(tgovr.itenstg) > 0:
                        print(f'Pulando TG {tgovr.id} OVR {tgovr.ovr_id} porque já possui itens')
                        continue
                    if planilha:
                        alertas = importa_planilha_tg(db_session, tgovr,
                                                      os.path.join(caminho_tg, planilha))
                        if alertas:
                            print(alertas)
                            invalidos += 1
                        else:
                            print(f'Criou ItensTG no OVR id {tgovr.ovr_id}')
                            validos += 1
    print(validos, invalidos)


processa_dirs()
