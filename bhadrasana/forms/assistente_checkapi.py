from flask_wtf import FlaskForm
from wtforms import SelectField, FileField, BooleanField


class CheckApiForm(FlaskForm):
    tipoevento_id = SelectField('Tipo de Evento', default=-1)
    recinto_id = SelectField('Tipo de fonte', default=-1)
    planilha = FileField('Planilha de checagem física')
    eventos_json = FileField('Arquivo de eventos JSON extraído da API Recintos')
    mostrar_colunas = BooleanField('Mostrar todas as colunas das planilhas', default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.recinto_id.choices = [[0, 'Selecione']]
        if kwargs.get('recintos'):
            self.recinto_id.choices.extend(kwargs.get('recintos'))
        self.tipoevento_id.choices = [[0, 'Selecione']]
        if kwargs.get('tiposevento'):
            self.tipoevento_id.choices.extend(kwargs.get('tiposevento'))


class ArquivoApiForm(FlaskForm):
    arquivo = FileField('Arquivo de eventos ZIP extraído da API Recintos')
