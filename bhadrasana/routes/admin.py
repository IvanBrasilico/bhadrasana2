from flask import url_for, request, current_app
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from werkzeug.utils import redirect

from bhadrasana.models import Setor, Usuario
from bhadrasana.models.ovr import Marca, RoteiroOperacaoOVR, TipoEventoOVR


class ProtectedModelView(ModelView):
    def is_accessible(self):
        if current_user.is_authenticated:
            current_app.logger.info('Usuario {} acessando {}'.format(
                current_user.name, request.url))
            return True
        return False

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('login', next=request.url))


class UserModel(ProtectedModelView):
    can_delete = False
    column_hide_backrefs = False
    column_searchable_list = ['nome']
    column_filters = ['setor']
    # column_list = ('cpf', 'nome', 'telegram', 'setor_id')
    # form_columns = ('cpf', 'nome', 'telegram', 'setor_id')


class SetorModel(ProtectedModelView):
    can_delete = False
    column_display_pk = True
    # column_hide_backrefs = False
    column_searchable_list = ['nome']
    # column_filters = ['pai']
    column_list = ('id', 'nome', 'pai_id')
    # form_columns = ('id', 'nome', 'pai_id')
    # inline_models = ['', ]


class MarcasModel(ProtectedModelView):
    column_searchable_list = ['nome']


class RoteirosModel(ProtectedModelView):
    column_filters = ['tipooperacao']
    column_hide_backrefs = False
    column_list = ('tipooperacao', 'get_tipooperacao', 'descricao',
                   'tipoevento', 'ordem', 'quem')


class TipoEventoModel(ProtectedModelView):
    can_delete = False


def admin_app(app, session):
    # set optional bootswatch theme
    app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
    admin = Admin(app, name='Controle de Cargas', template_mode='bootstrap3')
    # Add administrative views here
    admin.add_view(UserModel(Usuario, session))
    admin.add_view(SetorModel(Setor, session))
    admin.add_view(MarcasModel(Marca, session))
    admin.add_view(RoteirosModel(RoteiroOperacaoOVR, session))
    admin.add_view(TipoEventoModel(TipoEventoOVR, session))
