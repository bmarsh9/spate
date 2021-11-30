from flask import render_template, redirect, url_for, abort, flash, request, \
    current_app, jsonify
from . import main
from app.models import *
from flask_login import login_required,current_user
from app.utils.decorators import roles_required
from app.utils.misc import parse_locker_creation,generate_uuid
from app.utils.docker_manager import DockerManager

@main.route('/', methods=['GET'])
@login_required
def home():
    return redirect(url_for("main.workflows"))

@main.route('/docs', methods=['GET'])
@login_required
def docs():
    return render_template("docs.html")

@main.route('/status', methods=['GET'])
@login_required
def status():
    data = {}
    docker_manager = DockerManager()
    container_list = ["spate-ui","spate-poller","spate-ingress","spate-cron","postgres_db"]
    for name in container_list:
        data[name] = {"status":"not running","running":False}
        container = docker_manager.get_container(name)
        if container:
            state = container.attrs["State"]
            data[name]["status"] = state["Status"]
            data[name]["running"] = state["Running"]
    return render_template("status.html",status=data)

@main.route('/admin/operators', methods=['GET'])
@roles_required("admin")
def operators():
    operators = Operator.query.all()
    return render_template('operators.html',operators=operators)

#--------------- Workflow ----------------------
@main.route('/workflows', methods=['GET'])
@login_required
def workflows():
    workflows = Workflow.query.all()
    return render_template("workflows.html",workflows=workflows)

@main.route('/workflows/<int:id>', methods=['GET'])
@login_required
def view_workflow(id):
    workflow = Workflow.query.get(id)
    if not workflow:
        flash("Workflow does not exist","warning")
        return redirect(url_for("main.home"))
    if not workflow.user_can_read(current_user.id):
        flash("You do not have access to this resource","warning")
        return redirect(url_for("main.home"))
    return render_template("home.html",workflow=workflow)

@main.route('/workflows/add', methods=['GET','POST'])
@login_required
def add_workflow():
    new_workflow = Workflow().add()
    flash("Added workflow")
    return redirect(url_for("main.view_workflow",id=new_workflow.id))

@main.route('/workflows/<int:id>/access', methods=['GET'])
@login_required
def workflow_access(id):
    workflow = Workflow.query.get(id)
    if not workflow:
        flash("Workflow does not exist","warning")
        return redirect(url_for("main.home"))
    _query = WorkflowUser.query.filter(WorkflowUser.workflow_id == id)
    read_users = workflow.get_read_user_access()
    write_users = workflow.get_write_user_access()
    users = User.query.filter(User.is_active == True).all()
    return render_template('workflow_access.html',users=users,workflow=workflow,
        read_users=read_users,write_users=write_users)

@main.route('/workflows/<int:workflow_id>/results', methods=['GET'])
@login_required
def workflow_results(workflow_id):
    workflow = Workflow.query.get(workflow_id)
    if not workflow:
        flash("Workflow does not exist","warning")
        return redirect(url_for("main.home"))
    if not workflow.user_can_read(current_user.id):
        flash("You do not have access to this resource","warning")
        return redirect(url_for("main.home"))
    results = workflow.results.order_by(Result.id.desc()).all()
    return render_template("workflow_results.html",workflow=workflow,results=results)

@main.route('/workflows/<int:workflow_id>/results/<int:result_id>', methods=['GET'])
@login_required
def view_results_of_workflow(workflow_id,result_id):
    workflow = Workflow.query.get(workflow_id)
    if not workflow:
        flash("Workflow does not exist","warning")
        return redirect(url_for("main.home"))
    if not workflow.user_can_read(current_user.id):
        flash("You do not have access to this resource","warning")
        return redirect(url_for("main.home"))
    result = workflow.results.filter(Result.id == result_id).first()
    if not result:
        flash("Resource does not exist")
        return redirect(url_for("main.workflows"))
    return render_template("view_results.html",workflow=workflow,result=result)

@main.route('/workflows/<int:workflow_id>/results/<int:result_id>/paths', methods=['GET'])
@login_required
def view_paths_of_workflow(workflow_id,result_id):
    workflow = Workflow.query.get(workflow_id)
    if not workflow:
        flash("Workflow does not exist","warning")
        return redirect(url_for("main.home"))
    if not workflow.user_can_read(current_user.id):
        flash("You do not have access to this resource","warning")
        return redirect(url_for("main.home"))
    result = workflow.results.filter(Result.id == result_id).first()
    if not result:
        flash("Resource does not exist")
        return redirect(url_for("main.workflows"))
    return render_template("view_paths.html",workflow=workflow,result=result)

#--------------- Locker ----------------------
@main.route('/lockers', methods=['GET'])
@login_required
def lockers():
    lockers = Locker.query.all()
    return render_template("lockers.html",lockers=lockers)

@main.route('/lockers/<int:id>', methods=['GET'])
@login_required
def view_locker(id):
    locker = Locker.query.get(id)
    workflows = locker.get_workflows_ex()
    return render_template("view_locker.html",locker=locker,workflows=workflows)

@main.route('/lockers/add', methods=['GET','POST'])
@login_required
def add_locker():
    name = "Locker_{}".format(generate_uuid(length=7))
    new_locker = Locker(name=name,label=name)
    db.session.add(new_locker)
    db.session.commit()
    flash("Added locker")
    return redirect(url_for("main.view_locker",id=new_locker.id))

@main.route('/lockers/<int:id>/attributes', methods=['POST'])
@login_required
def edit_locker_attributes(id):
    locker = Locker.query.get(id)
    attr_set = parse_locker_creation(request.form)
    config = {}
    for pair in attr_set:
        config[pair["key"]] = pair["value"]
    locker.config = config
    db.session.commit()
    flash("Edited locker attributes")
    return redirect(url_for("main.view_locker",id=id))

@main.route('/lockers/<int:id>/settings', methods=['POST'])
@login_required
def edit_locker_settings(id):
    locker = Locker.query.get(id)
    workflows = request.form.getlist('workflows[]')
    locker.set_workflows_by_name(workflows)
    locker.label = request.form.get("label")
    db.session.commit()
    flash("Edited locker settings")
    return redirect(url_for("main.view_locker",id=id))
