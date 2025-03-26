from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.fields import DateField


class FiltroRVFForm(FlaskForm):
    numeroCEmercante = StringField(u'CE Mercante',
                                   default='')
    numerolote = StringField(u'Contêiner ou Lote',
                             default='')
    datainicio = DateField(u'Data inicial da pesquisa')
    datafim = DateField(u'Data final da pesquisa')
