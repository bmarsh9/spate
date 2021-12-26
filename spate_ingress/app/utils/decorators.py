from flask import current_app,request,jsonify
from functools import wraps

def token_required(view_function):
    @wraps(view_function)    # Tells debuggers that is is a function wrapper
    def decorator(*args, **kwargs):
        if current_app.config["ENFORCE_TOKEN_FOR_RESULTS"]:
            token = request.args.get("token")
            if not token:
                token = request.headers.get("token")
            if not token:
                return jsonify({"message":"token not found"}),401
            if token != current_app.config["SHARED_TOKEN"]:
                return jsonify({"message":"invalid token"}),401
        return view_function(*args, **kwargs)
    return decorator

def token_required(*role_names):
    def wrapper(view_function):
        @wraps(view_function)
        def decorator(*args, **kwargs):
            workflow = current_app.db_session.query(current_app.Workflow).filter(current_app.Workflow.uuid == workflow_uuid).first()
            if workflow.auth_required:
                token = request.headers.get("token")
                if not token:
                    return jsonify({"message":"authentication failed - missing token"}),401
                token_ok = validate_token_in_header(enc_token)
                if not token_ok:
                    return jsonify({"message":"authentication failed - bad token"}),401
            # It's OK to call the view
            return view_function(*args, **kwargs)
        return decorator
    return wrapper
