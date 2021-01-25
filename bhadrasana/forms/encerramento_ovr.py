from enum import Enum

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, BooleanField
from wtforms.fields.html5 import DateField


class TipoResultado(Enum):
    #TODO: Hoje o resultado é "Arquivado (sem resultado)" e "Concluído (com resultado)"
    # o detalhamento do resultado é pelos dados. Se houver apreensão de droga,
    # tem um campo específico, se houver apreensão de mercadoria, tem um TG. Para outros
    # casos como recolhimento de DARF, auto de crédito, devolução, etc, o Sistema ainda
    # não tem nada específico. Cabe aqui começar a pensar de, ao menos na tela,
    # já mostrar caminhos para facilitar
    SEMRESULTADO = 1
    TERMODEGUARDA = 2
    TASEDA = 3
    CREDITO = 4
    OUTRO = 5


class EncerramentoOVRForm(FlaskForm):
    tiporesultado = SelectField('Tipo de Resultado', default=-1)
    numerodossie = StringField(u'Número do dossiê no e-Processo', default='')
    numeroprocesso = StringField(u'Número do PAF', default='')
    numerorffp = StringField(u'Número do RFFP', default='')
    responsavel_cpf = SelectField(u'CPF do Responsável pelo Auto/Encerramento'
                                  u' (padrão responsável atual)', default='')
