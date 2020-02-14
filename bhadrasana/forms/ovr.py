from bhadrasana.models.ovrmanager import Enumerado
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SelectField
from wtforms.fields.html5 import DateField, TimeField


class OVRForm(FlaskForm):
    id = IntegerField('ID')
    numero = StringField(u'Numero OVR',
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        datahora = kwargs.get('datahora')
        if datahora:
            self.adata.data = datahora.date()
            self.ahora.data = datahora.time()


class FiltroOVRForm(FlaskForm):
    id = IntegerField('ID')
    tipoevento = SelectField('tipoevento', default=0)
    fase = SelectField('fase', default=0)
    numero = StringField(u'Numero OVR',
                         default='')
    numeroCEmercante = StringField(u'CE Mercante',
                                   default='')
    datainicio = DateField(u'Data inicial da pesquisa')
    datafim = DateField(u'Data final da pesquisa')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fase.choices = Enumerado.faseOVR()
        if kwargs.get('tiposeventos'):
            self.tipoevento.choices = kwargs.get('tiposeventos')


class HistoricoOVRForm(FlaskForm):
    id = IntegerField('ID')
    ovr_id = IntegerField('OVR')
    tipoevento_id = SelectField('tipoevento', default=0)
    user_name = StringField(u'Nome do usuário',
                            default='')
    motivo = StringField(u'Nome do usuário',
                         default='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get('tiposeventos'):
            self.tipoevento_id.choices = kwargs.get('tiposeventos')


class ProcessoOVRForm(FlaskForm):
    id = IntegerField('ID')
    ovr_id = IntegerField('OVR')
    tipoprocesso_id = SelectField('tipoprocesso', default=0)
    numero = StringField(u'Número do processo',
                         default='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get('tiposprocesso'):
            self.tipoprocesso_id.choices = kwargs.get('tiposprocesso')
