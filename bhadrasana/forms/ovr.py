from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SelectField, \
    validators, SelectMultipleField, BooleanField
from wtforms.fields.html5 import DateField, TimeField, DecimalField
from wtforms.validators import optional

from bhadrasana.forms.exibicao_ovr import TipoExibicao
from bhadrasana.models.ovr import Enumerado, TipoResultado
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
    dataentrada = DateField(u'Data')
    adata = DateField(u'Data')
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
    responsavel_cpf = SelectField(u'CPF do Responsável Atual', default='')
    cpfauditorresponsavel = SelectField(u'CPF do Auditor designado', default='')
    teveevento = SelectField('tipoevento', default='')
    usuarioevento = SelectField('tipoevento', default=None)
    tipoexibicao = SelectField('Campos a serem exibidos na tela', default=1)
    agruparpor = SelectField('tipoevento', default=None)
    temapreensao = BooleanField(default=False)
    temtg = BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipooperacao.choices = [(None, 'Selecione'),
                                     *Enumerado.tipoOperacao()]
        # self.fase.choices = Enumerado.faseOVR()
        self.fase.choices = [(None, 'Selecione'), *Enumerado.faseOVR()]
        self.tipoevento_id.choices = [(None, 'Selecione')]
        self.teveevento.choices = [(None, 'Selecione')]
        if kwargs.get('tiposeventos'):
            self.tipoevento_id.choices = [(None, 'Selecione'), *kwargs.get('tiposeventos')]
            self.teveevento.choices = [(None, 'Selecione'), *kwargs.get('tiposeventos')]
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
        self.responsavel_cpf.choices = [(None, 'Selecione')]
        self.usuarioevento.choices = [(None, 'Selecione')]
        if kwargs.get('responsaveis'):
            self.responsavel_cpf.choices.extend(kwargs.get('responsaveis'))
            self.usuarioevento.choices.extend(kwargs.get('responsaveis'))
        self.cpfauditorresponsavel.choices = [(None, 'Selecione')]
        if kwargs.get('auditores'):
            self.cpfauditorresponsavel.choices.extend(kwargs.get('auditores'))
        self.tipoexibicao.choices = [(tipo.value, tipo.name) for tipo in TipoExibicao]
        self.agruparpor.choices = ((None, 'Nenhum'), ('fase', 'Fase'),
                                   ('responsavel_cpf', 'Responsável atual'),
                                   ('cpfauditorresponsavel', 'Auditor Responsável'),)


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
    meramente_informativo = BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipoevento_id.choices = []
        if kwargs.get('tiposeventos'):
            self.tipoevento_id.choices = kwargs.get('tiposeventos')
        self.user_name.choices = []
        if kwargs.get('responsaveis'):
            self.user_name.choices.extend(kwargs.get('responsaveis'))


class RastreavelForm(FlaskForm):
    user_name = StringField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_name.data = current_user.name


class ProcessoOVRForm(RastreavelForm):
    id = IntegerField('ID')
    ovr_id = IntegerField('OVR')
    tipoprocesso_id = SelectField('tipoprocesso', default=0)
    numero_processo = StringField(u'Número do processo',
                                  default='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipoprocesso_id.choices = []
        if kwargs.get('tiposprocesso'):
            self.tipoprocesso_id.choices.extend(kwargs.get('tiposprocesso'))


class ResultadoOVRForm(RastreavelForm):
    id = IntegerField('ID')
    ovr_id = IntegerField('OVR')
    cpf_auditor = StringField(u'CPF do Auditor',
                                  default='')
    tipo_resultado = SelectField('tipoprocesso', default=0)
    valor = StringField(u'Valor',
                                  default='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo_resultado.choices = [(i.value, i.name) for i in TipoResultado]


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
    orfas = BooleanField('Exibir Fichas órfãs (sem responsável)')
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
    oid = IntegerField('ID do objeto que será fonte para preenchimento do docx')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docx_id.choices = []
        if kwargs.get('lista_docx'):
            self.docx_id.choices.extend(kwargs.get('lista_docx'))


class ModeloDocxForm(FlaskForm):
    id = IntegerField()
    filename = StringField()
    fonte_docx_id = SelectField('Tipo de fonte', default=-1)
    oid = IntegerField('ID do objeto que será fonte para preenchimento do docx')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fonte_docx_id.choices = [(tipo.value, tipo.name) for tipo in FonteDocx]


class EscaneamentoOperadorForm(FlaskForm):
    qtde = IntegerField('Qtde de contêineres',
                        [validators.NumberRange(min=1, max=100)],
                        default=10)
    lista_recintos = StringField()
    recinto_id = SelectField(u'Recinto')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.recinto_id.choices = [[0, 'Selecione']]
        if kwargs.get('recintos'):
            self.recinto_id.choices.extend(kwargs.get('recintos'))


class FiltroAbasForm(FlaskForm):
    datainicio = DateField(u'Data inicial da pesquisa')
    datafim = DateField(u'Data final da pesquisa')
    setor_id = SelectField('Setores', validators=[optional()])
    tipooperacao_id = SelectMultipleField('TipoOperacao', default=[99], coerce=int)
    flags_id = SelectMultipleField('Flags / Alertas', default=[99], coerce=int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setor_id.choices = [(None, 'Selecione')]
        if kwargs.get('setores'):
            self.setor_id.choices.extend(kwargs.get('setores'))
        self.tipooperacao_id.choices = [(99, 'Todos'), *Enumerado.tipoOperacao()]
        self.tipooperacao_id.default = [99]
        if kwargs.get('flags'):
            self.flags_id.choices = [(99, 'Todos'), *kwargs.get('flags')]
            self.flags_id.default = [99]
