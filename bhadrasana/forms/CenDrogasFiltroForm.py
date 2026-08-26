from flask_wtf import FlaskForm
from wtforms import DateField, SubmitField
from wtforms.validators import DataRequired, ValidationError


class CenDrogasFiltroForm(FlaskForm):
    datainicio = DateField('Data Início', validators=[DataRequired()], format='%Y-%m-%d')
    datafim = DateField('Data Fim', validators=[DataRequired()], format='%Y-%m-%d')
    submit = SubmitField('Exportar Excel')

    def validate_datafim(self, field):
        if self.datainicio.data and field.data and field.data < self.datainicio.data:
            raise ValidationError('Data fim não pode ser anterior à data início.')