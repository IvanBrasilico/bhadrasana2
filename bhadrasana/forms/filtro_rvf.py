from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DateTimeField



class FiltroRVFForm(FlaskForm):
    id = IntegerField('ID')
    ce = StringField(u'CE Mercante',
                                   default='')
    datainicio = DateTimeField(u'Data inicial da pesquisa')
    datafim = DateTimeField(u'Data final da pesquisa')
