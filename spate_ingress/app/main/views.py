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
    form = current_app.db_session.query(current_app.IntakeForm).filter(current_app.IntakeForm.name == name).first()
    if not form or not form.enabled:
        flash("Form not found or it is disabled","danger")
        return redirect(url_for("main.home"))
    return render_template("show_form.html",form=form,workflow=workflow)

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
        workflow_id=workflow_id,form=form)
