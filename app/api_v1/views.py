from flask import jsonify, request, current_app
from . import api
from app.models import *
from app.utils.misc import request_to_json
from flask_login import login_required,current_user
from app.utils.decorators import roles_required
from app.utils.misc import generate_uuid
import arrow

@api.route('/health', methods=['GET'])
def get_health():
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

#----------------------------------------WORKFLOW-----------------------------------------
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

@api.route('/workflows/<int:id>/meta', methods=['GET'])
@login_required
def get_workflow_meta(id):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    return jsonify(workflow.as_meta())

@api.route('/workflows/<int:id>/actions/refresh', methods=['GET'])
@login_required
def refresh_workflow(id):
    workflow = Workflow.query.get(id)
    if not workflow:
        return jsonify({"message":"workflow not found"}),404
    if not workflow.user_can_write(current_user.id):
        return jsonify({"message":"access denied"}),403
    results = workflow.setup_workflow()
    workflow.refresh_required = False
    db.session.commit()
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
    workflow.refresh_required = True
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
    workflow.refresh_required = True
    db.session.commit()
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
    workflow.refresh_required = True
    db.session.commit()
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
    workflow.refresh_required = True
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

    # add variables to locker
    locker = workflow.get_default_locker()
    custom_vars = data["custom_variables"]
    if custom_vars:
        for key,value in custom_vars.items():
            locker.add_key(key,value)
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
    if data.get("form"):
        operator.form_id = data.get("form")
    workflow.refresh_required = True
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
    workflow.refresh_required = True
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
    workflow.refresh_required = True
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
    workflow.refresh_required = True
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
    workflow.refresh_required = True
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

#----------------------------------------FORM-----------------------------------------
@api.route("/forms", methods=["POST"])
@login_required
def add_form():
    data = request.get_json()
    form = IntakeForm(name=generate_uuid(length=10),label=data["label"],
        description=data["description"],data=data["form"],user_id=current_user.id)
    db.session.add(form)
    db.session.commit()
    return jsonify({"message":"ok"})

@api.route("/forms/<string:name>", methods=["PUT"])
@login_required
def edit_form(name):
    data = request.get_json()
    form = IntakeForm.query.filter(IntakeForm.name == name).first()
    if not form:
        return jsonify({"message":"form not found"}),404
    if not current_user.has_role("admin") and not current_user.id == form.user_id:
        return jsonify({"message":"access denied"}),403
    form.label = data["label"]
    form.description = data["description"]
    form.data = data["form"]
    form.enabled = data["enabled"]
    db.session.commit()
    return jsonify({"message":"ok"})

#----------------------------------------GRAPH-----------------------------------------
@api.route("/graphs/workflow-results", methods=["GET"])
@login_required
def graph_get_workflow_results():
    span_of_days = [(0,7),(7,14),(14,21),(21,28),(28,35)]
    now = arrow.utcnow()
    categories = []
    data = {"not started":[],"in progress":[],"complete":[],"failed":[]}
    for span in span_of_days:
        start,end = span
        categories.append("{}-{} days ago".format(start,end))
        for status in ["not started","in progress","complete","failed"]:
            count = Result.query.filter(Result.date_added < now.shift(days=-start).datetime).filter(Result.date_added > now.shift(days=-end).datetime).filter(Result.status == status).count()
            data[status].append(count)
    series = []
    for key,value in data.items():
        series.append({"name":key.upper(),"data":value})
    return jsonify({"categories":categories,"series":series})

@api.route("/graphs/workflow-triggers", methods=["GET"])
@login_required
def graph_get_workflow_triggers():
    series = []
    labels = ["API","CRON","FORM"]
    for label in labels:
        series.append(Operator.query.filter(Operator.official == False).filter(Operator.subtype == label.lower()).count())
    return jsonify({"labels":labels,"series":series})

@api.route("/graphs/events", methods=["GET"])
@login_required
def graph_get_events():
    data = {"data":[]}
    now = arrow.utcnow()
    for log in Logs.query.filter(Logs.date_added > now.shift(days=-14).datetime).all():
        data["data"].append([log.id,log.log_type,log.message,log.date_added])
    return jsonify(data)
