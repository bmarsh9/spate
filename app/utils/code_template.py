import os
from flask import current_app

'''
Note: end-user can NOT edit the first three or the last three lines.
Any comments or code placed in those lines can't be changed by end user
'''

def default_op_code(name="code"):
    return """def {}(input, **kwargs):
    '''Place your custom code below.
    Must be indented under this function.'''


    '''Default return is True. If you want to return something else, do so above.
    If the return is False, the workflow will NOT proceed.'''
    return input
    """.format(name)

def default_input_code(name="code"):
    return """def {}(input, **kwargs):
    '''Place your custom code below.
    Must be indented under this function.'''


    '''Default return is True. If you want to return something else, do so above.
    If the return is False, the workflow will NOT proceed.'''
    return input
    """.format(name)

def default_link_code(name="code"):
    return """def {}(input, **kwargs):
    '''Place your custom code below.
    Must be indented under this function.'''


    '''Default return is True. If you want to return something else, do so above.
    If the return is False, the event will NOT be sent to the next Operator'''
    return input
    """.format(name)

def default_router_code(workflow_dir):
    path = os.path.join(current_app.config["BASE_DIR"],"app/utils/code_library/router_code.txt")
    if os.path.exists(path):
        with open(path) as f:
            contents = f.read()
            return contents.replace(int(current_app.config("BLOCK_TIMEOUT",30)),"BLOCK_TIMEOUT_PARAMETER")
    return ""

def default_store_code():
    path = os.path.join(current_app.config["BASE_DIR"],"app/utils/code_library/store_code.txt")
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return ""

def default_locker_code():
    path = os.path.join(current_app.config["BASE_DIR"],"app/utils/code_library/locker_code.txt")
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return ""
