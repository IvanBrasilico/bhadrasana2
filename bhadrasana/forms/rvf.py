from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField
from wtforms.fields.html5 import DateField, TimeField, DecimalField


class RVFForm(FlaskForm):
    id = IntegerField('ID')
    # ovr_id = IntegerField('ID da OVR relacionada, se houver' )
    numeroCEmercante = StringField(u'CE Mercante',
                                   default='')
    descricao = TextAreaField(u'Descrição',
                              render_kw={'rows': 5, 'cols': 100},
                              default='')
    peso = DecimalField('Peso efetivo da carga verificada em kg', places=2)
    volume = DecimalField('Volume efetivo da carga verificada em m3', places=2)
    adata = DateField(u'Data')
    ahora = TimeField(u'Horário')
