from flask import jsonify, request, current_app
from . import api
from app.models import *
from app.utils.misc import request_to_json
from flask_login import login_required,current_user
from app.utils.decorators import roles_required

@api.route('/health', methods=['GET'])
def get_health():
    return jsonify({"message":"ok"})

@api.route('/service/status', methods=['GET'])
def get_service_status():
    return jsonify({"message":"ok"})

@api.route('/operators/<int:id>/official', methods=['PUT'])
@roles_required("admin")
def update_operator_official(id):
    operator = Operator.query.get(id)
    if not operator:
        return jsonify({"message":"operator not found"}),404
    operator.official = not operator.official
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/operators/<int:id>/public', methods=['PUT'])
@roles_required("admin")
def update_operator_public(id):
    operator = Operator.query.get(id)
    if not operator:
        return jsonify({"message":"operator not found"}),404
    operator.public = not operator.public
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/workflows/<int:workflow_id>/results/<int:result_id>', methods=['GET'])
@login_required
def workflow_endpoint(workflow_id,result_id):
    workflow = Workflow.query.get(workflow_id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_read(current_user.id):
        return jsonify({"message":"access denied"}),403
    result = Result.query.get(result_id)
    if not result:
        return jsonify({"message":"result does not exist"}),404
    if result.status != "complete":
        return jsonify({"message":"result is not finished",
            "complete":False,"status":result.status})
    return jsonify(result.as_dict())

@api.route('/workflows/<int:id>', methods=['GET'])
@login_required
def get_workflow(id):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_read(current_user.id):
        return jsonify({"message":"access denied"}),403
    data = workflow.to_workflow()
    return jsonify(data)

@api.route('/workflows/<int:id>/actions/refresh', methods=['GET'])
@login_required
def refresh_workflow(id):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_write(current_user.id):
        return jsonify({"message":"access denied"}),403
    results = workflow.setup_workflow()
    return jsonify({"message":"ok"})

@api.route('/workflows/<int:id>/config', methods=['GET'])
@login_required
def get_workflow_config(id):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_read(current_user.id):
        return jsonify({"message":"access denied"}),403
    return jsonify({"config":workflow.to_html_settings()})

@api.route('/operators/<string:operator_name>/inputs', methods=['GET'])
@login_required
def get_inputs_for_operator_2(operator_name):
    operator = Operator.find_by_name(operator_name)
    if not operator:
        return jsonify({"message":"operator not found"}),404
    data = operator.modal_inputs()
    return jsonify(data)

@api.route('/operators/<string:operator_name>/outputs', methods=['GET'])
@login_required
def get_outputs_for_operator_2(operator_name):
    operator = Operator.find_by_name(operator_name)
    if not operator:
        return jsonify({"message":"operator not found"}),404
    data = operator.modal_outputs()
    return jsonify(data)

@api.route('/workflows/<int:id>/config', methods=['PUT'])
@login_required
def update_config_for_workflow(id):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_write(current_user.id):
        return jsonify({"message":"access denied"}),403
    data = request.get_json()
    workflow.label = data["label"]
    workflow.description = data["description"]
    workflow.imports = data["imports"]
    workflow.enabled = data["enabled"]
    workflow.log_level = data["log_level"]
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/workflows/<int:id>/operators', methods=['POST'])
@login_required
def add_operator_for_workflow(id):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_write(current_user.id):
        return jsonify({"message":"access denied"}),403
    data = request.get_json()
    operator_id = data["operator_id"]
    operator = Operator.query.get(operator_id)
    if not operator:
        return jsonify({"message":"operator not found"})
    '''only allowing one trigger per workflow right now'''
    if operator.type == "trigger":
        if workflow.get_trigger():
            return jsonify({"message":"one trigger per workflow"}),400
    add_output = operator.outputs.count()
    new_operator = Operator.add(workflow.id,operator.id,type=operator.type,top=data["top"],left=data["left"],add_output=add_output)
    return jsonify(new_operator.template())

@api.route('/workflows/<int:id>/operators/<string:operator_name>/position', methods=['PUT'])
@login_required
def update_operator_position(id, operator_name):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_write(current_user.id):
        return jsonify({"message":"access denied"}),403
    data = request.get_json()
    operator = Operator.find_by_name(operator_name)
    if not operator:
        return jsonify({"message":"operator not found"}),404
    operator.top = data["top"]
    operator.left = data["left"]
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/workflows/<int:id>/operators/<string:operator_name>', methods=['DELETE'])
@login_required
def delete_operator_for_workflow(id, operator_name):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_write(current_user.id):
        return jsonify({"message":"access denied"}),403
    operator = Operator.find_by_name(operator_name)
    if not operator:
        return jsonify({"message":"operator not found"}),404
    operator.remove()
    return jsonify({"message":"ok"})

@api.route('/workflows/<int:id>/operators/<string:operator_name>/meta', methods=['GET'])
@login_required
def get_operator_meta(id,operator_name):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_read(current_user.id):
        return jsonify({"message":"access denied"}),403
    operator = Operator.find_by_name(operator_name)
    if not operator:
        return jsonify({"message":"operator not found"}),404
    data = {
        "name":operator.name,
        "label":operator.label,
    }
    return jsonify(data)

@api.route('/workflows/<int:id>/operators/<string:operator_name>/exist', methods=['GET'])
@login_required
def does_operator_exist_for_workflow(id,operator_name):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_read(current_user.id):
        return jsonify({"message":"access denied"}),403
    return jsonify({"message":True})

@api.route('/workflows/<int:id>/operators/<string:operator_name>/code', methods=['GET'])
@login_required
def get_code_for_operator(id,operator_name):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_read(current_user.id):
        return jsonify({"message":"access denied"}),403
    operator = Operator.find_by_name(operator_name)
    if not operator:
        return jsonify({"message":"operator not found"}),404
    return jsonify({"code":operator.code})

@api.route('/workflows/<int:id>/operators/<string:operator_name>/code', methods=['PUT'])
@login_required
def update_code_for_operator(id,operator_name):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_write(current_user.id):
        return jsonify({"message":"access denied"}),403
    operator = Operator.find_by_name(operator_name)
    if not operator:
        return jsonify({"message":"operator not found"}),404
    data = request.get_json()
    operator.code = data["code"]
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/workflows/<int:id>/operators/<string:operator_name>/config', methods=['GET'])
@login_required
def get_config_for_operator(id,operator_name):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_read(current_user.id):
        return jsonify({"message":"access denied"}),403
    operator = Operator.find_by_name(operator_name)
    if not operator:
        return jsonify({"message":"operator not found"}),404
    return jsonify({"config":operator.form_html()})

@api.route('/workflows/<int:id>/operators/<string:operator_name>/config', methods=['PUT'])
@login_required
def update_config_for_operator(id,operator_name):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_write(current_user.id):
        return jsonify({"message":"access denied"}),403
    operator = Operator.find_by_name(operator_name)
    if not operator:
        return jsonify({"message":"operator not found"}),404
    data = request.get_json()
    operator.label = data["label"]
    operator.description = data["description"]
    operator.enabled = data["enabled"]
    operator.imports = data["imports"]
    operator.return_path = data.get("return_path")
    if data.get("synchronous"):
        if data["synchronous"] == "synchronous":
            operator.synchronous = True
        else:
            operator.synchronous = False
    if data.get("runevery"):
        operator.run_every = data.get("runevery")
    db.session.commit()
    return jsonify({"config":operator.form_html()})

@api.route('/workflows/<int:id>/links/<string:link_name>/code', methods=['GET'])
@login_required
def get_code_for_link(id,link_name):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_read(current_user.id):
        return jsonify({"message":"access denied"}),403
    link = OutputLink.find_by_name(link_name)
    if not link:
        return jsonify({"message":"link not found"}),404
    return jsonify({"code":link.code})

@api.route('/workflows/<int:id>/links/<string:link_name>/config', methods=['GET'])
@login_required
def get_config_for_link(id,link_name):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_read(current_user.id):
        return jsonify({"message":"access denied"}),403
    link = OutputLink.find_by_name(link_name)
    if not link:
        return jsonify({"message":"link not found"}),404
    return jsonify({"config":link.form_html()})

@api.route('/workflows/<int:id>/links/<string:link_name>/config', methods=['PUT'])
@login_required
def update_config_for_link(id,link_name):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_write(current_user.id):
        return jsonify({"message":"access denied"}),403
    link = OutputLink.find_by_name(link_name)
    if not link:
        return jsonify({"message":"link not found"}),404
    data = request.get_json()
    link.label = data["label"]
    link.description = data["description"]
    link.enabled = data["enabled"]
    link.imports = data["imports"]
    db.session.commit()
    return jsonify({"config":link.form_html()})

@api.route('/workflows/<int:id>/links/<string:link_name>/code', methods=['PUT'])
@login_required
def update_code_for_link(id,link_name):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_write(current_user.id):
        return jsonify({"message":"access denied"}),403
    link = OutputLink.find_by_name(link_name)
    if not link:
        return jsonify({"message":"link not found"}),404
    data = request.get_json()
    link.code = data["code"]
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/workflows/<int:id>/operators/<string:operator_name>/outputs', methods=['GET'])
@login_required
def get_outputs_for_operator(id,operator_name):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_read(current_user.id):
        return jsonify({"message":"access denied"}),403
    operator = Operator.find_by_name(operator_name)
    if not operator:
        return jsonify({"message":"operator not found"}),404
    data = {"operator_name":operator.name,"outputs":[]}
    #get all outputs for a operator
    for output in operator.outputs.all():
        row = {"output_name":output.name,"links":output.get_links_ex()}
        data["outputs"].append(row)
    return jsonify(data)

@api.route('/workflows/<int:id>/sidebar', methods=['GET'])
@login_required
def get_sidebar_for_workflow(id):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_read(current_user.id):
        return jsonify({"message":"access denied"}),403
    search_term = request.args.get("search",None)
    data = workflow.get_sidebar(search_term=search_term)
    return jsonify(data)

@api.route('/workflows/<int:id>/links', methods=['POST'])
@login_required
def add_link(id):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_write(current_user.id):
        return jsonify({"message":"access denied"}),403
    data = request.get_json()
    output = Output.find_by_name(data["from_connector"])
    if not output:
        return jsonify({"message":"output not found"}),404
    result = output.add_link(data["to_operator"],data["to_connector"])
    return jsonify(result)

@api.route('/workflows/<int:id>/links/<string:link_name>', methods=['DELETE'])
@login_required
def delete_link(id, link_name):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_write(current_user.id):
        return jsonify({"message":"access denied"}),403
    link = OutputLink.find_by_name(link_name)
    if not link:
        return jsonify({"message":"link not found"}),404
    db.session.delete(link)
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route('/workflows/<int:id>/inputs/<string:input_name>/config', methods=['GET'])
@login_required
def get_input_config(id,input_name):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_read(current_user.id):
        return jsonify({"message":"access denied"}),403
    input = Input.find_by_name(input_name)
    if not input:
        return jsonify({"message":"input not found"}),404
    return jsonify({"config":input.form_html()})

@api.route('/workflows/<int:id>/inputs/<string:input_name>/code', methods=['GET'])
@login_required
def get_input_code(id,input_name):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_read(current_user.id):
        return jsonify({"message":"access denied"}),403
    input = Input.find_by_name(input_name)
    if not input:
        return jsonify({"message":"input not found"}),404
    return jsonify({"code":"test code"})
