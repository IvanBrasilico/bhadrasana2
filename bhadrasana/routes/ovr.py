import datetime
from _collections import defaultdict

from flask import request, flash, render_template, url_for, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import redirect

from ajna_commons.flask.log import logger
from bhadrasana.forms.ovr import OVRForm, FiltroOVRForm, HistoricoOVRForm, \
    ProcessoOVRForm, ItemTGForm, ResponsavelOVRForm, TGOVRForm
from bhadrasana.models import delete_objeto
from bhadrasana.models.ovr import ItemTG, OVR
from bhadrasana.models.ovrmanager import cadastra_ovr, get_ovr, \
    get_ovr_filtro, gera_eventoovr, get_tipos_evento, \
    gera_processoovr, get_tipos_processo, lista_itemtg, get_itemtg, get_recintos, \
    cadastra_itemtg, get_usuarios, atribui_responsavel_ovr, lista_tgovr, get_tgovr, \
    cadastra_tgovr, get_ovr_responsavel
from bhadrasana.models.rvfmanager import get_marcas_choice
from virasana.integracao.mercante.mercantealchemy import Conhecimento, NCMItem, Item


def ovr_app(app):
    def trata_ovr(request, ovr_id):
        session = app.config.get('dbsession')
        listahistorico = []
        processos = []
        tiposeventos = get_tipos_evento(session)
        recintos = get_recintos(session)
        responsaveis = get_usuarios(session)
        ovr_form = OVRForm(tiposeventos=tiposeventos, recintos=recintos)
        tiposprocesso = get_tipos_processo(session)
        historico_form = HistoricoOVRForm(tiposeventos=tiposeventos)
        processo_form = ProcessoOVRForm(tiposprocesso=tiposprocesso)
        responsavel_form = ResponsavelOVRForm(responsaveis=responsaveis)
        conhecimento = None
        ncms = []
        containers = []
        ovr = OVR()
        try:
            if request.method == 'POST':
                ovr_form = OVRForm(request.form)
                ovr_form.adata.data = request.form.get('adata')
                ovr_form.ahora.data = request.form.get('ahora')
                ovr_form.validate()
                print(ovr_form.data.items())
                ovr = cadastra_ovr(session,
                                   dict(ovr_form.data.items()),
                                   user_name=current_user.name)
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
                               ovr=ovr,
                               oform=ovr_form,
                               conhecimento=conhecimento,
                               ncms=ncms,
                               containers=containers,
                               historico_form=historico_form,
                               processo_form=processo_form,
                               responsavel_form=responsavel_form,
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
                ovrs = get_ovr_filtro(session, current_user.name,
                                      dict(filtro_form.data.items()))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
        return render_template('pesquisa_ovr.html',
                               oform=filtro_form,
                               ovrs=ovrs)

    @app.route('/minhas_ovrs', methods=['GET'])
    @app.route('/ovrs_meus_setores', methods=['GET'])
    @login_required
    def minhas_ovrs():
        session = app.config.get('dbsession')
        listasovrs = defaultdict(list)
        try:
            if 'minhas_ovrs' in request.url:
                active_tab = 'minhas_ovrs'
                ovrs = get_ovr_responsavel(session, current_user.name)
            else:
                active_tab = 'ovrs_meus_setores'
                ovrs = get_ovr_filtro(session, current_user.name)
            for ovr in ovrs:
                listasovrs[str(ovr.fase) + '-' + ovr.get_fase()].append(ovr)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
        return render_template('minhas_ovrs.html',
                               listasovrs=listasovrs,
                               active_tab=active_tab)

    @app.route('/responsavelovr', methods=['POST'])
    @login_required
    def atribuirresponsavel():
        session = app.config.get('dbsession')
        responsavel_ovr_form = ResponsavelOVRForm(request.form)
        atribui_responsavel_ovr(session,
                                ovr_id=responsavel_ovr_form.ovr_id.data,
                                responsavel=responsavel_ovr_form.responsavel.data
                                )
        return redirect(url_for('ovr', id=responsavel_ovr_form.ovr_id.data))

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

    @app.route('/lista_tgovr', methods=['GET'])
    @login_required
    def listatgovr():
        session = app.config.get('dbsession')
        ovr_id = request.args.get('ovr_id')
        item_id = request.args.get('item_id')
        listatgovr = lista_tgovr(session, ovr_id)
        marcas = get_marcas_choice(session)
        if item_id:
            tgovr = get_tgovr(session, item_id)
            marcas = get_marcas_choice(session)
            oform = TGOVRForm(**tgovr.__dict__, marcas=marcas)
        else:
            oform = TGOVRForm(ovr_id=ovr_id, marcas=marcas)
        return render_template('lista_tgovr.html',
                               listatgovr=listatgovr,
                               oform=oform)

    @app.route('/tgovr', methods=['POST'])
    @login_required
    def tgovr():
        session = app.config.get('dbsession')
        item_id = None
        try:
            tgovr_form = TGOVRForm(request.form)
            tgovr_form.validate()
            tgovr = cadastra_tgovr(session, dict(tgovr_form.data.items()))
            ovr_id = tgovr.ovr_id
            # item_id = tgovr.id
        except Exception as err:
            flash(str(err))
            logger.error(err, exc_info=True)
            ovr_id = request.form.get('ovr_id')
        return redirect(url_for('listatgovr',
                                ovr_id=ovr_id,
                                item_id=item_id))

    @app.route('/lista_itemtg', methods=['GET'])
    @login_required
    def listaitemtg():
        session = app.config.get('dbsession')
        ovr_id = request.args.get('ovr_id')
        item_id = request.args.get('item_id')
        listaitemtg = lista_itemtg(session, ovr_id)
        marcas = get_marcas_choice(session)
        if item_id:
            itemtg = get_itemtg(session, item_id)
            marcas = get_marcas_choice(session)
            oform = ItemTGForm(**itemtg.__dict__, marcas=marcas)
        else:
            oform = ItemTGForm(ovr_id=ovr_id, marcas=marcas)
        return render_template('lista_itemtg.html',
                               listaitemtg=listaitemtg,
                               oform=oform)

    @app.route('/itemtg', methods=['POST'])
    @login_required
    def itemtg():
        session = app.config.get('dbsession')
        itemtg_form = ItemTGForm(request.form)
        itemtg_form.validate()
        print(request.form)
        print(itemtg_form.data.items())
        itemtg = cadastra_itemtg(session, dict(itemtg_form.data.items()))
        return redirect(url_for('listaitemtg', ovr_id=itemtg.ovr_id))

    @app.route('/edita_itemtg', methods=['GET'])
    @login_required
    def edita_itemtg():
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
