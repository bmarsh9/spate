import docker
import json
from datetime import datetime

class WorkflowManager():
    def __init__(self, app, docker_client, workflow_id):
        self.current_app = app
        self.docker_client = docker_client
        self.workflow_id = workflow_id

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

    def add_in_progress_result(self):
        result = self.current_app.Result(workflow_id=self.workflow_id,status="in progress",date_added=datetime.utcnow())
        self.current_app.db_session.add(result)
        self.current_app.db_session.commit()
        return result

    def run(self,name,env={},request={}):
        container = self.find_container_by_workflow_name(name)
        if not container:
            raise ValueError("Container not found")
        result = self.add_in_progress_result()
        command = "python3 /app/workflow/tmp/router.py {} '{}'".format(result.id,json.dumps(request))
        container.exec_run(command,environment=env,detach=True)
        return True
