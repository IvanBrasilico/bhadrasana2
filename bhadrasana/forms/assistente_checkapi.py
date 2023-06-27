from flask_wtf import FlaskForm
from wtforms import SelectField


class CheckApiForm(FlaskForm):
    tipoevento_id = SelectField('Tipo de Evento', default=-1)
    recinto_id = SelectField('Tipo de fonte', default=-1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.recinto_id.choices = [[0, 'Selecione']]
        if kwargs.get('recintos'):
            self.recinto_id.choices.extend(kwargs.get('recintos'))
        self.tipoevento_id.choices = [[0, 'Selecione']]
        if kwargs.get('tiposevento'):
            self.tipoevento_id.choices.extend(kwargs.get('tiposevento'))
