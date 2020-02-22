from bhadrasana.models.ovr import Enumerado
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SelectField
from wtforms.fields.html5 import DateField, TimeField


class OVRForm(FlaskForm):
    id = IntegerField('ID')
    tipooperacao = SelectField(u'Tipo de Operação')
    recinto_id = SelectField(u'Recinto')
    tipoevento_id = SelectField(u'Tipo de Evento', render_kw={'disabled': ''})
    fase = SelectField(u'Fase', render_kw={'disabled': ''})
    numero = StringField(u'Numero OVR',
                         default='')
    ano = StringField(u'Ano',
                      default='')
    numeroCEmercante = StringField(u'CE Mercante',
                                   default='')
    observacoes = TextAreaField(u'Observações',
                                render_kw={"rows": 3, "cols": 100},
                                default='')
    adata = DateField(u'Data')
    ahora = TimeField(u'Horário')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipooperacao.choices = Enumerado.tipoOperacao()
        self.fase.choices = Enumerado.faseOVR()
        self.tipoevento_id.choices = []
        if kwargs.get('tiposeventos'):
            self.tipoevento_id.choices.extend(kwargs.get('tiposeventos'))
        self.recinto_id.choices = []
        if kwargs.get('recintos'):
            self.recinto_id.choices.extend(kwargs.get('recintos'))
        datahora = kwargs.get('datahora')
        if datahora:
            self.adata.data = datahora.date()
            self.ahora.data = datahora.time()


class FiltroOVRForm(FlaskForm):
    id = IntegerField('ID')
    tipooperacao = SelectField('tipooperacao', default=-1)
    fase = SelectField('fase', default=-1)
    recinto_id = SelectField('recinto_id', default=0)
    tipoevento_id = SelectField('tipoevento', default=0)
    numero = StringField(u'Numero OVR',
                         default='')
    numeroCEmercante = StringField(u'CE Mercante',
                                   default='')
    datainicio = DateField(u'Data inicial da pesquisa')
    datafim = DateField(u'Data final da pesquisa')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipooperacao.choices = [(None, 'Selecione'), *Enumerado.tipoOperacao()]
        # self.fase.choices = Enumerado.faseOVR()
        self.fase.choices = [(None, 'Selecione'), *Enumerado.faseOVR()]
        self.tipoevento_id.choices = [(None, 'Selecione')]
        if kwargs.get('tiposeventos'):
            self.tipoevento_id.choices = [(None, 'Selecione'), *kwargs.get('tiposeventos')]
        self.recinto_id.choices = [(None, 'Selecione')]
        if kwargs.get('recinto_id'):
            self.recinto_id.choices.extend(kwargs.get('recinto_id'))


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
        self.tipoevento_id.choices = []
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
        self.tipoprocesso_id.choices = []
        if kwargs.get('tiposprocesso'):
            self.tipoprocesso_id.choices.extend(kwargs.get('tiposprocesso'))


class ResponsavelOVRForm(FlaskForm):
    ovr_id = IntegerField('OVR')
    responsavel = SelectField('CPF do Responsável')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.responsavel.choices = []
        if kwargs.get('responsaveis'):
            self.responsavel.choices.extend(kwargs.get('responsaveis'))


class TGOVRForm(FlaskForm):
    id = IntegerField('ID')
    tg_id = IntegerField('TG')
    numerolote = StringField(u'Número do contêiner, ou do lote do terminal'
                             u' se não houver contêiner', default='')
    descricao = TextAreaField(u'Descrição',
                              render_kw={"rows": 5, "cols": 100},
                              default='')
    unidadedemedida = SelectField('Unidade de Medida', default=1)
    qtde = StringField(u'Quantidade',
                       default='')
    valor = StringField(u'Valor unitário',
                        default='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unidadedemedida.choices = Enumerado.unidadeMedida()


class ItemTGForm(FlaskForm):
    id = IntegerField('ID')
    tg_id = IntegerField('TG')
    descricao = TextAreaField(u'Descrição',
                              render_kw={"rows": 5, "cols": 100},
                              default='')
    unidadedemedida = SelectField('Unidade de Medida', default=1)
    qtde = StringField(u'Quantidade',
                       default='')
    valor = StringField(u'Valor unitário',
                        default='')
    ncm = StringField(u'Código Subitem NCM',
                      default='')
    marca_id = SelectField('Marca licenciada, se existir', default=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unidadedemedida.choices = Enumerado.unidadeMedida()
        self.marca_id.choices = [(0, 'Nenhuma')]
        if kwargs.get('marcas'):
            self.marca_id.choices.extend(kwargs.get('marcas'))
