from flask import url_for, request
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from werkzeug.utils import redirect

from bhadrasana.models import Enumerado as ModelEnumerado
from bhadrasana.models import Setor, Usuario, PerfilUsuario
from bhadrasana.models.ovr import Marca, RoteiroOperacaoOVR, TipoEventoOVR, Enumerado


class ProtectedModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('login', next=request.url))


class UsuarioModel(ProtectedModelView):
    can_delete = False
    column_hide_backrefs = False
    column_searchable_list = ['nome']
    column_filters = ['setor']
    column_list = ('cpf', 'nome', 'telegram', 'setor', 'perfis')
    form_columns = ('cpf', 'nome', 'telegram', 'setor')


class PerfilUsuarioModel(ProtectedModelView):
    column_hide_backrefs = False
    column_searchable_list = ['cpf', 'perfil']
    column_filters = ['cpf', 'perfil']
    column_list = ('cpf', 'perfil', 'perfil_descricao')
    form_choices = {'perfil': ModelEnumerado.perfilAcesso()}

    def validate_form(self, form):
        form.perfil.data = int(form.perfil.data)
        return super(PerfilUsuarioModel, self).validate_form(form)

    def on_form_prefill(self, form, id):
        form.perfil.data = str(form.perfil.data)


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
    column_list = ('tipooperacao', 'descricao_tipooperacao', 'descricao',
                   'tipoevento', 'ordem', 'quem')
    form_choices = {'tipooperacao': Enumerado.tipoOperacao()}

    def validate_form(self, form):
        form.tipooperacao.data = int(form.tipooperacao.data)
        return super(RoteirosModel, self).validate_form(form)

    def on_form_prefill(self, form, id):
        form.tipooperacao.data = str(form.tipooperacao.data)


class TipoEventoModel(ProtectedModelView):
    can_delete = False
    column_list = ('nome', 'descricao', 'descricao_fase', 'eventoespecial')
    form_columns = ('nome', 'descricao', 'fase')
    form_choices = {'fase': Enumerado.faseOVR()}

    def validate_form(self, form):
        form.fase.data = int(form.fase.data)
        return super(TipoEventoModel, self).validate_form(form)

    def on_form_prefill(self, form, id):
        form.fase.data = str(form.fase.data)


def admin_app(app, session):
    # set optional bootswatch theme
    app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
    admin = Admin(app, name='Controle de Cargas', template_mode='bootstrap3')
    # Add administrative views here
    admin.add_view(UsuarioModel(Usuario, session))
    admin.add_view(PerfilUsuarioModel(PerfilUsuario, session))
    admin.add_view(SetorModel(Setor, session))
    admin.add_view(MarcasModel(Marca, session))
    admin.add_view(RoteirosModel(RoteiroOperacaoOVR, session))
    admin.add_view(TipoEventoModel(TipoEventoOVR, session))
