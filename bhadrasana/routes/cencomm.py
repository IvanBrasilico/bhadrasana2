import json
import logging
from datetime import datetime, time
from io import BytesIO

import openpyxl
from flask import request, jsonify, flash, redirect, url_for, render_template, send_file
from sqlalchemy import text

from bhadrasana.forms.CenDrogasFiltroForm import CenDrogasFiltroForm

# ---------------------------------------------------------------------------
# Relatório CENdrogas
# ---------------------------------------------------------------------------

# Cabeçalho EXATO do modelo CENdrogas (39 colunas, aba "CEN_droga_report")
CABECALHO_CENDROGAS = [
    'Country', 'Ref', 'Commodity', 'Offence Date', 'Offence Location',
    'Offence Location Type', 'Service', 'Concelament', 'Concelament Details',
    'Country Of Origin', 'Direction', 'Seizure Made Within ', 'Name Of Operatio',
    'Drugs Category', 'Drugs Type Level 1', 'Drugs Type Level 2', 'Other Type',
    'Drugs Quantity', 'Drugs Unit', 'Other Unit', 'Drugs percursor Type',
    'Drugs percursor ', 'Drugs percursor Unit', 'Detection Method', 'Technical aids',
    'Conveyance Level 1', 'Conveyance Level 2', 'Dept Country', 'Dept location',
    'Dept Location Type', 'Dept transport', 'Transit 1 Country', 'Transit 1 location',
    'Transit 1 location type', 'Transit 1 transport', 'Dest country', 'Dest location',
    'Dest location type', 'Dest transport',
]

# Posição (0-indexed) onde a coluna "Other Type" entra, já que a SQL não a gera
INDICE_OTHER_TYPE = 16


def _sql_cendrogas(com_filtro_data):
    filtro = 'AND ficha.datahora BETWEEN :data_inicio AND :data_fim' if com_filtro_data else ''
    return text(f"""
        SELECT
            'BR' AS pais,
            ficha.id AS ref,
            'drugs' AS commodity,
            ficha.datahora AS offence_date,
            'STS' AS offence_location,
            'Seaport' AS offence_location_type,
            'Customs' AS service,
            'Other-Specify' AS concelament,
            '' AS concelament_details,
            'Brazil' AS country_of_origin,
            'Export' AS direction,
            'NO' AS seizure_made_within,
            '' AS name_of_operatio,
            ta.descricao AS drugs_category,
            ta.descricao AS drugs_type_level_1,
            '' AS drugs_type_level_2,
            a.peso AS drugs_quantity,
            'kg' AS drugs_unit,
            '' AS other_unit,
            '' AS drugs_percursor_type,
            '' AS drugs_percursor,
            '' AS drugs_percursor_unit,
            'Routine control' AS detection_method,
            'X-Rays Scanneres, Dog' AS technical_aids,
            'Vessel' AS conveyance_level_1,
            'Commercial' AS conveyance_level_2,
            'BRAZIL' AS dept_country,
            c.portoOrigemCarga AS dept_location,
            'Seaport' AS dept_location_type,
            'Vessel' AS dept_transport,
            '' AS transit_1_country,
            m.portoDescarregamento AS transit_1_location,
            'Seaport' AS transit_1_location_type,
            'Vessel' AS transit_1_transport,
            '' AS dest_country,
            c.portoDestFinal AS dest_location,
            'Seaport' AS dest_location_type,
            'Vessel' AS dest_transport
        FROM ovr_ovrs AS ficha
        INNER JOIN ovr_verificacoesfisicas AS rvf ON ficha.id = rvf.ovr_id
        INNER JOIN ovr_apreensoes_rvf AS a ON a.rvf_id = rvf.id
        INNER JOIN ovr_tiposapreensao AS ta ON ta.id = a.tipo_id
        left join conhecimentosresumo c on ficha.numeroCEmercante = c.numeroCEmercante
        left join manifestosresumo m on m.numero = c.manifestoCE
        WHERE ficha.tipooperacao not in (6, 8)
        {filtro}
        ORDER BY ficha.datahora
    """)


def gerar_relatorio_cendrogas(session, data_inicio=None, data_fim=None):
    """Executa a consulta CENdrogas (com filtro opcional de período) e monta o workbook.

    data_inicio e data_fim são objetos date (apenas dia); internamente são
    expandidos para cobrir o dia inteiro (00:00:00 a 23:59:59).
    """
    params = {}
    if data_inicio and data_fim:
        params = {
            'data_inicio': datetime.combine(data_inicio, time.min),
            'data_fim': datetime.combine(data_fim, time.max),
        }
    sql = _sql_cendrogas(com_filtro_data=bool(params))
    logging.info('SQL CENdrogas: %s | params=%s', sql, params)
    resultado = session.execute(sql, params)

    workbook = openpyxl.Workbook()
    planilha = workbook.active
    planilha.title = 'CEN_droga_report'
    planilha.append(CABECALHO_CENDROGAS)

    for linha in resultado:
        valores = list(linha)
        offence_date = valores[3]
        if offence_date is not None:
            valores[3] = offence_date.strftime('%d/%m/%Y %H:%M')
        valores.insert(INDICE_OTHER_TYPE, '')
        planilha.append(valores)

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


def cendrogas_app(app):
    """Configura rotas para evento."""

    @app.route('/relatorio/cendrogas', methods=['GET'])
    def relatorio_cendrogas():
        session = app.config['dbsession']
        try:
            buffer = gerar_relatorio_cendrogas(session)
        except Exception as e:
            logging.exception('Erro ao gerar relatório CENdrogas')
            return jsonify({"error": str(e)}), 500

        return send_file(
            buffer,
            as_attachment=True,
            download_name='CENdrogas.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    @app.route('/cendrogas/filtro', methods=['GET'])
    def cendrogas_filtro():
        form = CenDrogasFiltroForm()
        return render_template('cendrogas_filtro.html', oform=form)

    @app.route('/cendrogas/exporta', methods=['POST'])
    def exporta_cendrogas():
        session = app.config['dbsession']
        form = CenDrogasFiltroForm()
        if not form.validate_on_submit():
            for campo, erros in form.errors.items():
                for erro in erros:
                    flash(f'{campo}: {erro}', 'danger')
            return redirect(url_for('cendrogas_filtro'))

        try:
            buffer = gerar_relatorio_cendrogas(
                session,
                data_inicio=form.datainicio.data,
                data_fim=form.datafim.data,
            )
        except Exception as e:
            logging.exception('Erro ao gerar relatório CENdrogas filtrado')
            flash(f'Erro ao gerar relatório: {e}', 'danger')
            return redirect(url_for('cendrogas_filtro'))

        return send_file(
            buffer,
            as_attachment=True,
            download_name='CENdrogas.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
