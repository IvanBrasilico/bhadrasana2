from bhadrasana.models.fmamanager import Enumerado
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SelectField
from wtforms.fields.html5 import DateField, TimeField


class FMAForm(FlaskForm):
    id = IntegerField('ID')
    numero = StringField(u'Numero FMA',
                         default='')
    ano = StringField(u'Ano',
                      default='')
    numeroCEmercante = StringField(u'CE Mercante',
                                   default='')
    observacoes = TextAreaField(u'Descrição',
                                render_kw={'rows': 5, 'cols': 100},
                                default='')
    adata = DateField(u'Data')
    ahora = TimeField(u'Horário')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        datahora = kwargs.get('datahora')
        if datahora:
            self.adata.data = datahora.date()
            self.ahora.data = datahora.time()


class FiltroFMAForm(FlaskForm):
    id = IntegerField('ID')
    status = SelectField('status', default=0)
    fase = SelectField('fase', default=0)
    numero = StringField(u'Numero FMA',
                         default='')
    numeroCEmercante = StringField(u'CE Mercante',
                                   default='')
    datainicio = DateField(u'Data inicial da pesquisa')
    datafim = DateField(u'Data final da pesquisa')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status.choices = [(None, 'Selecione'), *Enumerado.tipoStatusFMA()]
        self.fase.choices = Enumerado.faseOVR()


class HistoricoFMAForm(FlaskForm):
    id = IntegerField('ID')
    fma_id = IntegerField('FMA')
    status = SelectField('status', default=0)
    user_name = StringField(u'Nome do usuário',
                            default='')
    motivo = StringField(u'Nome do usuário',
                         default='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status.choices = Enumerado.tipoStatusFMA()
