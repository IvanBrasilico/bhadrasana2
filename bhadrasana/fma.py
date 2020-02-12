import datetime

from ajna_commons.flask.log import logger
from bhadrasana.forms.fma import FMAForm, FiltroFMAForm
from bhadrasana.models.fma import FMA
from flask import request, flash, render_template
from flask_login import login_required, current_user
from sqlalchemy import and_


def cadastra_fma(session, params):
    print(params)
    fma = get_fma(session, params.get('id'))
    print(fma.id)
    for key, value in params.items():
        setattr(fma, key, value)
    data = params.get('adata', '')
    hora = params.get('ahora', '')
    try:
        if isinstance(data, str):
            data = datetime.strptime(data, '%Y-%m-%d')
    except:
        data = datetime.date.today()
    try:
        if isinstance(hora, str):
            hora = datetime.strptime(data, '%H:%M')
    except:
        hora = datetime.datetime.now().time()
    fma.datahora = datetime.datetime.combine(data, hora)
    try:
        session.add(fma)
        session.commit()
    except Exception as err:
        session.rollback()
        raise err
        print(fma)

    return fma


def get_fma(session, id: int = None):
    if id is None:
        return FMA()
    return session.query(FMA).filter(FMA.id == id).one_or_none()


def get_fma_filtro(session, pfiltro):
    filtro = and_()
    if pfiltro.get('datainicio'):
        filtro = and_(FMA.datahora >= pfiltro.get('datainicio'))
    rvfs = session.query(FMA).filter(filtro).all()
    return [rvf for rvf in rvfs]


def fma_app(app):
    @app.route('/fma', methods=['POST', 'GET'])
    @login_required
    def fma():
        session = app.config.get('dbsession')
        db = app.config['mongo_risco']
        user_name = current_user.name
        marcas = []
        marcas_encontradas = []
        anexos = []
        fma = None
        fma_form = FMAForm()
        try:
            if request.method == 'POST':
                fma_form = FMAForm(request.form)
                fma_form.adata.data = request.form['adata']
                fma_form.ahora.data = request.form['ahora']
                fma_form.validate()
                fma = cadastra_fma(session,
                                   dict(fma_form.data.items()))
            else:
                fma_id = request.args.get('id')
                if fma_id is not None:
                    fma = get_fma(session, fma_id)
                    if fma is not None:
                        fma_form = FMAForm(**fma.__dict__)
                        if fma.datahora:
                            fma_form.adata.data = fma.datahora.date()
                            fma_form.ahora.data = fma.datahora.time()
            if fma:
                fma_form.id.data = fma.id
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
        return render_template('fma.html',
                               oform=fma_form)

    @app.route('/pesquisa_fma', methods=['POST', 'GET'])
    @login_required
    def pesquisa_fma():
        session = app.config.get('dbsession')
        user_name = current_user.name
        rvfs = []
        filtro_form = FiltroFMAForm(
            datainicio=datetime.date.today() - datetime.timedelta(days=10),
            datafim=datetime.date.today()
        )
        try:
            if request.method == 'POST':
                filtro_form = FiltroFMAForm(request.form)
                filtro_form.validate()
                rvfs = get_fma_filtro(session, dict(filtro_form.data.items()))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
        return render_template('pesquisa_fma.html',
                               oform=filtro_form,
                               rvfs=rvfs)
