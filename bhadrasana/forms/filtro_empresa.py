from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.fields.html5 import DateField


class FiltroEmpresaForm(FlaskForm):
    cnpj = StringField(u'Número do CNPJ',
                       default='')
    nome = StringField(u'Nome',
                       default='')
    datainicio = DateField(u'Data inicial da pesquisa')
    datafim = DateField(u'Data final da pesquisa')
