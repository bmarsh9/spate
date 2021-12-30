from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
import sqlalchemy
import os
import docker

db = automap_base()

class Config():
    def __init__(self,base_dir):
        # --------------------------------- Poller Setting
        self.APP_NAME = os.environ.get("APP_NAME","Spate")
        self.API_HOST = os.environ.get("API_HOST")
        self.VERSION = os.environ.get("VERSION","1.0.0")
        self.LOG_LEVEL = os.environ.get("LOG_LEVEL","DEBUG")
        self.SLEEP_TIME = os.environ.get("SLEEP_TIME",120)

        db_uri = os.environ.get("SQLALCHEMY_DATABASE_URL","postgresql://db1:db1@postgres_db/db1")
        db_engine = sqlalchemy.create_engine(db_uri)
        db.prepare(db_engine,reflect=True)
        self.db_session = Session(db_engine)
        self.Workflow = db.classes.workflows
        self.Operator = db.classes.operators
        self.Step = db.classes.steps

        self.docker_client = docker.from_env()

        self.MAIL_SERVER = 'smtp.googlemail.com'
        self.MAIL_PORT = 587
        self.MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
        self.MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

        self.TASKS = [
            {"name":"Remove stale workflow containers","module":"remove_stale_workflow_containers","enabled":True},
            {"name":"Send notification email for paused paths","module":"send_email_for_paused_path","enabled":True},
        ]
