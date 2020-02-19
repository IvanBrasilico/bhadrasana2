from flask_wtf import FlaskForm
from bhadrasana.models.dta import Enumerado
from wtforms import IntegerField, TextAreaField, SelectField, BooleanField


class AnexoForm(FlaskForm):
    id = IntegerField('ID')
    dta_id = IntegerField('OVR')
    observacoes = TextAreaField(u'Observações',
                                render_kw={"rows": 5, "cols": 100},
                                default='')
    temconteudo = BooleanField(u'Desmarcar se arquivo vazio',
                               default=1)
    qualidade = IntegerField(u'Qualidade da digitalização (0 a 10)',
                             default='')
    tipoconteudo = SelectField('Enumerado de Tipo do Conteúdo', default=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipoconteudo.choices = Enumerado.tipoConteudo()
        self.marca_id.choices = [(0, 'Nenhuma')]
        if kwargs.get('marcas'):
            self.marca_id.choices.extend(kwargs.get('marcas'))
