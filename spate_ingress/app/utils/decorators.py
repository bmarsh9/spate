from flask import current_app,request,jsonify
from functools import wraps

def token_required(view_function):
    @wraps(view_function)    # Tells debuggers that is is a function wrapper
    def decorator(*args, **kwargs):
        token = request.args.get("token")
        if not token:
            token = request.headers.get("token")
        if not token:
            return jsonify({"message":"token not found"}),401
        if token != current_app.config["SHARED_TOKEN"]:
            return jsonify({"message":"invalid token"}),401
        return view_function(*args, **kwargs)
    return decorator
