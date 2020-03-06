from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from bhadrasana.models import Setor, Usuario


def admin_app(app, session):
    # set optional bootswatch theme
    app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
    admin = Admin(app, name='Ficha de Carga', template_mode='bootstrap3')
    # Add administrative views here
    admin.add_view(ModelView(Usuario, session))
    admin.add_view(ModelView(Setor, session))
