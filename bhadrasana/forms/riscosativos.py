from flask_wtf import FlaskForm
from wtforms import BooleanField
from wtforms.fields.html5 import DateField


class RiscosAtivosForm(FlaskForm):
    datainicio = DateField(u'Data inicial da pesquisa')
    datafim = DateField(u'Data final da pesquisa')
    portoDestFinal = BooleanField(u'Porto de Destino Final',
                                  default=1)
    consignatario = BooleanField(u'Consignatario',
                                 default=0)
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


class RecintoRiscosAtivosForm(FlaskForm):
    datainicio = DateField(u'Data inicial da pesquisa')
    datafim = DateField(u'Data final da pesquisa')
    cnpjTransportador = BooleanField(u'CNPJ do Transportador',
                                     default=0)
    motorista_cpf = BooleanField(u'CPF do Motorista',
                                 default=0)
    login = BooleanField(u'Login do Operador de Escâner',
                         default=0)
    mercadoria = BooleanField(u'Descrição da mercadoria',
                              default=0)
    portoDescarga = BooleanField(u'Próximo porto de descarga',
                                 default=0)
    destinoCarga = BooleanField(u'Porto - destino de descarga final',
                                default=0)
    imoNavio = BooleanField(u'Nome do Navio',
                            default=0)
