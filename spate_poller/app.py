import json
import os
import sys
import time
from config import Config
import tasks as schtasks
import logging

class Poller():
    def __init__(self,app):
        pass

    def run(self):
        while True:
            logging.debug("(Looping) Processing the tasks")
            for task in app.TASKS:
                if task["enabled"]:
                    logging.info("Executing task: {}".format(task["name"]))
                    try:
                        result = getattr(schtasks,task["module"])(app, logging)
                    except Exception as e:
                        logging.error("Exception when processing task:{}. Error:{}".format(task["module"],e))
                else:
                    logging.debug("Skipping disabled task:{}".format(task["name"]))
            logging.debug("Completed loop. Sleeping for {} seconds".format(app.SLEEP_TIME))
            time.sleep(app.SLEEP_TIME)

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app = Config(base_dir)
    logging.basicConfig(stream=sys.stdout,
            level=getattr(logging,app.LOG_LEVEL),
            format='%(asctime)s %(levelname)-8s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.info("Starting the poller. Version {}".format(app.VERSION))

    if not app.Workflow:
        logging.critical("Database is not ready. Exiting...")
    else:
        # Start service
        Poller(app).run()
