from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField


class RVFForm(FlaskForm):
    id = IntegerField('ID')
    numeroCEmercante = StringField(u'CE Mercante',
                                   default='')
    descricao = TextAreaField(u'Descrição',
                              render_kw={"rows": 5, "cols": 100},
                              default='')
