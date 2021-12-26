from flask import current_app
import docker
import json
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
from datetime import datetime
import uuid
import hashlib

class WorkflowManager():
    def __init__(self, workflow_id):
        self.workflow_id = workflow_id

    def verify_auth_token(token):
        workflow = current_app.db_session.query(current_app.Workflow).filter(current_app.Workflow.id == self.workflow_id).first()
        s = Serializer(workflow.secret_key)
        try:
            data = s.loads(token)
        except SignatureExpired:
            return False # valid token, but expired
        except BadSignature:
            return False # invalid token
        return True

    def generate_auth_token(self, expiration = 6000):
        workflow = current_app.db_session.query(current_app.Workflow).filter(current_app.Workflow.id == self.workflow_id).first()
        s = Serializer(workflow.secret_key, expires_in = expiration)
        return s.dumps({ 'workflow_id': self.workflow_id })

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

    def create_hash_for_steps(self,values):
        sha1 = hashlib.sha1()
        for value in values:
            val = str(value["name"]).encode('utf-8')
            sha1.update(val)
        return sha1.hexdigest()

    def find_or_create_step(self,name,label,hash,execution_id):
        step = current_app.db_session.query(current_app.Step).filter(current_app.Step.hash == hash).filter(current_app.Step.execution_id == execution_id).first()
        if step:
            return step
        new_step = current_app.Step(uuid=self.generate_uuid(),name=name,label=label,hash=hash,
            execution_id=execution_id,status="not started",date_added=datetime.utcnow())
        current_app.db_session.add(new_step)
        current_app.db_session.commit()
        return new_step

    def add_execution(self):
        workflow = current_app.db_session.query(current_app.Workflow).filter(current_app.Workflow.id == self.workflow_id).first()
        tree = workflow.map
        # create execution object
        execution = current_app.Execution(uuid=self.generate_uuid(),return_hash=tree["return_path"],
            workflow_id=self.workflow_id,date_added=datetime.utcnow())
        current_app.db_session.add(execution)
        current_app.db_session.flush()

        # create all paths and associate them to the steps
        for path in tree["paths"]:
            for path_hash,steps in path.items():
                new_path = current_app.Path(hash=path_hash,uuid=self.generate_uuid(),execution_id=execution.id,date_added=datetime.utcnow())
                current_app.db_session.add(new_path)
                current_app.db_session.flush()
                for previous_step, current_step in zip(steps, steps[1:]):
                    step_hash = self.create_hash_for_steps(steps[:steps.index(current_step)])
                    step = self.find_or_create_step(current_step["name"],current_step["label"],step_hash,execution.id)
                    ps = current_app.PathSteps(step_id=step.id,path_id=new_path.id)
                    current_app.db_session.add(ps)
                current_app.db_session.commit()
        return execution

    def get_steps_for_path(self,path_id):
        steps = []
        for path_step in current_app.db_session.query(current_app.PathSteps).filter(current_app.PathSteps.path_id == path_id).order_by(current_app.PathSteps.id.asc()).all():
            step = current_app.db_session.query(current_app.Step).filter(current_app.Step.id == path_step.step_id).first()
            if step:
                steps.append(step)
        return steps

    def return_value_for_execution(self, execution_id, execution_hash):
        path = current_app.db_session.query(current_app.Path).filter(current_app.Path.hash == execution_hash).filter(current_app.Path.execution_id == execution_id).first()
        if not path:
            return {}
        steps = self.get_steps_for_path(path.id)
        if steps:
            return steps[-1].result
        return {}

    def execution_time_for_execution(self, execution_id):
        time = 0
        for step in current_app.db_session.query(current_app.Step).filter(current_app.Step.execution_id == execution_id).all():
            time+= step.execution_time
        return time

    def is_path_complete(self,path_id):
        steps = self.get_steps_for_path(path_id)
        if not steps:
            return False
        for step in steps:
            if not step.complete:
                return False
        return True

    def is_execution_complete(self, execution_id):
        for path in current_app.db_session.query(current_app.Path).filter(current_app.Path.execution_id == execution_id).all():
            if not self.is_path_complete(path.id):
                return False
        return True

    def resume(self,name,execution,step,response,env={}):
        container = self.find_container_by_workflow_name(name)
        if not container:
            raise ValueError("Container not found. Please refresh it.")

        command = "python3 /app/workflow/tmp/router.py --execution_id {} --step_hash {} --response '{}' --request '{}'".format(step.execution_id,step.hash,response,step.request)
        container.exec_run(command,environment=env)
        response = {
            "id":execution.id,
            "uuid":execution.uuid,
            "resumed_step":step.uuid,
            "callback_url":"/api/v1/executions/{}".format(execution.uuid),
            "status":"resuming",
        }
        return response

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
            execution = current_app.db_session.query(current_app.Execution).filter(current_app.Execution.id == execution.id).first()
            logs = ""
            if execution.logs:
                logs = execution.logs.split("\n")
            debug = ""
            if execution.user_messages:
                debug = execution.user_messages.split("\n")
            response = {
                "id":execution.id,
                "uuid":execution.uuid,
                "return_value":self.return_value_for_execution(execution.id, execution.return_hash),
                "return_hash":execution.return_hash,
                "logs":logs,
                "debug":debug,
                "complete":self.is_execution_complete(execution.id),
                "failed":execution.failed,
                "execution_time":self.execution_time_for_execution(execution.id),
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
