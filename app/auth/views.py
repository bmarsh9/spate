from datetime import datetime as dt
import logging
from secrets import token_urlsafe
from flask import (
    request,
    render_template,
    flash,
    redirect,
    Blueprint,
    url_for,
    current_app
)
from flask_babel import lazy_gettext as _l
from flask_login import current_user, logout_user, login_user, login_required
from . import auth

from app import db
from app.forms import LoginForm, RegisterForm, ResetPasswordReq, ResetPassword
from app.models import *
from app.email import send_email
import datetime

logger = logging.getLogger(__name__)

def create_user(form):
    email = form.email.data
    existing_user = User.query.filter(
        User.email == email
    ).first()
    if existing_user:
        flash(_l(f'({email}) already created!'), 'info')
        return redirect(url_for('auth.login'))
    else:
        new_user = User(
            email=email,
            email_confirmed_at=datetime.datetime.utcnow(),
        )
        new_user.set_password(form.password.data)
        flash(_l(f'{email} you are registered now'), 'success')
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.home'))
    logger.info('Form action')
    return True

@auth.route('/login', methods=['GET', 'POST'])
def login():
    next_page = request.args.get('next')
    if current_user.is_authenticated:
        return redirect(next_page or url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash(_l('Invalid email or password'), 'info')
            return redirect(next_page or url_for('auth.login'))
        Logs.add_log("{} logged in".format(user.email),log_type="info",namespace="events")
        login_user(user)
        return redirect(next_page or url_for('main.home'))
    return render_template('auth/login.html', form=form)

@auth.route('/logout')
def logout():
    logout_user()
    flash("You are logged out.", "success")
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if not current_app.config["ENABLE_SELF_REGISTRATION"]:
        #check token in args
        token = request.args.get("token")
        if not token:
            flash("Missing token","warning")
            return redirect(url_for("auth.login"))
        result = User().verify_invite_token(token)
        if not result:
            flash("Invalid or expired token","warning")
            return redirect(url_for("auth.login"))

    next_page = request.args.get('next')
    if current_user.is_authenticated:
        return redirect(next_page or url_for('main.home'))
    form = RegisterForm()
    if form.validate_on_submit():
        create_user(form)
        return redirect(next_page or url_for('auth.login'))
    return render_template('auth/register.html', form=form)

@auth.route("/reset_password", methods=['GET', 'POST'])
def reset_password():
    next_page = request.args.get('next')
    if current_user.is_authenticated:
        return redirect(next_page or url_for('main.home'))
    form = ResetPasswordReq()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.verify_expiration_token()
            db.session.commit()
            send_email(
                _l('Request change password'),
                sender=current_app.config['ADMINS'][0],
                recipients=[user.email],
                text_body=render_template(
                    'email/reset_password.txt',
                    token=token),
                html_body=render_template(
                    'email/reset_password.html',
                    token=token)
            )
            flash("Email sent, check your mail now!", "info")
            return redirect(url_for('auth.login'))
        flash("This email not registered", "info")
    return render_template('auth/reset_password_req.html', form=form)

@auth.route("/reset_password_token/<token>", methods=['GET', 'POST'])
def reset_password_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = ResetPassword()
    if form.validate_on_submit():
        user = User.query.filter_by(token=token).first()
        if user:
            user.set_password(form.password.data)
            db.session.commit()
            flash("Password changed!", "success")
            return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)
