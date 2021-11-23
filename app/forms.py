from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField,\
  PasswordField, TextAreaField,FileField,SelectField,SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class LoginForm(FlaskForm):
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    submit = SubmitField(_l('Sign In'))

class RegisterForm(FlaskForm):
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    password2 = PasswordField(
            _l('Repeat Password'),
            validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField(_l('Sign In'))

class ResetPasswordReq(FlaskForm):
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    submit = SubmitField(_l('Sign In'))

class ResetPassword(FlaskForm):
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    password2 = PasswordField(
            _l('Repeat Password'),
            validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField(_l('Sign In'))
