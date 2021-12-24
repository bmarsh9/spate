from flask import current_app
import docker
import json
from datetime import datetime
import uuid

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

    def generate_uuid(self,length=None):
        id = uuid.uuid4().hex
        if length:
            id = id[:length]
        return id

    def add_in_progress_result(self):
        result = current_app.Result(name=self.generate_uuid(),workflow_id=self.workflow_id,
            status="in progress",date_added=datetime.utcnow())
        current_app.db_session.add(result)
        current_app.db_session.commit()
        return result

    def add_execution(self):
        tree = self.path_tree()
        # create execution object
        execution = Execution(uuid=generate_uuid(),return_hash=tree["return_path"],
            workflow_id=self.id)
        db.session.add(execution)
        db.session.flush()

        # create all paths and associate them to the steps
        for path in tree["paths"]:
            for path_hash,steps in path.items():
                new_path = Path(hash=path_hash,uuid=generate_uuid(),execution_id=execution.id)
                for previous_step, current_step in zip(steps, steps[1:]):
                    step_hash = self.create_hash_for_steps(steps[:steps.index(current_step)])
                    step = Step.find_or_create_step(current_step["name"],current_step["label"],step_hash,execution.id)
                    new_path.steps.append(step)
                db.session.add(new_path)
                db.session.commit()
        return execution

    def run(self,name,env={},request={},subtype="api"):
        trigger = self.get_trigger(subtype=subtype)
        if not trigger:
            raise ValueError("Trigger not found. Please add an API trigger.")
        container = self.find_container_by_workflow_name(name)
        if not container:
            raise ValueError("Container not found. Please refresh it.")

        execution = self.add_execution()

        command = "python3 /app/workflow/tmp/router.py --execution_id {} --request '{}'".format(execution.id,json.dumps(request))
        container.exec_run(command,environment=env,detach=not trigger.synchronous)

        if trigger.subtype == "form":
            return execution

        if trigger.synchronous:
            result = current_app.db_session.query(current_app.Result).filter(current_app.Result.id == result.id).first()
            if result.status != "complete":
                response = {
                    "id":execution.id,
                    "uuid":execution.uuid,
                    "status":result.status,
                    "date_requested":str(result.date_added),
                }
            else:
                response = {
                    "id":execution.id,
                    "uuid":execution.uuid,
                    "return_value":result.return_value, #TODO
                    "return_hash":result.return_hash, #TODO
                    "logs":result.log.split("\n"), #TODO
                    "debug":result.user_messages.split("\n"), #TODO
                    "complete":True, #TODO
                    "execution_time":result.execution_time, #TODO
                    "date_requested":str(execution.date_added),
                }
        else:
            response = {
                "id":execution.id,
                "uuid":execution.uuid,
                "callback_url":"/api/v1/executions/{}".format(execution.uuid),
                "status":"in progress",
            }
        return response
