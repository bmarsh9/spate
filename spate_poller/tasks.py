import datetime
import os
from utils.email import send_email

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
    if not app.API_HOST or not app.MAIL_USERNAME or not app.MAIL_PASSWORD:
        logging.warning("Missing required env variables for sending emails")
        return False
    for step in app.db_session.query(app.Step).filter(app.Step.status == "paused").all():
        for operator in app.db_session.query(app.Operator).filter(app.Operator.email_status == "ready").all():
            recipients = operator.paused_email_to.split(",")
            if recipients:
                logging.info("Sending email for paused step:{}-{}".format(step.name,step.uuid))
                send_email(app,step,operator.paused_email_to)
                operator.email_status = "sent"
                app.db_session.commit()
    return True
