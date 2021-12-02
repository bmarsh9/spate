from flask import current_app
import docker
import json
from datetime import datetime

class WorkflowManager():
    def __init__(self, workflow_id):
        self.workflow_id = workflow_id

    def get_trigger(self,subtype):
        return current_app.db_session.query(current_app.Operator).filter(current_app.Operator.official == False).filter(current_app.Operator.subtype == subtype).filter(current_app.Operator.workflow_id == self.workflow_id).first()

    def find_container_by_workflow_name(self,name,by_id=False):
        '''search for workflow_name key set on the
        container labels
        '''
        for container in current_app.docker_client.containers.list():
            if container.labels.get("workflow_name","") == name:
                if by_id:
                    return container.short_id
                return container
        return None

    def add_in_progress_result(self):
        result = current_app.Result(workflow_id=self.workflow_id,status="in progress",date_added=datetime.utcnow())
        current_app.db_session.add(result)
        current_app.db_session.commit()
        return result

    def run(self,name,env={},request={},subtype="api"):
        trigger = self.get_trigger(subtype=subtype)
        if not trigger:
            raise ValueError("Trigger not found. Please add an API trigger.")
        container = self.find_container_by_workflow_name(name)
        if not container:
            raise ValueError("Container not found. Please refresh it.")

        result = self.add_in_progress_result()

        command = "python3 /app/workflow/tmp/router.py {} '{}'".format(result.id,json.dumps(request))
        container.exec_run(command,environment=env,detach=not trigger.synchronous)

        if trigger.subtype == "form":
            return result

        if trigger.synchronous:
            result = current_app.db_session.query(current_app.Result).filter(current_app.Result.id == result.id).first()
            if result.status != "complete":
                response = {
                    "id":result.id,
                    "status":result.status,
                    "date_requested":str(result.date_added),
                }
            else:
                response = {
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
        else:
            response = {
                "callback_url":"/api/v1/workflows/{}/results/{}".format(self.workflow_id,result.id),
                "status":"in progress",
            }
        return response
