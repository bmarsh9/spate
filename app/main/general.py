from flask import render_template, redirect, url_for, abort, flash, request, \
    current_app, jsonify
from . import main
from app.models import *
from flask_login import login_required,current_user
from app.utils.decorators import roles_required
from app.models import Role,User

@main.route('/admin/users', methods=['GET'])
@login_required
def users():
    users = User.query.all()
    return render_template('users.html',users=users)

@main.route('/admin/users/<int:id>', methods=['GET','POST'])
@login_required
def view_user(id):
    user = User.query.get(id)
    if not user:
        flash("User does not exist!")
        return redirect(url_for("main.users"))
    if not current_user.has_role("admin") and not current_user.id == id:
        flash("You do not have access to this resource","warning")
        return redirect(url_for("main.home"))
    if request.method == "POST":
        if current_user.has_role("admin"):
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

@main.route('/workflows/<int:id>/read-access', methods=['POST'])
@login_required
def edit_workflow_read_access(id):
    workflow = Workflow.query.get(id)
    if not workflow:
        flash("Workflow does not exist","warning")
        return redirect(url_for("main.home"))
    if not workflow.user_can_write(current_user.id) and not current_user.has_role("admin"):
        flash("You do not have access to this resource","warning")
        return redirect(url_for("main.home"))
    current_access = WorkflowUser.query.filter(WorkflowUser.workflow_id == workflow.id).filter(WorkflowUser.permission == 1).delete()
    read_users = request.form.getlist('read_users[]')
    for user_id in read_users:
        workflow.set_user(user_id,permission_level=1)
    db.session.commit()
    flash("Updated access to the workflow")
    return redirect(url_for("main.workflow_access",id=id))

@main.route('/workflows/<int:id>/write-access', methods=['POST'])
@login_required
def edit_workflow_write_access(id):
    workflow = Workflow.query.get(id)
    if not workflow:
        flash("Workflow does not exist","warning")
        return redirect(url_for("main.home"))
    if not workflow.user_can_write(current_user.id) and not current_user.has_role("admin"):
        flash("You do not have access to this resource","warning")
        return redirect(url_for("main.home"))
    current_access = WorkflowUser.query.filter(WorkflowUser.workflow_id == workflow.id).filter(WorkflowUser.permission == 2).delete()
    write_users = request.form.getlist('write_users[]')
    WorkflowUser.query.filter(WorkflowUser.workflow_id == workflow.id)
    for user_id in write_users:
        workflow.set_user(user_id,permission_level=2)
    db.session.commit()
    flash("Updated access to the workflow")
    return redirect(url_for("main.workflow_access",id=id))