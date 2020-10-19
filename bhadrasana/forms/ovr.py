from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SelectField
from wtforms.fields.html5 import DateField, TimeField, DecimalField

from bhadrasana.forms.exibicao_ovr import TipoExibicao
from bhadrasana.models.ovr import Enumerado
from bhadrasana.models.ovr_dict_repr import FonteDocx


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
                                render_kw={'rows': 3, 'cols': 100, 'maxlength': 1000},
                                default='')
    numerodeclaracao = StringField(u'DUE ou DUIMP ou DTA',
                                   default='')
    adata = DateField(u'Data')
    dataentrada = DateField(u'Data')
    ahora = TimeField(u'Horário')
    user_name = StringField()
    user_descricao = StringField(default='')
    cnpj_fiscalizado = StringField()
    nome_fiscalizado = StringField(default='')
    setor_descricao = StringField(default='')
    auditor_descricao = StringField(default='')

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
    recinto_id = SelectField('recinto_id', default=-1)
    tipoevento_id = SelectField('tipoevento', default=-1)
    flag_id = SelectField('flags', default=-1)
    infracao_id = SelectField('infracoes', default=-1)
    numero = StringField(u'Numero OVR',
                         default='')
    numeroCEmercante = StringField(u'CE Mercante',
                                   default='')
    numerodeclaracao = StringField(u'DUE ou DUIMP ou DTA',
                                   default='')
    datainicio = DateField(u'Data inicial da pesquisa')
    datafim = DateField(u'Data final da pesquisa')
    cnpj_fiscalizado = StringField(u'CNPJ do Fiscalizado',
                                   default='')
    numeroprocesso = StringField(u'Número de processo informado na Ficha',
                                 default='')
    setor_id = SelectField('Setores')
    tipoexibicao = SelectField('Campos a serem exibidos na tela', default=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipooperacao.choices = [(None, 'Selecione'),
                                     *Enumerado.tipoOperacao()]
        # self.fase.choices = Enumerado.faseOVR()
        self.fase.choices = [(None, 'Selecione'), *Enumerado.faseOVR()]
        self.tipoevento_id.choices = [(None, 'Selecione')]
        if kwargs.get('tiposeventos'):
            self.tipoevento_id.choices = [(None, 'Selecione'),
                                          *kwargs.get('tiposeventos')]
        self.recinto_id.choices = [(None, 'Selecione')]
        if kwargs.get('recintos'):
            self.recinto_id.choices.extend(kwargs.get('recintos'))
        self.flag_id.choices = [(None, 'Selecione')]
        if kwargs.get('flags'):
            self.flag_id.choices.extend(kwargs.get('flags'))
        self.infracao_id.choices = [(None, 'Selecione')]
        if kwargs.get('infracoes'):
            self.infracao_id.choices.extend(kwargs.get('infracoes'))
        self.setor_id.choices = [(None, 'Selecione')]
        if kwargs.get('setores'):
            self.setor_id.choices.extend(kwargs.get('setores'))
        self.tipoexibicao.choices = [(tipo.value, tipo.name) for tipo in TipoExibicao]


class FiltroRelatorioForm(FlaskForm):
    relatorio = SelectField('Relatórios disponiveis', default=-1)
    datainicio = DateField(u'Data inicial da pesquisa')
    datafim = DateField(u'Data final da pesquisa')
    setor_id = SelectField('Setores')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.relatorio.choices = [(None, 'Selecione')]
        if kwargs.get('relatorios'):
            self.relatorio.choices = [(None, 'Selecione'),
                                      *kwargs.get('relatorios')]
        self.setor_id.choices = []
        if kwargs.get('setores'):
            self.setor_id.choices = kwargs.get('setores')


class HistoricoOVRForm(FlaskForm):
    id = IntegerField('ID')
    ovr_id = IntegerField('OVR')
    tipoevento_id = SelectField('tipoevento', default=0)
    user_name = SelectField('CPF do Responsável')
    motivo = StringField(u'Nome do usuário',
                         render_kw={'rows': 1, 'cols': 200, 'maxlength': 200},
                         default='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipoevento_id.choices = []
        if kwargs.get('tiposeventos'):
            self.tipoevento_id.choices = kwargs.get('tiposeventos')
        self.user_name.choices = []
        if kwargs.get('responsaveis'):
            self.user_name.choices.extend(kwargs.get('responsaveis'))


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


class SetorOVRForm(FlaskForm):
    ovr_id = IntegerField('OVR')
    setor = SelectField('Novo Setor')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setor.choices = []
        if kwargs.get('setores'):
            self.setor.choices = kwargs.get('setores')


class TGOVRForm(FlaskForm):
    id = IntegerField('ID')
    ovr_id = IntegerField('OVR')
    numerolote = StringField(u'Número do contêiner, ou do lote do terminal'
                             u' se não houver contêiner', default='')
    descricao = TextAreaField(u'Descrição',
                              render_kw={'rows': 2, 'cols': 100, 'maxlength': 500},
                              default='')
    unidadedemedida = SelectField('Unidade de Medida', default=1)
    qtde = DecimalField(u'Quantidade total',
                        places=2)
    valor = DecimalField(u'Valor total',
                         places=2)
    tipomercadoria_id = SelectField('Unidade de Medida', default=0)
    numerotg = StringField(u'Número do Termo de Guarda', default='')
    afrfb = SelectField(u'CPF do AFRFB Responsável')
    identificacao = StringField(u'Identificação(marca) da carga', default='')
    observacoes = TextAreaField(u'Observações',
                                render_kw={'rows': 2, 'cols': 100, 'maxlength': 500},
                                default='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unidadedemedida.choices = Enumerado.unidadeMedida()
        self.tipomercadoria_id.choices = []
        if kwargs.get('tiposmercadoria'):
            self.tipomercadoria_id.choices.extend(kwargs.get('tiposmercadoria'))
        self.afrfb.choices = []
        if kwargs.get('lista_afrfb'):
            self.afrfb.choices.extend(kwargs.get('lista_afrfb'))


class ItemTGForm(FlaskForm):
    id = IntegerField('ID')
    tg_id = IntegerField('TG')
    numero = IntegerField('numero')
    descricao = TextAreaField(u'Descrição',
                              render_kw={'rows': 5, 'cols': 100, 'maxlength': 500},
                              default='')
    unidadedemedida = SelectField('Unidade de Medida', default=1)
    qtde = DecimalField(u'Quantidade total',
                        places=2)
    valor = DecimalField(u'Valor unitário',
                         places=2)
    ncm = StringField(u'Código Subitem NCM',
                      default='')
    marca_id = SelectField('Marca licenciada, se existir', default=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unidadedemedida.choices = Enumerado.unidadeMedida()
        self.marca_id.choices = [(None, 'Nenhuma')]
        if kwargs.get('marcas'):
            self.marca_id.choices.extend(kwargs.get('marcas'))


class FiltroMinhasOVRsForm(FlaskForm):
    datainicio = DateField(u'Data inicial da pesquisa')
    datafim = DateField(u'Data final da pesquisa')
    tipoexibicao = SelectField('Campos a serem exibidos na tela', default=1)
    activetab = StringField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipoexibicao.choices = [(tipo.value, tipo.name) for tipo in TipoExibicao]


class OKRObjectiveForm(FlaskForm):
    id = IntegerField()
    inicio = DateField(u'Data inicial da pesquisa')
    fim = DateField(u'Data final da pesquisa')
    nome = StringField()
    setor_id = SelectField('Setores')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get('setores'):
            self.setor_id.choices = kwargs.get('setores')


class OKRMetaForm(FlaskForm):
    id = IntegerField()
    objective_id = IntegerField()
    result_id = SelectField('OKRResult')
    ameta = IntegerField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get('key_results'):
            self.result_id.choices = kwargs.get('key_results')


class FiltroDocxForm(FlaskForm):
    docx_id = SelectField('Documentos disponiveis', default=-1)
    fonte = SelectField('Tipo de fonte', default=-1)
    fonte_id = IntegerField('ID do objeto que será fonte para preenchimento do docx')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docx_id.choices = []
        if kwargs.get('lista_docx'):
            self.docx_id.choices.extend(kwargs.get('lista_docx'))
        self.fonte.choices = [(tipo.value, tipo.name) for tipo in FonteDocx]


class ModeloDocxForm(FlaskForm):
    id = IntegerField()
    filename = StringField()
