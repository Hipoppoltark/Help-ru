from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SubmitField, BooleanField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, EqualTo


class ProfileForm(FlaskForm):
    username = EmailField('Email', validators=[DataRequired()])
    surname = StringField('Фамилия')
    name = StringField('Имя')
    age = IntegerField('Возраст')
    submit = SubmitField('Сохранить')