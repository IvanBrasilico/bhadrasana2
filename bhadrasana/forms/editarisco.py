from flask_wtf import FlaskForm
from wtforms import SelectField, StringField

from bhadrasana.models.mercantemanager import CAMPOS_RISCO


class EditaRiscoForm(FlaskForm):
    campo = SelectField(u'Tags de usuário',
                              default=[0])
    valor = StringField(u'Valor')
    motivo = StringField(u'Motivo')

def get_edita_risco_form():
    edita_risco_form = EditaRiscoForm()
    edita_risco_form.campo.choices = CAMPOS_RISCO
    return edita_risco_form
