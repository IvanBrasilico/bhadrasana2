from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import BooleanField

class RiscosAtivosForm(FlaskForm):
    consignatario = BooleanField(u'Consignatario',
                                 default=0)
    embarcador = BooleanField(u'Embarcador',
                              default=0)
    portoorigem = BooleanField(u'Porto de Origem',
                               default=1)
    ncm = BooleanField(u'NCM',
                       default=0)
