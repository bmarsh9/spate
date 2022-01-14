from flask import current_app
from flask_script import Command
from app.models import *
from app import db
import datetime

class InitDbCommand(Command):
    """ Initialize the database."""

    def run(self):
        init_db()
        print('Database has been initialized.')

def init_db():
    """ Initialize the database."""
    db.drop_all()
    db.create_all()
    create_users()
    create_default_workflow()

def create_users():
    """ Create users """
    default_user = current_app.config.get("DEFAULT_EMAIL","admin@example.com")
    default_password = current_app.config.get("DEFAULT_PASSWORD","admin")
    if not User.query.filter(User.email == default_user).first():
        user = User(
            email=default_user,
            email_confirmed_at=datetime.datetime.utcnow(),
        )
        user.set_password(default_password)
        user.roles.append(Role(name='Admin'))
        user.roles.append(Role(name='User'))
        db.session.add(user)
        db.session.commit()

def create_default_workflow():
    attrs = {
        "imports":"import logging,os,sys,json,glob",
        "label":"Default Workflow",
        "description":"This is the demo workflow",
    }
    workflow = Workflow.add(**attrs)
    Operator.add(workflow.id,type="trigger",label="API Ingress",description="Creates an API Endpoint that will trigger your workflow",official=True,subtype="api")
    Operator.add(workflow.id,type="trigger",label="Sensor",description="Periodically runs and will trigger your workflow",official=True,subtype="cron")
    Operator.add(workflow.id,type="trigger",label="Form",description="Creates a UI form that will trigger your workflow",official=True,subtype="form")
    Operator.add(workflow.id,type="action",label="Basic Operator",description="Basic Operator that allows you to input your own code",official=True)

    Operator.add(workflow.id,type="misc",label="User Input",description="Collect user input before proceeding",official=True,subtype="input")
    #Operator.add(workflow.id,type="misc",label="Return Value",description="Returns the output value of a single path inside your workflow",official=True,add_output=False)
    return True
