from flask import jsonify, request, current_app
from app.utils.decorators import token_required
from . import api
from app.utils.workflow_manager import WorkflowManager
from app.utils.misc import request_to_json
import logging

@api.route('/health', methods=['GET'])
def get_health():
    return jsonify({
        "status":"ok",
        "message":current_app.config["APP_NAME"],
        "version":current_app.config["VERSION"],
        "routes":[
            {"endpoint":"/api/v1/results/<string:result_uuid>","desc":"view results of execution"},
            {"endpoint":"/api/v1/endpoints/<string:workflow_uuid>","desc":"execute workflow via API route"},
            {"endpoint":"/intake/<string:form_name>","desc":"execute workflow via Form route"},
        ]
    })

@api.route('/results/<string:result_name>', methods=['GET'])
@token_required
def get_result_status(result_name):
    result = current_app.db_session.query(current_app.Result).filter(current_app.Result.name == result_name).first()
    if not result:
        return jsonify({"message":"result does not exist"}),404
    if result.status != "complete":
        return jsonify({"message":"execution is not complete",
            "complete":False,"status":result.status})
    template = {
        "id":result.id,
        "name":result.name,
        "return_value":result.return_value,
        "return_hash":result.return_hash,
        "paths":result.paths,
        "logs":result.log.split("\n"),
        "debug":result.user_messages.split("\n"),
        "complete":True,
        "status":result.status,
        "execution_time":result.execution_time,
        "date_requested":str(result.date_added),
    }
    return jsonify(template)

@api.route('/endpoints/<string:workflow_uuid>', methods=['GET'])
def execute_api_workflow(workflow_uuid):
    workflow = current_app.db_session.query(current_app.Workflow).filter(current_app.Workflow.uuid == workflow_uuid).first()
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.enabled:
        return jsonify({"message":"workflow is disabled"}),400
    try:
        results = WorkflowManager(workflow.id).run(workflow.name,
            request=request_to_json(request))
        code = 200
    except Exception as e:
        logging.error("An error occurred upon submission of the API trigger:{}. Error:{}".format(workflow.name,str(e)))
        results = str(e)
        code = 500
    return jsonify({"response":results}),code

@api.route('/workflows/<int:workflow_id>/intake/<string:name>', methods=['POST'])
def submit_intake(workflow_id,name):
    workflow = current_app.db_session.query(current_app.Workflow).filter(current_app.Workflow.id == workflow_id).first()
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.enabled:
        return jsonify({"message":"workflow is disabled"}),400
    form = current_app.db_session.query(current_app.IntakeForm).filter(current_app.IntakeForm.name == name).first()
    if not form:
        return jsonify({"message":"form not found"}),404
    trigger = current_app.db_session.query(current_app.Operator).filter(current_app.Operator.form_id == form.id).filter(current_app.Operator.workflow_id == workflow_id).first()
    if not trigger:
        return jsonify({"message":"trigger not found"}),404
    # result returns the name of the submitted Result or 0 (failed)
    try:
        result = WorkflowManager(workflow.id).run(workflow.name,
            request=request_to_json(request),subtype="form")
        request_id = result.name
        code = 200
    except Exception as e:
        logging.error("An error occurred upon submission of the Form trigger:{}. Error:{}".format(workflow.name,str(e)))
        request_id = "0"
        code = 500
    redirect_url = "/workflows/{}/intake/{}/done?request_id={}".format(workflow.id,form.name,request_id)
    return jsonify({"message":"ok","url":redirect_url}),code

@api.route('/intake/<string:name>/status', methods=['GET'])
def get_intake_status(name):
    if str(name) == "0":
        return jsonify({"complete":False,"status":"failed",
            "message":"Hmmm... looks like an error occurred. We are looking into it."})
    result = current_app.db_session.query(current_app.Result).filter(current_app.Result.name == name).first()
    if not result:
        return jsonify({"complete":False,"status":"failed","message":"The requested resource was not found"}),404
    if result.status != "complete":
        return jsonify({"id":result.id,"name":result.name,"complete":False,
            "status":result.status,"message":"[{}] Please wait...".format(result.status)})
    return jsonify({"id":result.id,"name":result.name,"complete":True,
        "status":result.status,"message":result.return_value})
