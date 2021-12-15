from flask import current_app
from app.models import *
import github
import base64
import arrow
import json
import os

class GitManager():
    def __init__(self):
        pass

    def decode(self,base64_string):
        return base64.b64decode(base64_string).decode('utf-8')

    def validate_name(self,name):
        '''
        check the name of the file
        '''
        if not name:
            return False
        if not len(name) == 10:
            return False
        return True

    def validate_code(self,code):
        '''
        check the first and last line of the file
        first = def code(input, **kwargs):
        last = return input
        '''
        lines = code.strip().split("\n")
        if lines[0].strip() != "def code(input, **kwargs):":
            return False
        if lines[-1].strip() != "return input":
            return False
        return True

    def sync(self):
        namespace = "github_sync"
        Logs.add_log("Starting a sync for Github. GIT_SYNC_REPO:{}. GIT_SYNC_DIRECTORY:{}".format(current_app.config["GIT_SYNC_REPO"],
            current_app.config["GIT_SYNC_DIRECTORY"]),namespace=namespace)
        try:
            if not current_app.config["GIT_SYNC_REPO"]:
                Logs.add_log("GIT_SYNC_REPO env var is not defined",log_type="error",namespace=namespace)
                return False

            g = github.Github()
            repo = g.get_repo(current_app.config["GIT_SYNC_REPO"])
            manifest_filepath = os.path.join(current_app.config["GIT_SYNC_DIRECTORY"],"manifest.json")
            file_map = repo.get_contents(manifest_filepath)

            if not file_map:
                Logs.add_log("Manifest file was not found:{}".format(manifest_filepath),log_type="error",namespace=namespace)
                return False
            manifest_file = json.loads(file_map.decoded_content.decode("utf-8"))

            for object in manifest_file:
                if object.get("file_name") and object.get("enabled",True):
                    file = repo.get_contents(os.path.join(current_app.config["GIT_SYNC_DIRECTORY"],object["file_name"]))
                    code = file.decoded_content.decode("utf-8")
                    if not self.validate_name(object.get("uuid")):
                        Logs.add_log("uuid is not valid for file:{}".format(object["file_name"]),log_type="warning",namespace=namespace)
                    elif not self.validate_code(code):
                        Logs.add_log("code is not valid for file:{}".format(object["file_name"]),log_type="warning",namespace=namespace)
                    else:
                        name = "operator_{}".format(object["uuid"])
                        operator = Operator.find_by_name(name)
                        if not operator:
                            Logs.add_log("Adding new operator:{}".format(name),namespace=namespace)
                            operator = Operator(name=name,label=object.get("label","default"),type=object.get("type","action"),
                              code=code,top=1000,left=1000,workflow_id=object.get("workflow_id",1),documentation=object.get("documentation",True),
                              description=object.get("description","default"),official=object.get("official",True),
                              git_url=file.download_url,hash=file.sha,imports=object.get("imports",""),
                              git_sync_date=arrow.utcnow().datetime,git_stored=True)
                            db.session.add(operator)
                            db.session.commit()
                            # add input/output
                            operator.add_output()
                            if object.get("type","action") != "trigger":
                                operator.add_input()
                        elif not operator.git_stored:
                            Logs.add_log("Duplicate name for an operator not synced with Github. Skipping".format(name),log_type="warning",namespace=namespace)
                        elif operator.hash != file.sha:
                            Logs.add_log("File has been updated. Updating the code:{}".format(object["file_name"]),namespace=namespace)
                            operator.code = code
                            operator.hash = file.sha
                            operator.git_sync_date = arrow.utcnow().datetime
                            operator.label = object.get("label")
                            operator.description = object.get("description")
                            operator.imports = object.get("imports")
                            operator.documentation = object.get("documentation")
                            db.session.commit()
        except github.RateLimitExceededException as e:
            Logs.add_log("Github rate limit was reached",log_type="error",namespace=namespace)
            return False
        return True
