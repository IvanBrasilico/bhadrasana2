"""
Módulo para facilitar o registro de inspeções não-invasivas.

Permite registrar rapidamente análise de imagem efetuada pelo COV, seja com Ficha a
encaminhar para verificação física, ou registrando e logo em seguida encerrando.

"""
from datetime import timedelta

from bson import ObjectId
from flask import render_template, flash, url_for
from flask_login import login_required, current_user
from werkzeug.utils import redirect

from ajna_commons.flask.log import logger
from bhadrasana.models.ovr import OVR
from bhadrasana.models.ovrmanager import cadastra_ovr, atribui_responsavel_ovr
from bhadrasana.models.rvf import RVF
from bhadrasana.models.rvfmanager import programa_rvf_container, lista_rvfovr, gera_evento_rvf, get_rvf


def assistenteini_app(app):
    @app.route('/nova_inspecaoni/<_id>', methods=['GET'])
    @login_required
    def nova_inspecaonaoinvasiva(_id):
        title_page = 'Assistente de Inspeção Não Invasiva'
        mongodb = app.config['mongodb']
        mongo_risco = app.config['mongo_risco']
        session = app.config.get('dbsession')
        try:
            # raise Exception('Não implementado!!!')
            grid_data = mongodb['fs.files'].find_one({'_id': ObjectId(_id)})
            meta = grid_data['metadata']
            print(meta)
            xmldoc = meta.get('xml')
            if xmldoc is None:
                alerta = False
            else:
                alerta = xmldoc.get('alerta')
            container = meta.get('numeroinformado')
            dataescaneamento = meta.get('dataescaneamento')
            metacarga = meta.get('carga')
            tipooperacao = 2
            if metacarga is None:
                conhecimento = ''
                descricao = ''
            else:
                if metacarga.get('vazio'):
                    conhecimento = metacarga.get('manifesto')
                    if isinstance(conhecimento, list):
                        conhecimento = conhecimento[0]
                    conhecimento = conhecimento.get('manifesto')
                    descricao = 'Manifesto'
                else:
                    conhecimento = metacarga.get('conhecimento')
                    if isinstance(conhecimento, list):
                        conhecimento = conhecimento[0]
                    descricao = 'Conhecimento'
                    tipo = conhecimento.get('trafego').lower()
                    if tipo == 'lci':
                        tipooperacao = 1
                    conhecimento = conhecimento.get('conhecimento')
            ovr_data = {'numeroCEmercante': conhecimento,
                        'tipooperacao': tipooperacao,
                        'observacoes': f'Inspeção não invasiva {descricao} ' \
                                       f'{conhecimento} automaticamente registrada.'
                                       f'Análise do contêiner {container}'
                        }
            ovr = None
            if conhecimento:
                ovr = session.query(OVR).filter(OVR.numeroCEmercante == conhecimento). \
                    order_by(OVR.id.desc()).first()
            elif container and dataescaneamento:
                # 1 e 2: Parênteses corrigidos e ordenando por RVF.id
                rvf = session.query(RVF).filter(
                    RVF.numerolote == container,
                    RVF.datahora.between(dataescaneamento, dataescaneamento + timedelta(days=7))
                ).order_by(RVF.id.desc()).first()
                
                # 3: Checagem se o RVF realmente existe antes de buscar a OVR
                if rvf:
                    ovr = session.query(OVR).filter(OVR.id == rvf.ovr_id).one_or_none()
                else:
                    ovr = None
            if ovr is None:
                ovr = cadastra_ovr(session,
                                   params=ovr_data,
                                   user_name=current_user.name)
            atribui_responsavel_ovr(session, ovr.id, current_user.name, current_user.name)
            rvf = None
            rvfs = lista_rvfovr(session, ovr.id)
            if len(rvfs) > 0:
                for umarvf in rvfs:
                    if umarvf.numerolote == container:
                        rvf = get_rvf(session, umarvf.id)
                        break
            if rvf is None:
                # imagens = get_imagens_dict_container_id(mongodb, ovr.numeroCEmercante, '')
                rvf = programa_rvf_container(
                    mongodb, mongo_risco, session,
                    ovr, container, _id
                )
            if rvf and (rvf.descricao == '' or rvf.descricao is None):
                rvf.descricao = 'Análise de imagem de escaneamento, por rotina do COV.'
                if alerta:
                    rvf.descricao = rvf.descricao + '\n Contêiner com alerta Operador.'
            rvf.inspecaonaoinvasiva = True
            try:
                session.add(rvf)
                session.commit()
            except Exception as err:
                session.rollback()
                raise err
            gera_evento_rvf(session, rvf, user_name=current_user.name)
            return redirect(url_for('ovr', id=ovr.id))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('index.html',
                               title_page=title_page)
