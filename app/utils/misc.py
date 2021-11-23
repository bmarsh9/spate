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
