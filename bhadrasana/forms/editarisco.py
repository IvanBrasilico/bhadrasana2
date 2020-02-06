from flask_wtf import FlaskForm
from wtforms import SelectField, StringField


class EditaRiscoForm(FlaskForm):
    campo = SelectField(u'Tags de usuário',
                              default=[0])
    valor = StringField(u'Valor')
    motivo = StringField(u'Motivo')
