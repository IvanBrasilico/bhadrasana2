from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField
from wtforms.fields.html5 import DateField, TimeField


class RVFForm(FlaskForm):
    id = IntegerField('ID')
    numeroCEmercante = StringField(u'CE Mercante',
                                   default='')
    descricao = TextAreaField(u'Descrição',
                              render_kw={"rows": 5, "cols": 100},
                              default='')
    data = DateField(u'Data')
    hora = TimeField(u'Horário')
