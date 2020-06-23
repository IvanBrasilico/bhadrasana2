from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from bhadrasana.models import Setor, Usuario
from bhadrasana.models.ovr import Marca, RoteiroOperacaoOVR


class UserModel(ModelView):
    column_display_pk = True
    column_list = ('cpf', 'nome', 'telegram', 'setor_id')
    form_columns = ('cpf', 'nome', 'telegram', 'setor_id')


class SetorModel(ModelView):
    column_display_pk = True
    column_list = ('id', 'nome', 'pai_id')
    form_columns = ('id', 'nome', 'pai_id')
    # inline_models = ['', ]


class MarcasModel(ModelView):
    column_searchable_list = ['nome']


class RoteirosModel(ModelView):
    column_filters = ['tipooperacao']


def admin_app(app, session):
    # set optional bootswatch theme
    app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
    admin = Admin(app, name='Controle de Cargas', template_mode='bootstrap3')
    # Add administrative views here
    admin.add_view(UserModel(Usuario, session))
    admin.add_view(SetorModel(Setor, session))
    admin.add_view(MarcasModel(Marca, session))
    admin.add_view(RoteirosModel(RoteiroOperacaoOVR, session))
