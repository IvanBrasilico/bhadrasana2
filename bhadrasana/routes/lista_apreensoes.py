"""
Endpoint para a tela de análise de risco de operações atuais.

Recebe via GET (ambos opcionais, mas ao menos um deve ser informado):
    cnpj -> bate com OVR.cnpj_fiscalizado (exportadora/fiscalizada)
    ncm  -> NCM com até 4 dígitos; compara como PREFIXO de NCMItem.identificacaoNCM

Tratamento de entrada:
    - cnpj: remove tudo que não for letra/número (pontuação, espaços, máscara)
      e converte para maiúsculas (aceita o novo CNPJ alfanumérico da Receita).
    - ncm: remove tudo que não for dígito e trunca em 8 caracteres.

Contrato de resposta (pensado para ser consumido via jQuery/$.ajax):
    - Sucesso, com ou sem resultados -> HTTP 200 e um JSON com uma lista
      (array) de fichas, cada uma com os campos esperados. Uma busca sem
      resultados NÃO é erro: retorna 200 e lista vazia [].
    - Parâmetros inválidos/ausentes -> HTTP 400 e um JSON de erro:
      {"erro": "mensagem"}.
    - Qualquer exceção inesperada -> HTTP 500 e um JSON de erro:
      {"erro": "mensagem"}. Nunca deixa uma página de erro HTML/traceback
      vazar para o cliente.
    - Datas/horas são sempre serializadas em ISO 8601 (via .isoformat()),
      para que qualquer biblioteca de formatação no front-end (moment,
      dayjs, Date nativo) consiga interpretar sem parsing manual.

Fluxo da consulta:
    1) OVR <-> NCMItem são ligados por valor (sem FK declarada no model),
       através de OVR.numeroCEmercante == NCMItem.numeroCEMercante
       (atenção: nomes de campo com capitalização diferente entre as
       classes). O join com NCMItem só é feito quando "ncm" é informado.
    2) Filtra por cnpj_fiscalizado (se informado) e/ou por
       identificacaoNCM.like('NCM%') (se informado).
    3) Para cada OVR encontrada, monta o JSON com os dados pedidos,
       incluindo a lista de NCMs e de contêineres do CE Mercante, os RVFs
       (com a primeira imagem, ordem=1) e, dentro de cada RVF, as
       apreensões.

Se RVF/ApreensaoRVF não estiverem em bhadrasana.models.rvf, ajuste o
import abaixo.
"""

import re
import traceback

from flask import request, jsonify, render_template

from bhadrasana.models.ovr import OVR
from bhadrasana.models.rvf import RVF, ApreensaoRVF, ImagemRVF
from virasana.integracao.mercante.mercantealchemy import NCMItem, Item


# ---------------------------------------------------------------------
# Limpeza / normalização de parâmetros de entrada
# ---------------------------------------------------------------------

def limpar_cnpj(valor):
    """Remove pontuação/espaços, mantém apenas letras e números, maiúsculas.

    Aceita letras porque o CNPJ alfanumérico da Receita Federal (2026)
    também usa esse formato de 14 caracteres.
    """
    if not valor:
        return ''
    return re.sub(r'[^A-Za-z0-9]', '', valor).upper()


def limpar_ncm(valor):
    """Remove tudo que não for dígito e trunca em 8 caracteres (NCM completo)."""
    if not valor:
        return ''
    return re.sub(r'\D', '', valor)[:8]


def fmt_data(dt):
    """Serializa datetime em ISO 8601, ou None."""
    return dt.isoformat() if dt else None


def apreensoes_app(app):
    """Configura rotas para evento."""

    @app.route('/api/fichas/apreensoes', methods=['GET'])
    def fichas_por_risco():
        session = app.config['dbsession']

        cnpj = limpar_cnpj(request.args.get('cnpj', ''))
        ncm = limpar_ncm(request.args.get('ncm', ''))

        if not cnpj and not ncm:
            return jsonify(
                {'erro': 'Informe ao menos um dos parâmetros "cnpj" ou "ncm"'}
            ), 400

        try:
            query = session.query(OVR.id)

            # só faz o join com NCMItem quando o filtro de NCM é usado
            if ncm:
                query = query.join(
                    NCMItem, OVR.numeroCEmercante == NCMItem.numeroCEMercante
                ).filter(NCMItem.identificacaoNCM.like(f'{ncm}%'))

            if cnpj:
                query = query.filter(OVR.cnpj_fiscalizado == cnpj)

            ovr_ids_subquery = query.distinct().subquery()

            ovrs = (
                session.query(OVR)
                .filter(OVR.id.in_(ovr_ids_subquery))
                .all()
            )

            def ncms_da_ovr(ovr):
                """Lista distinta de NCMs (identificacaoNCM) dos itens do CE Mercante da OVR."""
                rows = (
                    session.query(NCMItem.identificacaoNCM)
                    .filter(NCMItem.numeroCEMercante == ovr.numeroCEmercante)
                    .distinct()
                    .all()
                )
                return [row[0] for row in rows]

            def conteineres_da_ovr(ovr):
                """Lista distinta de contêineres (Item.codigoConteiner) do CE Mercante da OVR."""
                rows = (
                    session.query(Item.codigoConteiner)
                    .filter(Item.numeroCEmercante == ovr.numeroCEmercante)
                    .distinct()
                    .all()
                )
                return [row[0] for row in rows]

            def primeira_imagem_da_rvf(rvf):
                """_id (GridFS) da imagem de ordem=1 da RVF, ou None se não houver."""
                imagem = (
                    session.query(ImagemRVF)
                    .filter(ImagemRVF.rvf_id == rvf.id, ImagemRVF.ordem == 1)
                    .first()
                )
                return imagem.imagem if imagem else None

            resultado = [
                {
                    'id': ovr.id,
                    'datahora': fmt_data(ovr.datahora),
                    'observacoes': ovr.observacoes,
                    'numeroCEmercante': ovr.numeroCEmercante,
                    'numerodeclaracao': ovr.numerodeclaracao,
                    'ncms': ncms_da_ovr(ovr),
                    'conteineres': conteineres_da_ovr(ovr),
                    'rvfs': [
                        {
                            'datahora': fmt_data(rvf.datahora),
                            'numerolote': rvf.numerolote,
                            'descricao': rvf.descricao,
                            'primeiraimagem': primeira_imagem_da_rvf(rvf),
                            'apreensoes': [apreensao.dump() for apreensao in rvf.apreensoes],
                        }
                        for rvf in ovr.rvfs
                    ],
                }
                for ovr in ovrs
            ]

            # sucesso -> sempre 200, mesmo com lista vazia
            return jsonify(resultado), 200

        except Exception:
            # nunca deixa um traceback/HTML de erro vazar para o cliente;
            # loga no servidor e responde com JSON válido + status de erro
            traceback.print_exc()
            return jsonify(
                {'erro': 'Erro interno ao processar a consulta de risco.'}
            ), 500

    @app.route('/api/fichas/apreensoes-demo', methods=['GET'])
    def risco_demo():
        """Serve a página de demonstração que consome /api/risco/fichas.

        Requer que 'apreensoes_demo.html' esteja na pasta templates/ da app
        (a mesma usada pelas outras telas do sistema). O HTML já referencia
        a rota existente /image/<id> para exibir a imagem da RVF.
        """
        return render_template('apreensoes_demo.html')