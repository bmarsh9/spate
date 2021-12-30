import datetime
import os

def remove_stale_workflow_containers(app, logging):
    number_of_stopped_containers = 0
    list_of_workflow_names = []
    for workflow in app.db_session.query(app.Workflow).all():
        list_of_workflow_names.append(workflow.name.lower())
    for container in app.docker_client.containers.list():
        label = container.labels.get("workflow_name","").lower()
        if label.startswith("workflow"):
            if label not in list_of_workflow_names:
                logging.info("Container workflow label:{} does not exist in the database. Removing.".format(label))
                container.stop()
                container.remove()
                number_of_stopped_containers += 1
    logging.info("Removed {} containers.".format(number_of_stopped_containers))
    return True

def send_email_for_paused_path(app, logging):
    pass
