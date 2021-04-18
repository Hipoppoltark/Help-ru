from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField
from wtforms import BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired


class RecordForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    description = TextAreaField("Описание")
    cost = SelectField('Стоимость вопроса', choices=[30, 60, 90, 120], validators=[DataRequired()])
    submit = SubmitField('Попросить помощь')