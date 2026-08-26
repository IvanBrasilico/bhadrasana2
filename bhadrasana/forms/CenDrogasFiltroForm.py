from datetime import date

from flask_wtf import FlaskForm
from wtforms import DateField, SubmitField
from wtforms.validators import DataRequired, ValidationError


def primeiro_dia_do_ano():
    return date(date.today().year, 1, 1)


class CenDrogasFiltroForm(FlaskForm):
    datainicio = DateField(
        'Data Início', validators=[DataRequired()], format='%Y-%m-%d',
        default=primeiro_dia_do_ano,
    )
    datafim = DateField(
        'Data Fim', validators=[DataRequired()], format='%Y-%m-%d',
        default=date.today,
    )
    submit = SubmitField('Exportar Excel')

    def validate_datafim(self, field):
        if self.datainicio.data and field.data and field.data < self.datainicio.data:
            raise ValidationError('Data fim não pode ser anterior à data início.')