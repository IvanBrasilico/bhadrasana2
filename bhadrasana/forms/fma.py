from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField
from wtforms.fields.html5 import DateField, TimeField


class FMAForm(FlaskForm):
    id = IntegerField('ID')
    numero = StringField(u'Numero FMA',
                                   default='')
    ano = StringField(u'Ano',
                                   default='')
    numeroCEmercante = StringField(u'CE Mercante',
                                   default='')
    observacoes = TextAreaField(u'Descrição',
                              render_kw={"rows": 5, "cols": 100},
                              default='')
    adata = DateField(u'Data')
    ahora = TimeField(u'Horário')


class FiltroFMAForm(FlaskForm):
    id = IntegerField('ID')
    numero = StringField(u'Numero FMA',
                                   default='')
    numeroCEmercante = StringField(u'CE Mercante',
                                   default='')
    datainicio = DateField(u'Data inicial da pesquisa')
    datafim = DateField(u'Data final da pesquisa')
