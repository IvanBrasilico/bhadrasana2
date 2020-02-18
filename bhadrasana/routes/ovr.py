import datetime
from _collections import defaultdict

from ajna_commons.flask.log import logger
from bhadrasana.forms.ovr import OVRForm, FiltroOVRForm, HistoricoOVRForm, ProcessoOVRForm, ItemTGForm
from bhadrasana.models.ovr import ItemTG
from bhadrasana.models.ovrmanager import cadastra_ovr, get_ovr, \
    get_ovr_filtro, gera_eventoovr, get_tipos_evento, delete_objeto, gera_processoovr, get_tipos_processo, lista_itemtg, \
    get_itemtg, get_recintos
from bhadrasana.models.rvfmanager import get_marcas_choice
from flask import request, flash, render_template, url_for, jsonify
from flask_login import login_required, current_user
from virasana.integracao.mercante.mercantealchemy import Conhecimento, NCMItem, Item
from werkzeug.utils import redirect


def ovr_app(app):
    def trata_ovr(request, ovr_id):
        session = app.config.get('dbsession')
        listahistorico = []
        processos = []
        tiposeventos = get_tipos_evento(session)
        recintos = get_recintos(session)
        ovr_form = OVRForm(tiposeventos=tiposeventos, recintos=recintos)
        tiposprocesso = get_tipos_processo(session)
        historico_form = HistoricoOVRForm(tiposeventos=tiposeventos)
        processo_form = ProcessoOVRForm(tiposprocesso=tiposprocesso)
        conhecimento = None
        ncms = []
        containers = []
        try:
            if request.method == 'POST':
                ovr_form = OVRForm(request.form)
                ovr_form.adata.data = request.form.get('adata')
                ovr_form.ahora.data = request.form.get('ahora')
                ovr_form.validate()
                ovr = cadastra_ovr(session,
                                   dict(ovr_form.data.items()))
                return redirect(url_for('ovr', id=ovr.id))
            else:
                if ovr_id is not None:
                    ovr = get_ovr(session, ovr_id)
                    if ovr is not None:
                        ovr_form = OVRForm(**ovr.__dict__,
                                           tiposeventos=tiposeventos,
                                           recintos=recintos)
                        # TODO: Extrair visualização do conhecimento para uma função,
                        # talvez um Endpoint para consulta JavaScript
                        numeroCEmercante = ovr.numeroCEmercante
                        conhecimento = session.query(Conhecimento).filter(
                            Conhecimento.numeroCEmercante == numeroCEmercante
                        ).one_or_none()
                        ncms = session.query(NCMItem).filter(
                            NCMItem.numeroCEMercante == numeroCEmercante
                        ).all()
                        containers = session.query(Item).filter(
                            Item.numeroCEmercante == numeroCEmercante
                        ).all()
                        ovr_form.id.data = ovr.id
                        listahistorico = ovr.historico
                        processos = ovr.processos
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
        return render_template('ovr.html',
                               oform=ovr_form,
                               conhecimento=conhecimento,
                               ncms=ncms,
                               containers=containers,
                               historico_form=historico_form,
                               processo_form=processo_form,
                               listahistorico=listahistorico,
                               processos=processos)

    @app.route('/ovr/<id>', methods=['POST', 'GET'])
    @login_required
    def ovr_id(id):
        return trata_ovr(request, id)

    @app.route('/ovr', methods=['POST', 'GET'])
    @login_required
    def ovr():
        id = request.args.get('id')
        return trata_ovr(request, id)

    @app.route('/pesquisa_ovr', methods=['POST', 'GET'])
    @login_required
    def pesquisa_ovr():
        session = app.config.get('dbsession')
        user_name = current_user.name
        ovrs = []
        tiposeventos = get_tipos_evento(session)
        filtro_form = FiltroOVRForm(
            datainicio=datetime.date.today() - datetime.timedelta(days=10),
            datafim=datetime.date.today(),
            tiposeventos=tiposeventos
        )
        try:
            if request.method == 'POST':
                filtro_form = FiltroOVRForm(request.form, tiposeventos=tiposeventos)
                filtro_form.validate()
                ovrs = get_ovr_filtro(session, dict(filtro_form.data.items()))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
        return render_template('pesquisa_ovr.html',
                               oform=filtro_form,
                               ovrs=ovrs)

    @app.route('/minhas_ovrs', methods=['GET'])
    @login_required
    def minhas_ovrs():
        session = app.config.get('dbsession')
        user_name = current_user.name
        ovrs = []
        listasovrs = defaultdict(list)
        try:
            ovrs = get_ovr_filtro(session, {})
            for ovr in ovrs:
                listasovrs[ovr.get_fase()].append(ovr)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
        return render_template('minhas_ovrs.html',
                               listasovrs=listasovrs)

    @app.route('/movimentaovr', methods=['POST'])
    @login_required
    def movimentaovr():
        session = app.config.get('dbsession')
        ovr_id = request.form['ovr_id']
        historico_ovr_form = HistoricoOVRForm(request.form)
        gera_eventoovr(session, dict(historico_ovr_form.data.items()))
        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/processoovr', methods=['POST'])
    @login_required
    def processoovr():
        session = app.config.get('dbsession')
        ovr_id = request.form['ovr_id']
        processo_ovr_form = ProcessoOVRForm(request.form)
        processo_ovr_form.validate()
        gera_processoovr(session, dict(processo_ovr_form.data.items()))
        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/lista_itemtg', methods=['GET'])
    @login_required
    def listaitemtg():
        session = app.config.get('dbsession')
        ovr_id = request.args.get('ovr_id')
        listaitemtg = lista_itemtg(session, ovr_id)
        # print(listaitemtg)
        item_id = request.args.get('item_id')
        itemtg = get_itemtg(session, item_id)
        if itemtg:
            marcas = get_marcas_choice(session)
            oform = ItemTGForm(**itemtg.__dict__, marcas=marcas)
        return render_template('lista_itemtg.html',
                               listaitemtg=listaitemtg,
                               oform=oform)

    @app.route('/edita_itemtg', methods=['GET'])
    @login_required
    def itemtg():
        session = app.config.get('dbsession')
        id = request.args.get('id')
        campo = request.args.get('campo')
        valor = request.args.get('valor')
        itemtg = session.query(ItemTG).filter(ItemTG.id == int(id)).one_or_none()
        setattr(itemtg, campo, valor)
        session.add(itemtg)
        session.commit()
        # itemtg_form = ItemTGForm(request.form)
        # itemtg_form.validate()
        # gera_itemtg(session, dict(itemtg_form.data.items()))
        return {'msg': 'Modificado com sucesso'}, 200

    @app.route('/excluiobjeto/<classname>/<id>', methods=['POST'])
    @login_required
    def excluiobjeto(classname, id):
        session = app.config.get('dbsession')
        delete_objeto(session, classname, id)
        return jsonify({'msg': 'Excluído'}), 200
