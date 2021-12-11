import uuid

def request_to_json(request):
    data = {
        "headers":dict(request.headers),
        "body":request.get_json(silent=True),
        "args":request.args.to_dict(),
    }
    for property in ["origin","method","mimetype","referrer","remote_addr","url"]:
        data[property] = getattr(request,property)
    return data

def parse_locker_creation(input):
    seen = []
    data = []
    for key,value in input.items():
        if "team" not in key:
            qid = int(key.split("_")[1])
            if qid not in seen:
                data.append({"id":qid,"key":value})
                seen.append(qid)
            else:
                list_id = [i for i,_ in enumerate(data) if _['id'] == qid][0]
                data[list_id]["value"] = value.lower()
    return data

def generate_uuid(length=None):
    id = uuid.uuid4().hex
    if length:
        id = id[:length]
    return id

def get_table_object(table=None):
    if table is None:
        return current_app.models
    return current_app.models.get(table.lower())

def msg_to_json(message="None",result=False,label="warning",**kwargs):
    '''
    .Description --> Return JSON message for the result
    '''
    message = {
        "message":str(message),
        "result":result,
        "type":str(label),
        "id":kwargs.get("id")
    }
    return message

def get_TableSchema(table,column=None,is_date=False,is_int=False,is_str=False,is_json=False,is_bool=False):
    '''
    :Description - Get a tables col names and types Usage - ("table",column="message",is_str=True)
    '''
    data = {}
    for col in table.__table__.columns:
        try: # field type JSON does not have a type attribute
            col_type=str(col.type)
        except:
            col_type="JSON"
        data[col.name] = str(col_type)
    if column is not None:
        splice = data.get(column,None)
        if splice:
            if is_int and "INTEGER" in splice:
                return True
            if is_str and "VARCHAR" in splice:
                return True
            if is_json and "JSON" in splice:
                return True
            if is_bool and "BOOLEAN" in splice:
                return True
            if is_date and "DATETIME" in splice:
                return True
            return False
        raise Exception("Column not found")
    return data

def generate_form_from_code(code):
    """
    generates HTML form based on comments in the Operator/Link code

    e.g. url = None ##input:type=text:placeholder=enter email:name=email:label=testing
    """
    input_dictionary = {
        "text":"<input type='text' class='form-control' {}>",
        "number":"<input type='number' class='form-control' {}>",
        "date":"<input type='date' class='form-control' data-mask='00/00/0000' data-mask-visible='true' autocomplete='off' {}>",
        "checkbox":"<input type='checkbox' class='form-check-input ml-2' {}>"
    }
    content = ""
    for line in code.split("\n"):
        if line:
            line = line.strip()
            if "##input" in line:
                available_params = line.split("##input")[-1:]
                if available_params:
                    param_dict = {}
                    for param in [x.split("=") for x in available_params[0].split(":") if "=" in x]:
                        param_dict[param[0]] = param[1]
                    type = param_dict.get("type")
                    input_type = input_dictionary.get(type)
                    if input_type:
                        param_dict.pop("type",None)
                        input_addons = ""
                        if param_dict:
                            for key,value in param_dict.items():
                                input_addons+="{}='{}' ".format(key,value)
                        input = input_type.format(input_addons)
                        content+="<div class='mb-3'><label class='form-label subheader'>{}</label>{}</div>".format(param_dict.get("label","Add Label"),input)
    return content

