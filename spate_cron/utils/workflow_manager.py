import docker
import json
from datetime import datetime
import logging
import uuid
import hashlib

class WorkflowManager():
    def __init__(self, app, docker_client, workflow_id):
        self.current_app = app
        self.docker_client = docker_client
        self.workflow_id = workflow_id
        self.workflow = self.current_app.db_session.query(self.current_app.Workflow).filter(self.current_app.Workflow.id == workflow_id).first()

    def find_container_by_workflow_name(self,name,by_id=False):
        '''search for workflow_name key set on the
        container labels
        '''
        for container in self.docker_client.containers.list():
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
        step = self.current_app.db_session.query(self.current_app.Step).filter(self.current_app.Step.hash == hash).filter(self.current_app.Step.execution_id == execution_id).first()
        if step:
            return step
        new_step = self.current_app.Step(uuid=self.generate_uuid(),name=name,label=label,hash=hash,
            execution_id=execution_id,status="not started",date_added=datetime.utcnow())
        self.current_app.db_session.add(new_step)
        self.current_app.db_session.commit()
        return new_step

    def add_execution(self):
        tree = self.workflow.map
        # create execution object
        execution = self.current_app.Execution(uuid=self.generate_uuid(),return_hash=tree["return_path"],
            workflow_id=self.workflow_id,date_added=datetime.utcnow())
        self.current_app.db_session.add(execution)
        self.current_app.db_session.flush()

        # create all paths and associate them to the steps
        for path in tree["paths"]:
            for path_hash,steps in path.items():
                new_path = self.current_app.Path(hash=path_hash,uuid=self.generate_uuid(),execution_id=execution.id,date_added=datetime.utcnow())
                self.current_app.db_session.add(new_path)
                self.current_app.db_session.flush()
                for previous_step, current_step in zip(steps, steps[1:]):
                    step_hash = self.create_hash_for_steps(steps[:steps.index(current_step)])
                    step = self.find_or_create_step(current_step["name"],current_step["label"],step_hash,execution.id)
                    ps = self.current_app.PathSteps(step_id=step.id,path_id=new_path.id)
                    self.current_app.db_session.add(ps)
                self.current_app.db_session.commit()
        return execution

    def run(self,env={},request={}):
        container = self.find_container_by_workflow_name(self.workflow.name)
        if not container:
            logging.warning("Container not found. Please refresh the {} workflow".format(self.workflow.name))
            return False

        execution = self.add_execution()

        command = "python3 /app/workflow/tmp/router.py --execution_id {} --request '{}'".format(execution.id,json.dumps(request))
        container.exec_run(command,environment=env,detach=True)

        return True
