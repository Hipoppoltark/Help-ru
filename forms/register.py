from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SubmitField, BooleanField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, EqualTo


class RegisterForm(FlaskForm):
    username = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    confirm_password = PasswordField(
        label=('Повторите пароль'),
        validators=[DataRequired(message='*Required'),
                    EqualTo('password', message='Both password fields must be equal!')])
    surname = StringField('Фамилия')
    name = StringField('Имя')
    age = IntegerField('Возраст')
    submit = SubmitField('Зарегистрироваться')