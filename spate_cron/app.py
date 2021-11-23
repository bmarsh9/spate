import json
import os
import sys
import time
from config import Config
import arrow
import logging
from utils.workflow_manager import WorkflowManager

class Scheduler():
    def __init__(self,app):
        pass

    def run(self):
        while True:
            logging.debug("(Looping) Processing the triggers.")
            for trigger in self.ready_to_run():
                logging.info("Executing trigger: {}".format(trigger.name))
                self.execute_trigger(trigger)
                self.was_executed(trigger)
            logging.debug("Completed loop. Sleeping for {} seconds".format(app.SLEEP_TIME))
            time.sleep(app.SLEEP_TIME)

    def execute_trigger(self,trigger):
        workflow = app.db_session.query(app.Workflow).filter(app.Workflow.id == trigger.workflow_id).first()
        if not workflow:
            logging.warning("Workflow ID: {} does not exist".format(trigger.workflow_id))
            return False
        results = WorkflowManager(app,app.docker_client,workflow.id).run(workflow.name)
        return results

    def ready_to_run(self):
        triggers = []
        now = arrow.utcnow()
        enabled_triggers = app.db_session.query(app.Operator).filter(app.Operator.subtype == "cron").filter(app.Operator.official == False).all()
        logging.debug("Found {} triggers".format(len(enabled_triggers)))
        for trigger in enabled_triggers:
            if not trigger.last_executed: # never ran
                logging.debug("{} trigger has not executed. Adding.".format(trigger.name))
                triggers.append(trigger)
            else:
                minutes = trigger.run_every or 1
                if arrow.get(trigger.last_executed).shift(minutes=int(minutes)) < now:
                    logging.debug("{} trigger is within schedule for execution. Adding.".format(trigger.name))
                    triggers.append(trigger)
        logging.debug("{} triggers are ready for execution".format(len(triggers)))
        return triggers

    def was_executed(self,operator):
        now = arrow.utcnow().datetime
        operator.last_executed = now
        app.db_session.commit()
        return True

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app = Config(base_dir)
    logging.basicConfig(stream=sys.stdout,
            level=getattr(logging,app.LOG_LEVEL),
            format='%(asctime)s %(levelname)-8s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.info("Starting the scheduler. Version {}".format(app.VERSION))

    if not app.Operator:
        logging.critical("Database is not ready. Exiting...")
    else:
        # Start service
        Scheduler(app).run()
