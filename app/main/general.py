from flask import render_template, redirect, url_for, abort, flash, request, \
    current_app, jsonify
from . import main
from app.models import *
from flask_login import login_required,current_user
from app.utils.decorators import roles_required
from app.models import Role,User

@main.route('/admin/users', methods=['GET'])
@roles_required("admin")
def users():
    users = User.query.all()
    return render_template('users.html',users=users)

@main.route('/admin/users/<int:id>', methods=['GET','POST'])
@roles_required("admin")
def view_user(id):
    user = User.query.get(id)
    if not user:
        flash("User does not exist!")
        return redirect(url_for("main.users"))
    if request.method == "POST":
        roles =  request.form.getlist('roles[]')
        user.set_roles_by_name(roles)
        user.first_name = request.form["first"]
        user.last_name = request.form["last"]
        user.username = request.form["username"]
        active = request.form["is_active"]
        if active == "yes":
            user.is_active = True
        else:
            user.is_active = False
        db.session.commit()
        flash("Updated user")
    roles = user.get_roles_for_form()
    return render_template('view_user.html',user=user,roles=roles)

@main.route('/admin/users/add', methods=['GET','POST'])
@roles_required("admin")
def add_user():
    token = None
    if request.method == "POST":
        email = request.form["email"]
        token = User().generate_invite_token(email)
        token = "{}{}?token={}".format(request.host_url,"register",token)
        flash("Provide the following link to the user.")
    return render_template('add_user.html',token=token)

@main.route('/admin/operators', methods=['GET'])
@roles_required("admin")
def operators():
    operators = Operator.query.all()
    return render_template('operators.html',operators=operators)
