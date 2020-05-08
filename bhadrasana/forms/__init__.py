from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import StringField


class RastreavelForm(FlaskForm):
    user_name = StringField()
    user_descricao = StringField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_name.data = current_user.name
