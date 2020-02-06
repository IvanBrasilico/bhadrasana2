from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import BooleanField

class RiscosAtivosForm(FlaskForm):
    consignatario = BooleanField(u'Consignatario',
                                 default=1)
    portoOrigemCarga = BooleanField(u'Porto de Origem',
                               default=0)
    ncm = BooleanField(u'NCM',
                       default=0)
    codigoConteiner = BooleanField(u'NCM',
                       default=0)
    descricao = BooleanField(u'NCM',
                       default=0)
    embarcador = BooleanField(u'Embarcador',
                              default=0)
