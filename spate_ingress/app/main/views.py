from flask import render_template, redirect, url_for, abort, flash, request, \
    current_app
from . import main
from app.utils.workflow_manager import WorkflowManager

@main.route('/', methods=['GET'])
def home():
    return render_template("home.html")

@main.route('/intake/<string:name>', methods=['GET'])
def view_intake(name):
    form = current_app.db_session.query(current_app.IntakeForm).filter(current_app.IntakeForm.name == name).first()
    if not form or not form.enabled:
        flash("Form not found or it is disabled","danger")
        return redirect(url_for("main.home"))
    return render_template("show_form.html",form=form)

@main.route('/intake/<string:name>/done', methods=['GET'])
def intake_complete(name):
    form = current_app.db_session.query(current_app.IntakeForm).filter(current_app.IntakeForm.name == name).first()
    if not form or not form.enabled:
        flash("Form not found or it is disabled","danger")
        return redirect(url_for("main.home"))
    request_id = request.args.get("request_id",False)
    if request_id == False:
        flash("Request ID was not found","danger")
        return redirect(url_for("main.home"))
    return render_template("complete_form.html",request_id=request_id,
        form=form)
