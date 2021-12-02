from flask import jsonify, request, current_app
from app.utils.decorators import token_required
from . import api
from app.utils.workflow_manager import WorkflowManager
from app.utils.misc import request_to_json

@api.route('/health', methods=['GET'])
def get_health():
    return jsonify({
        "message":"ok",
        "version":current_app.config["VERSION"],
        "routes":[
            {"endpoint":"/api/v1/workflows/<int:workflow_id>/results/<int:result_id>","desc":"view results of execution"},
            {"endpoint":"/workflows/<int:workflow_id>/actions/run","desc":"execute workflow via API route"},
        ]
    })

@api.route('/workflows/<int:workflow_id>/results/<int:result_id>', methods=['GET'])
@token_required
def workflow_endpoint(workflow_id,result_id):
    workflow = current_app.db_session.query(current_app.Workflow).filter(current_app.Workflow.id == workflow_id).first()
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    result = current_app.db_session.query(current_app.Result).filter(current_app.Result.id == result_id).first()
    if not result:
        return jsonify({"message":"result does not exist"}),404
    if result.status != "complete":
        return jsonify({"message":"result is not finished",
            "complete":False,"status":result.status})
    template = {
        "id":result.id,
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

@api.route('/workflows/<int:workflow_id>/actions/run', methods=['GET'])
def run_workflow(workflow_id):
    workflow = current_app.db_session.query(current_app.Workflow).filter(current_app.Workflow.id == workflow_id).first()
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.enabled:
        return jsonify({"message":"workflow is disabled"}),400
    try:
        results = WorkflowManager(workflow.id).run(workflow.name,
            request=request_to_json(request))
        code = 200
    except Exception as e:
        results = str(e)
        code = 500
    return jsonify({"response":results}),code

@api.route('/intake/<string:name>', methods=['POST'])
def submit_intake(name):
    form = current_app.db_session.query(current_app.IntakeForm).filter(current_app.IntakeForm.name == name).first()
    if not form:
        return jsonify({"message":"form not found"}),404
    operator = current_app.db_session.query(current_app.Operator).filter(current_app.Operator.form_id == form.id).first()
    if not operator:
        return jsonify({"message":"trigger  not found"}),404
    workflow = current_app.db_session.query(current_app.Workflow).filter(current_app.Workflow.id == operator.workflow_id).first()
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.enabled:
        return jsonify({"message":"workflow is disabled"}),400
    # result returns the ID of the submitted Result or 0 (failed)
    try:
        result = WorkflowManager(workflow.id).run(workflow.name,
            request=request_to_json(request),subtype="form")
        request_id = result.id
        code = 200
    except Exception as e:
        result = str(e)
        request_id = 0
        code = 500
    redirect_url = "/intake/{}/done?request_id={}".format(form.name,request_id)
    return jsonify({"message":"ok","url":redirect_url}),code

@api.route('/intake/<int:id>/status', methods=['GET'])
def get_intake_status(id):
    if id == 0:
        return jsonify({"id":id,"complete":False,"status":"error","message":"Hmmm... looks like an error occurred. We are looking into it."})
    request = current_app.db_session.query(current_app.Result).filter(current_app.Result.id == id).first()
    if not request:
        return jsonify({"message":"resource not found"}),404
    if request.status != "complete":
        return jsonify({"id":id,"complete":False,"status":request.status,"message":"[{}] Please wait...".format(request.status)})
    return jsonify({"id":id,"complete":True,"status":request.status,"message":request.return_value})
