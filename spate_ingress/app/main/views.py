from flask import render_template, redirect, url_for, abort, flash, request, \
    current_app
from . import main
from app.utils.workflow_manager import WorkflowManager

@main.route('/', methods=['GET'])
def home():
    return render_template("home.html")

@main.route('/workflows/<int:workflow_id>/intake/<string:name>', methods=['GET'])
def view_intake(workflow_id,name):
    workflow = current_app.db_session.query(current_app.Workflow).filter(current_app.Workflow.id == workflow_id).first()
    if not workflow:
        flash("Workflow not found!","danger")
        return redirect(url_for("main.home"))
    if not workflow.enabled:
        flash("Workflow is not enabled!","danger")
        return redirect(url_for("main.home"))
    trigger = WorkflowManager(workflow=workflow).get_trigger()
    if not trigger:
        flash("Missing trigger!","danger")
        return redirect(url_for("main.home"))
    if trigger.subtype != "form":
        flash("Trigger is not type form!","danger")
        return redirect(url_for("main.home"))
    if not WorkflowManager(workflow=workflow).verify_token_in_request(request):
        flash("Authentication failed","danger")
        return redirect(url_for("main.home"))
    form = current_app.db_session.query(current_app.IntakeForm).filter(current_app.IntakeForm.name == name).first()
    if not form or not form.enabled:
        flash("Form not found or it is disabled","danger")
        return redirect(url_for("main.home"))
    return render_template("show_form.html",form=form,workflow=workflow,token=request.args.get("token"))

@main.route('/workflows/<int:workflow_id>/intake/<string:name>/done', methods=['GET'])
def intake_complete(workflow_id,name):
    form = current_app.db_session.query(current_app.IntakeForm).filter(current_app.IntakeForm.name == name).first()
    if not form or not form.enabled:
        flash("Form not found or it is disabled","danger")
        return redirect(url_for("main.home"))
    request_id = request.args.get("request_id",False)
    if request_id == False:
        flash("Request ID was not found","danger")
        return redirect(url_for("main.home"))
    return render_template("complete_form.html",request_id=request_id,
        workflow_id=workflow_id,form=form,token=request.args.get("token"))

@main.route('/resume/<string:step_uuid>/done', methods=['GET'])
def resume_complete(step_uuid):
    '''show this form when the user submits their response to
    a paused workflow execution
    '''
    return render_template("resume_complete.html",step_uuid=step_uuid)

@main.route('/resume/<string:step_uuid>', methods=['GET'])
def view_intake_for_paused_path(step_uuid):
    step = current_app.db_session.query(current_app.Step).filter(current_app.Step.uuid == step_uuid).first()
    if not step:
        flash("Intake not found!","danger")
        return redirect(url_for("main.home"))
    if step.status != "paused":
        flash("Step is not paused!","danger")
        return redirect(url_for("main.home"))
    operator = current_app.db_session.query(current_app.Operator).filter(current_app.Operator.name == step.name).first()
    if not operator:
        flash("Operator does not exist anymore!","danger")
        return redirect(url_for("main.home"))
    form = current_app.db_session.query(current_app.IntakeForm).filter(current_app.IntakeForm.id == operator.form_id).first()
    if not form or not form.enabled:
        flash("Form not found or it is disabled","danger")
        return redirect(url_for("main.home"))
    return render_template("show_form_for_paused_path.html",form=form,step=step)
