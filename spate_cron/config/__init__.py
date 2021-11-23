from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
import sqlalchemy
import os
import docker

db = automap_base()

class Config():
    def __init__(self,base_dir):
        # --------------------------------- Scheduler Setting
        self.VERSION = os.environ.get("VERSION","1.0.0")
        self.LOG_LEVEL = os.environ.get("LOG_LEVEL","DEBUG")
        self.SLEEP_TIME = os.environ.get("SLEEP_TIME",10)

        db_uri = os.environ.get("SQLALCHEMY_DATABASE_URL","postgresql://db12:db12@10.0.10.171/db12")
        db_engine = sqlalchemy.create_engine(db_uri)
        db.prepare(db_engine,reflect=True)
        self.db_session = Session(db_engine)
        self.Workflow = db.classes.workflows
        self.Operator = db.classes.operators
        self.Result = db.classes.results

        self.docker_client = docker.from_env()
