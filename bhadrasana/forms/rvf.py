from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField
from wtforms.fields.html5 import DateTimeField


class RVFForm(FlaskForm):
    id = IntegerField('ID')
    numeroCEmercante = StringField(u'CE Mercante',
                                   default='')
    descricao = TextAreaField(u'Descrição',
                              render_kw={"rows": 5, "cols": 100},
                              default='')
    datahora = DateTimeField(u'Data e horário')
