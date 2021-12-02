from flask import render_template, redirect, url_for, abort, flash, request, \
    current_app
from . import main
from app.utils.workflow_manager import WorkflowManager

@main.route('/intake/<string:name>', methods=['GET'])
def view_intake(name):
    form = current_app.db_session.query(current_app.IntakeForm).filter(current_app.IntakeForm.name == name).first()
    if not form or not form.enabled and not current_user.is_authenticated:
        abort(404)
    return render_template("show_form.html",form=form)

@main.route('/intake/<string:name>/done', methods=['GET'])
def intake_complete(name):
    form = current_app.db_session.query(current_app.IntakeForm).filter(current_app.IntakeForm.name == name).first()
    if not form or not form.enabled and not current_user.is_authenticated:
        abort(404)
    request_id = request.args.get("request_id",False)
    if request_id == False:
        abort(404)
    return render_template("complete_form.html",request_id=request_id)
