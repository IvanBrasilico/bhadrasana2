from flask_wtf import FlaskForm
from wtforms import BooleanField
from wtforms.fields.html5 import DateField


class RiscosForm(FlaskForm):
    datainicio = DateField(u'Data inicial da pesquisa')
    datafim = DateField(u'Data final da pesquisa')
    operadorOU = BooleanField(u'Utilizar Operador OU no filtro',
                              default=0)


class RiscosAtivosForm(RiscosForm):
    # Campos ativadores são campos sem valores específicos a alimentar, simplesmente "ligam"
    # um filtro pré-especificado (Ex. Filtrar somente BLs de tipo Master e único (tipoBL in (10, 12, 15))
    campos_ativadores = ['matriz_corad', 'sem_matriz_corad', 'house_unico']
    portoDestFinal = BooleanField(u'Porto de Destino Final',
                                  default=1)
    consignatario = BooleanField(u'Consignatario',
                                 default=0)
    portoOrigemCarga = BooleanField(u'Porto de Origem',
                                    default=0)
    identificacaoNCM = BooleanField(u'NCM',
                                    default=0)
    codigoConteiner = BooleanField(u'NCM',
                                   default=0)
    descricao = BooleanField(u'NCM',
                             default=0)
    embarcador = BooleanField(u'Embarcador',
                              default=0)
    recinto = BooleanField(u'Recinto',
                           default=0)
    matriz_corad = BooleanField(u'Alto Risco Matriz CORAD',
                                default=0)
    sem_matriz_corad = BooleanField(u'Não consta da Matriz CORAD',
                                    default=0)
    house_unico = BooleanField(u'Somente BLs House ou únicos',
                               default=1)


class RecintoRiscosAtivosForm(RiscosForm):
    # Campos ativadores são campos sem valores específicos a alimentar, simplesmente "ligam"
    # um filtro pré-especificado (Ex. Filtrar somente BLs de tipo Master e único (tipoBL in (10, 12, 15))
    campos_ativadores = []
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
