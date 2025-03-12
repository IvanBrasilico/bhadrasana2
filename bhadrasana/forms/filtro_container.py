from datetime import date, timedelta

from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.fields.html5 import DateField


class FiltroContainerForm(FlaskForm):
    numerolote = StringField(u'Número do Contêiner',
                             default='')
    datainicio = DateField(u'Data inicial da pesquisa')
    datafim = DateField(u'Data final da pesquisa')

    def __init__(self, *args, **kwargs):
        super(FiltroContainerForm, self).__init__(*args, **kwargs)

        # Set defaults only if values are not provided
        if not self.datainicio.data:
            self.datainicio.data = date.today() - timedelta(days=360)

        if not self.datafim.data:
            self.datafim.data = date.today()


class FiltroCEForm(FlaskForm):
    numeroCEmercante = StringField(u'Número do CE',
                                   default='')


class FiltroDUEForm(FlaskForm):
    numero = StringField(u'Número da DUE',
                         default='')
