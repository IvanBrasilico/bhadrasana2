from flask import url_for, request
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink
from flask_login import current_user
from werkzeug.utils import redirect

from bhadrasana.models import Enumerado as ModelEnumerado, usuario_tem_perfil,\
    perfilAcesso, get_usuario_logado
from bhadrasana.models import Setor, Usuario, PerfilUsuario
from bhadrasana.models.ovr import Marca, RoteiroOperacaoOVR, TipoEventoOVR, Enumerado


class ProtectedModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('login', next=request.url))


class CadastradorModelView(ProtectedModelView):
    def is_accessible(self):
        if current_user.is_authenticated:
            result = usuario_tem_perfil(
                self.session,
                current_user.id,
                ModelEnumerado.get_id(perfilAcesso, 'Cadastrador')
            )
            # print('*****************' + str(result))
            return result
        return False


class SupervisorModelView(ProtectedModelView):
    def is_accessible(self):
        if current_user.is_authenticated:
            return usuario_tem_perfil(
                self.session,
                current_user.id,
                ModelEnumerado.get_id(perfilAcesso, 'Supervisor')
            )
        return False


class UsuarioModel(CadastradorModelView):
    can_delete = False
    column_hide_backrefs = False
    column_searchable_list = ['nome']
    column_filters = ['setor']
    column_list = ('cpf', 'nome', 'telegram', 'setor', 'perfis')
    form_columns = ('cpf', 'nome', 'telegram', 'setor')


class PerfilUsuarioModel(CadastradorModelView):
    column_hide_backrefs = False
    column_searchable_list = ['cpf', 'perfil']
    column_filters = ['cpf', 'perfil']
    column_list = ('cpf', 'perfil', 'perfil_descricao')
    form_choices = {'perfil': ModelEnumerado.perfilAcesso()}

    def validate_form(self, form):
        try:
            form.perfil.data = int(form.perfil.data)
        except AttributeError:  # Para não dar erro em exclusáo (DeleteForm)
            pass
        return super(PerfilUsuarioModel, self).validate_form(form)

    def on_form_prefill(self, form, id):
        form.perfil.data = str(form.perfil.data)


class SetorModel(SupervisorModelView):
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


class RoteirosModel(SupervisorModelView):
    column_filters = ['tipooperacao']
    column_hide_backrefs = False
    column_list = ('tipooperacao', 'descricao_tipooperacao', 'descricao',
                   'tipoevento', 'ordem', 'quem')
    form_choices = {'tipooperacao': Enumerado.tipoOperacao()}

    def validate_form(self, form):
        try:
            form.tipooperacao.data = int(form.tipooperacao.data)
        except AttributeError:  # Para não dar erro em exclusáo (DeleteForm)
            pass
        return super(RoteirosModel, self).validate_form(form)

    def on_form_prefill(self, form, id):
        form.tipooperacao.data = str(form.tipooperacao.data)


class TipoEventoModel(SupervisorModelView):
    can_delete = False
    column_list = ('nome', 'descricao', 'descricao_fase', 'eventoespecial')
    form_columns = ('nome', 'descricao', 'fase')
    form_choices = {'fase': Enumerado.faseOVR()}

    def validate_form(self, form):
        form.fase.data = int(form.fase.data)
        return super(TipoEventoModel, self).validate_form(form)

    def on_form_prefill(self, form, id):
        form.fase.data = str(form.fase.data)


class LogoutMenuLink(MenuLink):
    def is_accessible(self):
        return current_user.is_authenticated


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

    admin.add_link(LogoutMenuLink(name='Janela principal',
                                  url='/bhadrasana2', category='Ir para'))
    if current_user and current_user.is_authenticated:
        user = get_usuario_logado(session, current_user.id)
        admin.add_link(LogoutMenuLink(name='Sair (%s)' % user.nome,
                                      url=url_for('commons.logout'), category='Ir para'))
