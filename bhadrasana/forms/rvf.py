from wtforms import StringField, IntegerField, TextAreaField, SelectField, BooleanField
from wtforms.fields.html5 import DateField, TimeField, DecimalField

from bhadrasana.forms import RastreavelForm


class RVFForm(RastreavelForm):
    id = IntegerField('ID')
    ovr_id = IntegerField('ID da OVR relacionada, se houver')
    numeroCEmercante = StringField(u'CE Mercante',
                                   default='')
    numerolote = StringField(u'Número do contêiner, ou do lote do terminal'
                             u' se não houver contêiner', default='')
    descricao = TextAreaField(u'Descrição',
                              render_kw={'rows': 6, 'cols': 100, 'maxlength': 2000},
                              default='')
    descricao_interna = TextAreaField(u'Descrição interna',
                              render_kw={'rows': 6, 'cols': 100, 'maxlength': 2000},
                              default='')
    peso = DecimalField('Peso efetivo da carga verificada em kg', places=2)
    peso_manifestado = DecimalField('Peso Manifesado no Container em kg', places=2)
    volume = DecimalField('Volume efetivo da carga verificada em m3', places=2)
    adata = DateField(u'Data')
    ahora = TimeField(u'Horário')
    inspecaonaoinvasiva = BooleanField('Apenas inspeção não invasiva', default=False)
    marca_id = SelectField('Lista de marcas licenciadas, se existir', default=0)
    infracao_id = SelectField('Lista de possíveis infrações', default=0)
    k9_apontou = BooleanField('K9 acusou presença de droga', default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.marca_id.choices = [(None, 'Selecione')]
        if kwargs.get('marcas'):
            self.marca_id.choices.extend(kwargs.get('marcas'))
        self.infracao_id.choices = [(None, 'Selecione')]
        if kwargs.get('infracoes'):
            self.infracao_id.choices.extend(kwargs.get('infracoes'))


class ImagemRVFForm(RastreavelForm):
    id = IntegerField('ID')
    rvf_id = IntegerField('ID')
    imagem = StringField('_id do GridFS')
    tg_id = IntegerField('ID do TG relacionado, se houver')
    itemtg_id = IntegerField('ID do ItemTG relacionado, se houver')
    descricao = TextAreaField(u'Descrição',
                              render_kw={'rows': 3, 'cols': 80},
                              default='')
    marca_id = SelectField('Marca licenciada, se existir', default=0)
    ordem = IntegerField('ID')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.marca_id.choices = [(None, 'Nenhuma')]
        if kwargs.get('marcas'):
            self.marca_id.choices.extend(kwargs.get('marcas'))


class ApreensaoRVFForm(RastreavelForm):
    id = IntegerField('ID')
    rvf_id = IntegerField('RVF')
    tipo_id = SelectField('Tipo de Apreensão', default=0)
    descricao = StringField(u'Descricao da apreensao',
                            default='')
    peso = DecimalField('Peso efetivo da carga verificada em kg', places=2)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo_id.choices = []
        if kwargs.get('tiposapreensao'):
            self.tipo_id.choices = kwargs.get('tiposapreensao')
