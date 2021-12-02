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
        results = WorkflowManager(workflow_id).run(workflow.name,request=request_to_json(request))
        code = 200
    except Exception as e:
        results = str(e)
        code = 400
    return jsonify({"response":results}),code
