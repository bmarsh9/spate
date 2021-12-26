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
            {"endpoint":"/api/v1/executions/<string:execution_uuid>","desc":"view executions of the workflow"},
            {"endpoint":"/api/v1/endpoints/<string:workflow_uuid>","desc":"execute workflow via API route"},
            {"endpoint":"/api/v1/endpoints/<string:step_uuid>/resume","desc":"resume execution of workflow step"},
            {"endpoint":"/intake/<string:form_name>","desc":"execute workflow via Form route"},
        ]
    })

@api.route('/executions/<string:execution_uuid>', methods=['GET'])
def get_result_status(execution_uuid):
    execution = current_app.db_session.query(current_app.Execution).filter(current_app.Execution.uuid == execution_uuid).first()
    if not execution:
        return jsonify({"message":"execution does not exist"}),404

    workflow = WorkflowManager(execution.workflow_id)
    if not workflow.verify_token_in_request(request):
        return jsonify({"message":"authentication failed"}),401

    complete = workflow.is_execution_complete(execution.id)
    if not complete:
        return jsonify({"message":"execution is not complete",
            "complete":False})
    logs = ""
    if execution.logs:
        logs = execution.logs.split("\n")
    debug = ""
    if execution.user_messages:
        debug = execution.user_messages.split("\n")
    template = {
        "id":execution.id,
        "uuid":execution.uuid,
        "return_value":workflow.return_value_for_execution(execution.id, execution.return_hash),
        "return_hash":execution.return_hash,
        "logs":logs,
        "debug":debug,
        "complete":True,
        "failed":execution.failed,
        "execution_time":workflow.execution_time_for_execution(execution.id),
        "date_requested":str(execution.date_added),
    }
    return jsonify(template)

@api.route('/endpoints/<string:step_uuid>/resume', methods=['GET','POST'])
def resume_workflow_execution(step_uuid):
    step = current_app.db_session.query(current_app.Step).filter(current_app.Step.uuid == step_uuid).first()
    if not step:
        return jsonify({"message":"step not found"}),404
    execution = current_app.db_session.query(current_app.Execution).filter(current_app.Execution.id == step.execution_id).first()
    if not execution:
        return jsonify({"message":"execution not found"}),404
    workflow = WorkflowManager(execution.workflow_id)
    if not workflow.verify_token_in_request(request):
        return jsonify({"message":"authentication failed"}),401
    response = request_to_json(request)
    try:
        results = workflow.resume(execution,step,response)
        code = 200
    except Exception as e:
        logging.error("An error occurred upon resuming execution:{}. Error:{}".format(execution.id,str(e)))
        results = str(e)
        code = 500
    return jsonify({"response":results}),code

@api.route('/endpoints/<string:workflow_uuid>', methods=['GET'])
def execute_api_workflow(workflow_uuid):
    workflow = current_app.db_session.query(current_app.Workflow).filter(current_app.Workflow.uuid == workflow_uuid).first()
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.enabled:
        return jsonify({"message":"workflow is disabled"}),400
    if not WorkflowManager(workflow.id).verify_token_in_request(request):
        return jsonify({"message":"authentication failed"}),401
    try:
        results = WorkflowManager(workflow.id).run(request=request_to_json(request))
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
    if not WorkflowManager(workflow_id).verify_token_in_request(request):
        return jsonify({"message":"authentication failed"}),401
    form = current_app.db_session.query(current_app.IntakeForm).filter(current_app.IntakeForm.name == name).first()
    if not form:
        return jsonify({"message":"form not found"}),404
    trigger = current_app.db_session.query(current_app.Operator).filter(current_app.Operator.form_id == form.id).filter(current_app.Operator.workflow_id == workflow_id).first()
    if not trigger:
        return jsonify({"message":"trigger not found"}),404
    # result returns the name of the submitted Result or 0 (failed)
    try:
        result = WorkflowManager(workflow.id).run(request=request_to_json(request),subtype="form")
        request_id = result.uuid
        code = 200
    except Exception as e:
        logging.error("An error occurred upon submission of the Form trigger:{}. Error:{}".format(workflow.name,str(e)))
        request_id = "0"
        code = 500
    redirect_url = "/workflows/{}/intake/{}/done?request_id={}".format(workflow.id,form.name,request_id)
    return jsonify({"message":"ok","url":redirect_url}),code

@api.route('/intake/<string:uuid>/status', methods=['GET'])
def get_intake_status(uuid):
    if str(uuid) == "0":
        return jsonify({"complete":False,"status":"failed",
            "message":"Hmmm... looks like an error occurred. We are looking into it."})
    execution = current_app.db_session.query(current_app.Execution).filter(current_app.Execution.uuid == uuid).first()
    if not execution:
        return jsonify({"complete":False,"status":"failed","message":"The requested resource was not found"}),404
    workflow = WorkflowManager(execution.workflow_id)
    complete = workflow.is_execution_complete(execution.id)
    if not complete:
        return jsonify({"id":execution.id,"uuid":execution.uuid,"complete":False,
            "message":"[{}] Please wait..."})
    return_value = workflow.return_value_for_execution(execution.id, execution.return_hash)
    return jsonify({"id":execution.id,"uuid":execution.uuid,"complete":True,
        "message":return_value})
