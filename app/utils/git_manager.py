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
            current_app.logger.warning("{} does not contain 10 digit uuid".format(name))
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
        try:
            if not current_app.config["GIT_SYNC_REPO"]:
                raise ValueError("GIT_SYNC_REPO env var is not defined")

            g = github.Github()
            repo = g.get_repo(current_app.config["GIT_SYNC_REPO"])
            file_map = repo.get_contents(os.path.join(current_app.config["GIT_SYNC_DIRECTORY"],"manifest.json"))

            if not file_map:
                raise ValueError("Manifest file was not found:{}".format(os.path.join(current_app.config["GIT_SYNC_DIRECTORY"],"manifest.json")))
            manifest_file = json.loads(file_map.decoded_content.decode("utf-8"))

            for object in manifest_file:
                if object.get("file_name") and object.get("enabled",True):
                    file = repo.get_contents(os.path.join(current_app.config["GIT_SYNC_DIRECTORY"],object["file_name"]))
                    code = file.decoded_content.decode("utf-8")
                    if not self.validate_name(object.get("uuid")):
                        current_app.logger.warning("uuid is not valid for file:{}".format(object["file_name"]))
                    elif not self.validate_code(code):
                        current_app.logger.warning("code is not valid for file:{}".format(object["file_name"]))
                    else:
                        name = "operator_{}".format(object["uuid"])
                        operator = Operator.find_by_name(name)
                        if not operator:
                            current_app.logger.info("Adding new operator:{}".format(name))
                            operator = Operator(name=name,label=object.get("label","default"),type=object.get("type","action"),
                              code=code,top=1000,left=1000,workflow_id=object.get("workflow_id",1),
                              description=object.get("description","default"),official=object.get("official",True),
                              git_url=file.download_url,hash=file.sha,
                              git_sync_date=arrow.utcnow().datetime,git_stored=True)
                            db.session.add(operator)
                            db.session.commit()
                            # add input/output
                            operator.add_output()
                            if object.get("type","action") != "trigger":
                                operator.add_input()
                            Logs.add_log("Added an new operator from Github:{}".format(object["file_name"]),namespace="events")
                        elif not operator.git_stored:
                            current_app.logger.info("Duplicate name for an operator not synced with Github. Skipping.".format(name))
                        elif operator.hash != file.sha:
                            current_app.logger.info("File has been updated. Updating the code:{}".format(object["file_name"]))
                            operator.code = code
                            operator.hash = file.sha
                            operator.git_sync_date = arrow.utcnow().datetime
        except github.RateLimitExceededException as e:
            current_app.logger.error(e)
            return False
        return True
