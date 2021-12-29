from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import func,and_,or_
from app.utils.mixin_models import LogMixin
from flask_login import UserMixin
from app.utils.misc import generate_uuid
from app.utils.code_template import *
from flask import current_app,render_template
from networkx.readwrite import json_graph
from app.utils.docker_manager import DockerManager
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
import networkx as nx
from datetime import datetime
from app.email import send_email
from app import db, login
import hashlib
import shutil
import arrow
import json
import inspect
import os

class IntakeForm(LogMixin,db.Model):
    __tablename__ = 'intake_forms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    label = db.Column(db.String())
    enabled = db.Column(db.Boolean, default=True)
    description = db.Column(db.String())
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    data = db.Column(db.JSON(),default={})
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

class LockerAccess(LogMixin,db.Model):
    __tablename__ = 'locker_access'
    id = db.Column(db.Integer(), primary_key=True)
    locker_id = db.Column(db.Integer(), db.ForeignKey('lockers.id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))

class Locker(LogMixin,db.Model):
    __tablename__ = 'lockers'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), unique=True)
    label = db.Column(db.String())
    config = db.Column(db.JSON(),default={})
    users = db.relationship('User', secondary='locker_access',lazy='dynamic')
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @staticmethod
    def find_by_name(name):
        locker_exists = Locker.query.filter(func.lower(Locker.name) == func.lower(name)).first()
        if locker_exists:
            return locker_exists
        return False

    @staticmethod
    def add(name=None):
        if not name:
            name = "Locker_{}".format(generate_uuid(length=10))
        new_locker = Locker(name=name,label=name)
        db.session.add(new_locker)
        db.session.commit()
        return new_locker

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def remove_from_all_workflows(self):
        AssocLocker.query.filter(AssocLocker.locker_id == self.id).delete()
        db.session.commit()
        return True

    def set_workflows_by_name(self,workflows):
        self.remove_from_all_workflows()
        if not isinstance(workflows,list):
            workflows = [workflows]
        for name in workflows:
            found = Workflow.find_by_name(name)
            if found:
                assoc = AssocLocker(locker_id=self.id,workflow_id=found.id)
                db.session.add(assoc)
                db.session.commit()
        return True

    def remove_from_all_users(self):
        LockerAccess.query.filter(LockerAccess.locker_id == self.id).delete()
        db.session.commit()
        return True

    def set_users_by_id(self,users):
        self.remove_from_all_users()
        if not isinstance(users,list):
            users = [users]
        for id in users:
            found = User.query.get(id)
            if found:
                assoc = LockerAccess(locker_id=self.id,user_id=id)
                db.session.add(assoc)
                db.session.commit()
        return True

    def get_workflows(self):
        workflows = []
        for assoc in AssocLocker.query.filter(AssocLocker.locker_id == self.id).all():
            workflow = Workflow.query.get(assoc.workflow_id)
            if workflow:
                workflows.append(workflow)
        return workflows

    def add_key(self,key,value):
        self.config = {**self.config,**{key:value}}
        db.session.commit()
        return True

    def get_workflows_ex(self):
        '''used for select for showing workflows uses the locker'''
        workflows = {}
        all_workflows = Workflow.query.all()
        locker_workflows = self.get_workflows()
        for workflow in all_workflows:
            if workflow in locker_workflows:
                workflows[workflow] = True
            else:
                workflows[workflow] = False
        return workflows

    def can_user_access(self,id):
        user = User.query.get(id)
        if not user:
            return False
        if user.has_role("admin"):
            return True
        if user.has_locker(self.id):
            return True
        return False

class AssocLocker(LogMixin,db.Model):
    __tablename__ = 'assoc_lockers'
    id = db.Column(db.Integer(), primary_key=True)
    locker_id = db.Column(db.Integer(), db.ForeignKey('lockers.id', ondelete='CASCADE'))
    workflow_id = db.Column(db.Integer(), db.ForeignKey('workflows.id', ondelete='CASCADE'))

class PathSteps(db.Model):
    __tablename__ = 'path_steps'
    id = db.Column(db.Integer(), primary_key=True)
    step_id = db.Column(db.Integer(), db.ForeignKey('steps.id', ondelete='CASCADE'))
    path_id = db.Column(db.Integer(), db.ForeignKey('paths.id', ondelete='CASCADE'))

class Step(db.Model, LogMixin):
    __tablename__ = 'steps'
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(),nullable=False)
    name = db.Column(db.String(),nullable=False)
    label = db.Column(db.String())
    hash = db.Column(db.String(),nullable=False)
    request = db.Column(db.JSON(),default={})
    status = db.Column(db.String(),default="not started") #paused,no started,responded,complete
    complete = db.Column(db.Boolean, default=False)
    result = db.Column(db.String())
    execution_time = db.Column(db.Integer(),default=0)
    logs = db.Column(db.String(),default="")
    execution_id = db.Column(db.Integer, db.ForeignKey('executions.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @staticmethod
    def find_or_create_step(name,label,hash,execution_id):
        step = Step.query.filter(Step.hash == hash).filter(Step.execution_id == execution_id).first()
        if step:
            return step
        new_step = Step(uuid=generate_uuid(),name=name,label=label,hash=hash,execution_id=execution_id)
        db.session.add(new_step)
        db.session.commit()
        return new_step

class Path(db.Model, LogMixin):
    __tablename__ = 'paths'
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(),nullable=False)
    hash = db.Column(db.String(),nullable=False)
    logs = db.Column(db.String(),default="")
    steps = db.relationship('Step', secondary='path_steps', lazy='dynamic')
    execution_id = db.Column(db.Integer, db.ForeignKey('executions.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def execution_time(self):
        time = 0
        for step in self.steps.all():
            if step.execution_time:
                time += step.execution_time
        return time

    def paused(self,as_object=False):
        for step in self.steps.order_by(Step.id.asc()).all():
            if step.status == "paused":
                if as_object:
                    return step
                return True
        return False

    def result(self):
        step = self.steps.order_by(Step.id.desc()).first()
        return step.result

    def has_form(self):
        step = self.paused(as_object=True)
        if step:
            operator = Operator.query.filter(Operator.name == step.name).first()
            if operator:
                return operator.form_id
        return False

    def get_paused_uuid(self):
        step = self.status(as_object=True)
        if step.status == "paused":
            return step.uuid
        return None

    def send_paused_email(self):
        step = self.paused(as_object=True)
        if not step:
            raise ValueError("Path is not paused")
        operator = Operator.find_by_name(step.name)
        if not operator:
            raise ValueError("Operator name not found for the paused path")
        button_link = os.path.join(current_app.config["API_HOST"],"resume/{}".format(step.uuid))
        title = "{}: We need your input".format(current_app.config["APP_NAME"])
        content = "We need to collect your input for the {} workflow".format(operator.workflow.label)
        send_email(
          title,
          sender=current_app.config["DEFAULT_EMAIL"],
          recipients=operator.paused_email_to.split(","),
          text_body=render_template(
            'email/user_input.txt',
            title=title,content=content,button_link=button_link
          ),
          html_body=render_template(
            'email/user_input.html',
            title=title,content=content,button_link=button_link
          )
        )
        return True

    def status(self,as_object=False):
        for step in self.steps.order_by(Step.id.asc()).all():
            if not step.complete:
                if as_object:
                    return step
                return step.status
        if as_object:
            return self.steps.order_by(Step.id.desc()).first()
        return self.steps.order_by(Step.id.desc()).first().status

    def get_path_order(self):
        return self.steps.order_by(Step.id.asc()).all()

    def complete(self):
        step = self.steps.order_by(Step.id.desc()).first()
        return step.complete

class Execution(db.Model, LogMixin):
    __tablename__ = 'executions'
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String())
    return_hash = db.Column(db.String())
    user_messages = db.Column(db.String(),default="")
    failed = db.Column(db.Boolean, default=False)
    logs = db.Column(db.String(),default="")
    paths = db.relationship('Path', backref='execution', lazy='dynamic')
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflows.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def get_return_value(self):
        path = self.paths.filter(Path.hash == self.return_hash).first()
        if not path:
            return {}
        return path.result()

    def execution_time(self):
        time = 0
        for path in self.paths.all():
            time+= path.execution_time()
        return time

    def complete(self):
        for path in self.paths.all():
            if not path.complete():
                return False
        return True

    def paused(self):
        for path in self.paths.all():
            if path.paused():
                return True
        return False

    def trigger_type(self):
        trigger = self.workflow.get_trigger()
        if trigger:
            return trigger.subtype
        return "unknown"

    def as_dict(self):
        debug = ""
        logs = ""
        if self.logs:
            logs = self.logs.split("\n")
        if self.user_messages:
            debug = self.user_messages.split("\n")
        template = {
            "id":self.id,
            "return_value":self.get_return_value(),
            "return_hash":self.return_hash,
            "logs":logs,
            "debug":debug,
            "complete":self.complete(),
            "paused":self.paused(),
            "execution_time":self.execution_time(),
            "date_requested":str(self.date_added),
        }
        return template

    def finished(self):
        if not self.date_added:
            return "unknown"
        return arrow.get(self.date_added).humanize()

class Workflow(db.Model, LogMixin):
    __tablename__ = 'workflows'
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(),nullable=False)
    name = db.Column(db.String(),nullable=False)
    secret_key = db.Column(db.String())
    label = db.Column(db.String())
    base_image = db.Column(db.String())
    auth_required = db.Column(db.Boolean, default=False)
    enabled = db.Column(db.Boolean, default=False)
    refresh_required = db.Column(db.Boolean, default=True)
    description = db.Column(db.String())
    imports = db.Column(db.String())
    log_level = db.Column(db.String(),default="info")
    map = db.Column(db.JSON(),default="{}")
    config = db.Column(db.JSON(),default="{}")
    lockers = db.relationship('Locker', secondary='assoc_lockers', lazy='dynamic')
    operators = db.relationship('Operator', backref='workflow', lazy='dynamic')
    executions = db.relationship('Execution', backref='workflow', lazy='dynamic')
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def generate_auth_token(self, expiration = 6000):
        s = Serializer(self.secret_key, expires_in = expiration)
        token = s.dumps({ 'workflow_id': self.id })
        return token.decode("utf-8")

    @staticmethod
    def verify_invite_token(token):
        s = Serializer(self.secret_key)
        try:
            data = s.loads(token)
        except SignatureExpired:
            return False # valid token, but expired
        except BadSignature:
            return False # invalid token
        return True

    def create_hash_for_steps(self,values):
        sha1 = hashlib.sha1()
        for value in values:
            val = str(value["name"]).encode('utf-8')
            sha1.update(val)
        return sha1.hexdigest()

    def add_execution(self):
        tree = self.path_tree()
        # create execution object
        execution = Execution(uuid=generate_uuid(),return_hash=tree["return_path"],
            workflow_id=self.id)
        db.session.add(execution)
        db.session.flush()

        # create all paths and associate them to the steps
        for path in tree["paths"]:
            for path_hash,steps in path.items():
                new_path = Path(hash=path_hash,uuid=generate_uuid(),execution_id=execution.id)
                for previous_step, current_step in zip(steps, steps[1:]):
                    step_hash = self.create_hash_for_steps(steps[:steps.index(current_step)])
                    step = Step.find_or_create_step(current_step["name"],current_step["label"],step_hash,execution.id)
                    new_path.steps.append(step)
                db.session.add(new_path)
                db.session.commit()
        return execution

    def as_meta(self):
        needs_trigger = False
        needs_form = False

        trigger = self.get_trigger()
        if not trigger:
            needs_trigger = True
        else:
            if trigger.subtype == "form" and not trigger.form_id:
                needs_form = True
        return {
            "id":self.id,
            "uuid":self.uuid,
            "name":self.name,
            "label":self.label,
            "enabled":self.enabled,
            "has_return_value":self.has_return_value(),
            "needs_trigger":needs_trigger,
            "needs_form":needs_form,
            "refresh_required":self.refresh_required,
        }

    @staticmethod
    def add(**kwargs):
        uuid = generate_uuid(length=10)
        name = "Workflow_{}".format(uuid)
        if not kwargs.get("imports"):
            kwargs["imports"] = "import logging,os,sys,json,random"
        kwargs["name"] = name
        if "label" not in kwargs:
            kwargs["label"] = name
        kwargs["uuid"] = uuid
        kwargs["secret_key"] = generate_uuid()
        kwargs["base_image"] = current_app.config["BASE_PYTHON_IMAGE"]
        workflow = Workflow(**kwargs)
        db.session.add(workflow)
        db.session.commit()
        # add default locker
        locker_name = "Locker_{}".format(uuid)
        locker = Locker.add(name=locker_name)
        locker.set_workflows_by_name(name)
        return workflow

    @staticmethod
    def find_by_name(name):
        workflow_exists = Workflow.query.filter(func.lower(Workflow.name) == func.lower(name)).first()
        if workflow_exists:
            return workflow_exists
        return False

    def create_default_locker(self):
        name = "Locker_{}".format(self.name.split("_")[1])
        locker = Locker.add(name=name)
        locker.set_workflows_by_name(self.name)
        return locker

    def get_default_locker(self,create=False):
        name = "Locker_{}".format(self.name.split("_")[1])
        locker = Locker.query.filter(func.lower(Locker.name) == func.lower(name)).first()
        if not locker and create:
            locker = self.create_default_locker()
        return locker

    def has_return_value(self):
        has_return = False
        trigger = self.get_trigger()
        if not trigger:
            return False
        if not trigger.return_path:
            return False
        for path in self.path_tree(operator_id=trigger.id).get("paths",[]):
            for path_name,functions in path.items():
                if path_name == trigger.return_path:
                    has_return = True
        return has_return

    def get_read_user_access(self):
        '''warning... this function is just for the form. It does not include the users with perm_level > 1 (which do have read access)'''
        users = []
        for user in WorkflowUser.query.filter(WorkflowUser.workflow_id == self.id).filter(WorkflowUser.permission == 1).all():
            user = User.query.get(user.user_id)
            if user and user not in users:
                users.append(user)
        return users

    def get_write_user_access(self):
        users = []
        for user in WorkflowUser.query.filter(WorkflowUser.workflow_id == self.id).filter(WorkflowUser.permission == 2).all():
            user = User.query.get(user.user_id)
            if user and user not in users:
                users.append(user)
        return users

    def set_user(self,user_id,permission_level=1):
        '''
        give/take user access to the workflow
        0 = remove access
        1 = read access
        2 = write access
        '''
        if int(permission_level) not in [0,1,2]:
            raise ValueError("Permission level must be 0, 1 or 2")
        user = WorkflowUser.query.filter(WorkflowUser.workflow_id == self.id).filter(WorkflowUser.user_id == user_id).first()
        if permission_level == 0 and user:
            db.session.delete(user)
            db.session.commit()
        if user:
            user.permission = permission_level
            db.session.commit()
        if not user:
            user = WorkflowUser(workflow_id=self.id,user_id=user_id,permission=permission_level)
            db.session.add(user)
            db.session.commit()
        return True

    def user_can_read(self,user_id):
        user = User.query.get(user_id)
        if not user:
            return False
        if user.has_role("admin"):
            return True
        user = WorkflowUser.query.filter(WorkflowUser.workflow_id == self.id).filter(WorkflowUser.user_id == user_id).first()
        if not user:
            return False
        return True

    def user_can_write(self,user_id):
        user = User.query.get(user_id)
        if not user:
            return False
        if user.has_role("admin"):
            return True
        user = WorkflowUser.query.filter(WorkflowUser.workflow_id == self.id).filter(WorkflowUser.user_id == user_id).first()
        if not user:
            return False
        if user.permission == 2:
            return True
        return False

    def last_executed(self):
        latest_execution = self.executions.order_by(Execution.id.desc()).first()
        if not latest_execution:
            return "never"
        if not latest_execution.date_added:
            return "unknown"
        return arrow.get(latest_execution.date_added).humanize()

    def create_file(self, path, content):
        with open(path, 'w') as f:
            f.write(content)
        return True

    def run(self,setup=False,refresh=True,restart=False,output="log",env={},request={}):
        trigger = self.get_trigger()
        if not trigger:
            return False
        if setup:
            self.setup_workflow(refresh=refresh)
        dm = DockerManager()
        container_id = dm.find_container_by_workflow_name(self.name).short_id

        execution = self.add_execution()

        response = dm.exec_to_container(container_id,"python3 /app/workflow/tmp/router.py --execution_id {} --request '{}'".format(execution.id,json.dumps(request)),
            output=output,detach=not trigger.synchronous,env=env)
        if trigger.synchronous:
            response = ""
        else:
            response = {
                "callback_url":"/api/v1/workflows/{}/executions/{}".format(self.id,execution.id),
                "status":"in progress",
            }
        return response
    '''
    #TODO remove and place in api-ingress
    def resume(self,step,response):
        trigger = self.get_trigger()
        if not trigger:
            return False
        dm = DockerManager()
        id = dm.find_container_by_workflow_name(self.name).short_id
        response = dm.exec_to_container(id,"python3 /app/workflow/tmp/router.py --execution_id {} --step_hash {} --response {}".format(step.execution_id,step.hash,response),
            output="log",detach=not trigger.synchronous,env={})
        return response
    '''

    def setup_workflow(self,refresh=True,restart=False):
        self.setup_workflow_folder()
        self.setup_workflow_container(refresh=refresh,restart=restart)
        self.setup_configstore()
        return True

    def setup_workflow_container(self,refresh=True,restart=False):
        workflow_dir = os.path.join(current_app.config["WORKFLOW_MOUNT_DIRECTORY"],self.name,"tmp")
        dm = DockerManager()
        container = dm.get_container(self.name)
        if container:
            if container.status != "running":
                container.restart()
        if not container:
            dict = {}
            if current_app.config["LOCAL_DB"]:
                dict["network"] = current_app.config["POSTGRES_NW"]
            dm.run_container(self.base_image,labels={"workflow_name":self.name},name=self.name,**dict)
            container = dm.get_container(self.name)
            dm.copy_to(container,workflow_dir,"/app/workflow")
        else:
            if restart:
                container.restart()
        if refresh:
            container = dm.get_container(self.name)
            dm.copy_to(container,workflow_dir,"/app/workflow")
        return True

    def setup_configstore(self):
        c = ConfigStore.find_by_name(self.name)
        if not c:
            c = ConfigStore(name=self.name)
            db.session.add(c)
            db.session.commit()
        return True

    def setup_workflow_folder(self,clean=True,remove=False):
        parent_dir = os.path.join(current_app.config["WORKFLOW_MOUNT_DIRECTORY"],self.name)
        workflow_dir = os.path.join(current_app.config["WORKFLOW_MOUNT_DIRECTORY"],self.name,"tmp")
        if clean and os.path.exists(workflow_dir):
            shutil.rmtree(workflow_dir)
        if remove and os.path.exists(parent_dir):
            shutil.rmtree(parent_dir)
        if not os.path.exists(parent_dir):
            os.mkdir(parent_dir)
        if not os.path.exists(workflow_dir):
            os.mkdir(workflow_dir)
        for operator in self.operators.filter(Operator.official == False).all():
            op_dir = os.path.join(workflow_dir,operator.name)
            if not os.path.exists(op_dir):
                os.mkdir(op_dir)
            operator.create_code_folder(op_dir)
        map = self.path_tree()
        self.map = map
        db.session.commit()
        self.create_file(os.path.join(workflow_dir,"router.py"),default_router_code(workflow_dir))
        self.create_file(os.path.join(workflow_dir,"workflow_map.json"),json.dumps(map,indent=4))
        self.create_file(os.path.join(workflow_dir,"config.ini"),self.to_config_file())
        self.create_file(os.path.join(workflow_dir,"store.json"),"{}")
        self.create_file(os.path.join(workflow_dir,"__init__.py"),"")
        return True

    def get_locker_attrs(self):
        data = {}
        for locker in self.lockers.all():
            data[locker.name] = locker.config
        # add default locker
        data["default"] = self.get_default_locker(create=True).config
        return data

    def to_config_file(self):
        '''
        config file loaded inside the docker container
        '''
        docker_tmp_dir = "/app/workflow/tmp" # directory that exists in docker container
        host_dir = os.path.join(current_app.config["WORKFLOW_MOUNT_DIRECTORY"],self.name)
        workflow_path = os.path.join(docker_tmp_dir,"workflow_map.json")
        config_path = os.path.join(docker_tmp_dir,"config.ini")
        json_store = os.path.join(docker_tmp_dir,"store.json")
        config = """
        [config]
        workflow_name={}
        workflow_dir={}
        workflow_map={}
        config_path={}
        store={}
        host_dir={}
        log_level={}
        env={}
        lockers={}
        workflow_id={}
        sqlalchemy_database_url={}
        """.format(self.name,docker_tmp_dir,workflow_path,config_path,json_store,
            host_dir,self.log_level,{},json.dumps(self.get_locker_attrs()),
            self.id,current_app.config["SQLALCHEMY_DATABASE_URI"])
        return inspect.cleandoc(config)

    def set_lockers_by_name(self,lockers):
        if not isinstance(lockers,list):
            lockers = [lockers]
        new_lockers = []
        for locker in lockers:
            found = Locker.find_by_name(locker)
            if found:
                new_lockers.append(found)
        self.lockers[:] = new_lockers
        db.session.commit()
        return True

    def to_html_settings(self):
        checked = ""
        if self.enabled:
            checked = "checked"
        auth_checked = ""
        if self.auth_required:
            auth_checked = "checked"
        log_html = ""
        for level in ["info","debug","warning","error","critical"]:
            select = ""
            if level == self.log_level:
                select = "selected"
            log_html+='<option value="{}" {}>{}</option>'.format(level,select,level)
        return """
        <div class="modal-body">
          <div class="mb-2">
            <label class="form-label col-3 col-form-label">Name</label>
            <div class="col">
              <input type="text" class="form-control" name="example-disabled-input" value="{}" disabled="">
            </div>
          </div>
          <div class="mb-2">
            <label class="form-label">Label</label>
            <input type="text" class="form-control" id="workflow_label" value="{}" placeholder="Workflow label">
          </div>
          <div class="form-selectgroup-boxes row mb-2">
            <div class="col-lg-12">
              <div class="form-group row">
                <div class="row">
                  <label class="row">
                    <span class="col form-label">Enabled</span>
                    <span class="col-auto">
                      <label class="form-check form-check-single form-switch">
                        <input id="workflow_enabled" class="form-check-input cursor-pointer" type="checkbox" {}>
                      </label>
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>
          <div class="form-selectgroup-boxes row mb-2">
            <div class="col-lg-12">
              <div class="form-group row">
                <div class="row">
                  <label class="row">
                    <span class="col form-label">Authentication Required</span>
                    <span class="col-auto">
                      <label class="form-check form-check-single form-switch">
                        <input id="workflow_auth" class="form-check-input cursor-pointer" type="checkbox" {}>
                      </label>
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>
          <div class="mb-2">
            <label class="form-label">Description</label>
            <textarea class="form-control" id="workflow_description" rows="2">{}</textarea>
          </div>
          <div class="mb-2">
            <label class="form-label">Base Docker Image</label>
            <input type="text" class="form-control" id="workflow_image" value="{}" placeholder="Workflow base image">
          </div>
          <div class="mb-2">
            <label class="form-label">Imports</label>
            <textarea class="form-control" id="workflow_imports" rows="2">{}</textarea>
          </div>
          <div class="mb-3">
            <div class="form-label">Log Level</div>
              <select id="log_level" class="form-select">{}
              </select>
          </div>
        </div>
        <div class="modal-footer">
          <a href="#" class="btn btn-link link-secondary" data-bs-dismiss="modal">
            Cancel
          </a>
          <a href="#" onclick="saveWorkflowSettings('{}')" class="btn btn-primary ms-auto">
            Save
          </a>
        </div>
        """.format(self.name,self.label,checked,auth_checked,self.description,self.base_image,self.imports,log_html,self.name)

    def to_workflow(self):
        config = {"operators":{},"links":{}}
        for operator in self.operators.all():
            config["operators"][operator.name] = operator.to_json()
            config["links"] = {**config["links"],**operator.format_links()}
        return config

    def get_sidebar(self, search_term=None):
        data = []
        _query = Operator.query.filter(or_(Operator.official == True,Operator.public == True)).order_by(Operator.id.desc())
        if search_term:
            search = "%{}%".format(search_term)
            _query = _query.filter(Operator.label.ilike(search))
        for operator in _query.all(): # include workflow ID
            data.append({"type":operator.type,"html":operator.sidebar_html()})
        return data

    def get_trigger(self):
        return self.operators.filter(Operator.official == False).filter(Operator.type == "trigger").first()

    def is_trigger_api_endpoint(self):
        trigger = self.get_trigger()
        if not trigger:
            return False
        if trigger.subtype == "api":
            return True
        return False

    def to_tree(self,operator_id=None,identify_by="name"):
        data = []
        operator_tree = []
        def resolve_link(operator):
            links = operator.format_links()
            if links:
                for enum,(link_name,link_data) in enumerate(links.items()):
                    if identify_by == "label":
                        op_name = "{}__{}".format(operator.name,operator.label)
                        label = "{}__{}".format(link_name,link_data["connectorLabel"])
                        to_operator_label = "{}__{}".format(link_data["toOperator"],link_data["toOperatorLabel"])
                        data.append((op_name,label))
                        data.append((label,to_operator_label))
                    else:
                        data.append((operator.name,link_name))
                        data.append((link_name,link_data["toOperator"]))
                    to_operator = Operator.find_by_name(link_data["toOperator"])
                    operator_tree.append(to_operator)
            for operator in operator_tree:
                operator_tree.remove(operator)
                resolve_link(operator)

        if operator_id:
            operator = Operator.query.get(operator_id)
        else:
            operator = self.get_trigger()
        resolve_link(operator)

        if not data:
            data = [(operator.name,"")]

        parents, children = zip(*data)
        root_nodes = {x for x in parents if x not in children}
        for node in root_nodes:
            data.append((self.name, node))

        def get_nodes(node):
            d = {}
            d['name'] = node
            children = get_children(node)
            if children:
                d['children'] = [get_nodes(child) for child in children]
            return d

        def get_children(node):
            return [x[1] for x in data if x[0] == node]

        tree = get_nodes(self.name)
        return tree

    def flatten_tree(self):
        out = {}
        def flatten(x, name=''):
            if type(x) is dict:
                for a in x:
                    flatten(x[a], name + a + '_')
            elif type(x) is list:
                i = 0
                for a in x:
                    flatten(a, name + str(i) + '_')
                    i += 1
            else:
                out[name[:-1]] = x
        flatten(self.to_tree())
        return out

    def create_hash(self,values):
        sha1 = hashlib.sha1()
        for value in values:
            val = str(value).encode('utf-8')
            sha1.update(val)
        return sha1.hexdigest()

    def path_tree(self,source_node=None, operator_id=None, identify_by="name"):
        if not source_node:
            source_node = self.name
        G = json_graph.tree_graph(self.to_tree(operator_id=operator_id,identify_by=identify_by), ident="name")
        #get a list of sink nodes
        sinks = [node for node in G.nodes if G.out_degree(node) == 0]
        #get all shortest paths from source to sinks
        all_paths = [list(nx.all_simple_paths(G, source=source_node, target=sink)) for sink in sinks]
        paths = []
        for set in all_paths:
            if set:
                for path in set:
                    paths.append(path)
        #get first path since there is only one
        trigger = self.get_trigger()
        result = {"return_path":trigger.return_path or "","paths":[]}
        for path in paths:
            result["paths"].append(self.path_to_dictionary(path))
        return result

    def path_to_dictionary(self,path):
        data = []
        paths = []
        for step in path:
            name = step.split("__")[0]
            paths.append(name)
            if step.startswith("Operator"):
                pause = False
                op = Operator.find_by_name(name)
                if op.subtype == "input":
                    pause = True
                temp = {"id":op.id,"name":name,"label":op.label,"enabled":op.enabled,"type":"operator","pause":pause}
            elif step.startswith("Link"):
                link = OutputLink.find_by_name(name)
                temp = {"id":link.id,"name":name,"label":link.label,"enabled":link.enabled,"type":"link","pause":False}
            elif step.startswith("Workflow"):
                wf = Workflow.find_by_name(name)
                temp = {"id":wf.id,"name":name,"label":wf.label,"enabled":wf.enabled,"type":"workflow","pause":False}
            else:
                temp = {}
            if temp:
                temp["hash"] = self.create_hash(path[:path.index(step)])
                data.append(temp)
        path_hash = self.create_hash(paths)
        return {path_hash:data}

class Operator(db.Model, LogMixin):
    __tablename__ = 'operators'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(),nullable=False,unique=True)
    label = db.Column(db.String(),nullable=False) #nullable
    type = db.Column(db.String(),nullable=False,default="action")
    subtype = db.Column(db.String())
    description = db.Column(db.String())
    documentation = db.Column(db.String())
    imports = db.Column(db.String())
    git_stored = db.Column(db.Boolean, default=False)
    hash = db.Column(db.String())
    git_url = db.Column(db.String())
    git_sync_date = db.Column(db.DateTime)
    synchronous = db.Column(db.Boolean, default=False)
    enabled = db.Column(db.Boolean, default=True)
    active = db.Column(db.Boolean, default=True)
    public = db.Column(db.Boolean, default=False)
    official = db.Column(db.Boolean, default=False)
    code = db.Column(db.JSON(),default="{}")
    last_executed = db.Column(db.DateTime)
    run_every = db.Column(db.String(),default="10")
    top = db.Column(db.Integer(),nullable=False)
    left = db.Column(db.Integer(),nullable=False)
    return_path = db.Column(db.String())
    paused_email_to = db.Column(db.String())
    form_id = db.Column(db.Integer, db.ForeignKey('intake_forms.id'))
    inputs = db.relationship('Input', backref='operator', lazy='dynamic')
    outputs = db.relationship('Output', backref='operator', lazy='dynamic')
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflows.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @staticmethod
    def find_by_name(name):
        operator_exists = Operator.query.filter(func.lower(Operator.name) == func.lower(name)).first()
        if operator_exists:
            return operator_exists
        return False

    @staticmethod
    def add(workflow_id,operator_id=None,type="action",label=None,top=1000,left=1000,imports="",documentation="",
        code={},official=False,description="Default Description",add_output=True,subtype=None,**kwargs):
        '''operator_id is the existing operator that we want to clone'''
        if operator_id:
            existing_op = Operator.query.get(operator_id)
            if not existing_op:
                raise ValueError("operator not found")
            else:
                code = existing_op.code
                subtype = existing_op.subtype
                label = "(Copy) {}".format(existing_op.label)
                description = "(Copy) {}".format(existing_op.description)
                imports = existing_op.imports
                documentation = existing_op.documentation
        if not code:
            code = default_op_code()
        name = "Operator_{}".format(generate_uuid(length=10))
        if not label:
            label = name
        operator = Operator(name=name,label=label,type=type,
            code=code,top=top,left=left,workflow_id=workflow_id,
            description=description,official=official,subtype=subtype,
            imports=imports,documentation=documentation,**kwargs)
        db.session.add(operator)
        db.session.commit()

        # add input/output
        if type != "trigger":
            operator.add_input()
        if add_output:
            operator.add_output()
        return operator

    def get_intake_link(self):
        if self.form_id:
            intake = IntakeForm.query.get(self.form_id)
            if intake:
                return "/workflows/{}/intake/{}".format(self.workflow_id,intake.name)
        return None

    def last_executed_humanized(self):
        if not self.last_executed:
            return "never"
        return arrow.get(self.last_executed).humanize()

    def get_label(self):
        '''remove random ID from label b/c it has to be unique per workflow'''
        return "_".join(self.label.split("_")[:-1])

    def get_code(self):
        return "#general imports\n{}\n#operator imports\n{}\n\n{}\n\n{}\n\n{}".format(self.workflow.imports or "",
            self.imports or "",default_store_code(),default_locker_code(),self.code)

    def parse_locker_key_from_input(self,data):
        if "locker" in data:
            try:
                r = data.split("##input")[0].split(",")[-1:][0]
                r = r.replace('"',"")
                r = r.replace("'","")
                r = r.replace(")","")
                return r.strip()
            except:
                pass
        return None

    def generate_form_from_code(self):
        """
        generates HTML form based on comments in the Operator/Link code

        e.g. url = None ##input:type=text:placeholder=enter email:name=email:label=testing
        """
        input_dictionary = {
            "text":"<input value='{}' type='text' class='form-control' {}>",
            "number":"<input value='{}' type='number' class='form-control' {}>",
            "date":"<input value='{}' type='date' class='form-control' data-mask='00/00/0000' data-mask-visible='true' autocomplete='off' {}>",
            "checkbox":"<input type='checkbox' class='form-check-input ml-2' {}>"
        }
        locker = self.workflow.get_default_locker(create=True)
        content = ""
        for line in self.code.split("\n"):
            if line:
                line = line.strip()
                if "##input" in line:
                    locker_attr = self.parse_locker_key_from_input(line)
                    locker_value = locker.config.get(locker_attr,'')
                    available_params = line.split("##input")[-1:]
                    if available_params:
                        param_dict = {}
                        for param in [x.split("=") for x in available_params[0].split(":") if "=" in x]:
                            param_dict[param[0]] = param[1]
                        type = param_dict.get("type")
                        input_type = input_dictionary.get(type)
                        if input_type:
                            param_dict.pop("type",None)
                            input_addons = ""
                            if param_dict:
                                for key,value in param_dict.items():
                                    if key not in ["checked","value"]:
                                        input_addons+="{}='{}' ".format(key,value)
                            if type != "checkbox":
                                input = input_type.format(locker_value,input_addons)
                            else:
                                if locker_value == True:
                                    input_addons+=" checked=true"
                                input = input_type.format(input_addons)
                            content+="<div class='mb-3'><label class='form-label subheader'>{}</label>{}</div>".format(param_dict.get("label","Add Label"),input)
        return content

    def get_html_form_for_code(self):
        custom_html_form = self.generate_form_from_code()
        if not custom_html_form:
            custom_html_form = "There are no custom variables defined!"
        operator_variables_html = """
            <div class="card mb-2">
              <div class="card-header bg-light">
                <h3 class="card-title">Operator Variables</h3>
              </div>
              <div class="card-body" id="{}-vars">
                {}
              </div>
            </div>
        """.format(self.name,custom_html_form)
        return operator_variables_html

    def get_html_form_for_input(self):
        form_html = self.get_additional_input_for_input_trigger()
        operator_input_html = """
            <div class="card mb-2">
              <div class="card-header bg-light">
                <h3 class="card-title">User Input Settings</h3>
              </div>
              <div class="card-body">
                <div class="alert alert-important bg-blue-lt alert-dismissible" role="alert">
                  <div class="d-flex">
                    <div>
                      <i class="ti ti-info-circle icon mr-2"></i>
                    </div>
                    <div>
                      When your workflow is paused on this Operator, optionally set up a UI form to collect user input.
                    </div>
                  </div>
                  <a class="btn-close btn-close-white" data-bs-dismiss="alert" aria-label="close"></a>
                </div>
                {}
                <div class="form-group mb-3 row">
                  <label class="form-label col-3 col-form-label">Send Notification Email</label>
                  <div class="col">
                    <input id="email_{}" type="text" value="{}" class="form-control" placeholder="Comma separated list of email(s)">
                    <small class="form-hint">Specify if we should send a email to someone when the workflow is paused</small>
                  </div>
                </div>
              </div>
            </div>
        """.format(form_html,self.name,self.paused_email_to)
        return operator_input_html

    def get_additional_input_for_api_trigger(self):
        sync_html = ""
        for sync in ["synchronous","asynchronous"]:
            select = ""
            if self.synchronous and sync == "synchronous":
                select = "selected"
            elif not self.synchronous and sync == "asynchronous":
                select = "selected"
            sync_html+='<option value="{}" {}>{}</option>'.format(sync,select,sync)
        template = """
            <div class="form-group mb-3 row">
              <label class="form-label col-3 col-form-label">Synchronous/Async Return</label>
              <div class="col">
                <select id="synchronous_{}" class="form-select">{}</select>
                <small class="form-hint">Synchronous will wait for the return path to complete. Async will provide a callback URL.</small>
              </div>
            </div>""".format(self.name,sync_html)
        return template

    def get_additional_input_for_cron_trigger(self):
        template = """
            <div class="form-group mb-3 row">
              <label class="form-label col-3 col-form-label">Cron Schedule</label>
              <div class="col">
                <input type="number" id="runevery_{}" class="form-control" value="{}" placeholder="Enter minutes">
                <small class="form-hint">Configure how often you want this workflow to execute (in minutes)</small>
              </div>
            </div>""".format(self.name,self.run_every)
        return template

    def get_additional_input_for_form_trigger(self):
        template = """
            <div class="form-group mb-3 row">
              <label class="form-label col-3 col-form-label">Form</label>
              <div class="col">
                <select class="form-select" id="form_{}">
                  <option value="">Select an Form</option>
                  {}
                </select>
                <small class="form-hint">Select which form you want end users to see for your Workflow</small>
              </div>
            </div>
        """
        form_options = ""
        for form in IntakeForm.query.all():
            select = ""
            if self.form_id == form.id:
                select = "selected"
            form_options += '<option value="{}" {}>({}) {}</option>'.format(form.id,select,form.id,form.label)
        template = template.format(self.name,form_options)
        return template

    def get_additional_input_for_input_trigger(self):
        form_options = ""
        template = """
            <div class="form-group mb-3 row">
              <label class="form-label col-3 col-form-label">Select UI Form</label>
              <div class="col">
                <select class="form-select" id="form_{}">
                  <option value="">Select an Form</option>
                  {}
                </select>
                <small class="form-hint">Select which form you want end users to see for your Workflow</small>
              </div>
            </div>
        """
        for form in IntakeForm.query.all():
            select = ""
            if self.form_id == form.id:
                select = "selected"
            form_options += '<option value="{}" {}>({}) {}</option>'.format(form.id,select,form.id,form.label)
        template = template.format(self.name,form_options)
        return template

    def get_return_path_input(self):
        path_items = ""
        for path in self.workflow.path_tree(operator_id=self.id,identify_by="label").get("paths",[]):
            list_item = ""
            for path_name,functions in path.items():
                function_count = len(functions)
                for enum,function in enumerate(functions,1):
                    color = "cyan"
                    name = function["name"]
                    if "__" in name:
                        if name.startswith("Operator"):
                            name = "(O) {}".format(function["name"].split("__")[1])
                        else:
                            name = "(L) {}".format(function["name"].split("__")[1])
                            color = "green"
                    if enum == function_count:
                        color = "red"
                    list_item += "<li class='breadcrumb-item'><span class='badge bg-{}-lt'>{}</span></li>".format(color,name)
            checked = ""
            if self.return_path == path_name:
                checked = "checked"
            template = """
              <label class="form-selectgroup-item flex-fill">
                <input type="radio" name="form-payment" value="{}" class="form-selectgroup-input" {}>
                <div class="form-selectgroup-label d-flex align-items-center p-3">
                  <div class="me-3">
                    <span class="form-selectgroup-check"></span>
                  </div>
                  <div><ol class="breadcrumb breadcrumb-arrows" aria-label="breadcrumbs">{}</ol></div>
                </div>
              </label>
            """.format(path_name,checked,list_item)
            path_items += template
        return_section = """
            <div class="form-group mb-3 row">
              <label class="form-label col-3 col-form-label">Select path for return value</label>
              <div class="col">
                  <div id="path_{}" class="form-selectgroup form-selectgroup-boxes d-flex flex-column">
                    {}
                  </div>
                  <small class="form-hint">Choose a path for the return value</small>
              </div>
            </div>
        """.format(self.name,path_items)
        return return_section

    def form_html(self):
        return_section = ""
        addit_input_template = ""
        operator_variables_html = ""
        checked = ""

        if self.enabled:
            checked = "checked"

        # get custom variables
        operator_variables_html = self.get_html_form_for_code()

        # add input for different triggers
        if self.type == "trigger":
            if self.subtype == "api":
                addit_input_template = self.get_additional_input_for_api_trigger()

            elif self.subtype == "cron":
                addit_input_template = self.get_additional_input_for_cron_trigger()

            elif self.subtype == "form":
                addit_input_template = self.get_additional_input_for_form_trigger()

            return_section = self.get_return_path_input()
        # collect user input
        user_input = ""
        user_input_settings = ""
        if self.subtype == "input":
            user_input_settings = self.get_html_form_for_input()
        docs = ""
        if self.documentation:
            docs = """
            <div class="card mb-2 bg-blue-lt">
              <div class="card-body">
                  <p>Please see documentation <a href="{}">here</a> for configuration details</p>
              </div>
            </div>
            """.format(self.documentation)
        template = """
          {}
          {}
          {}
          <div class="card">
            <div class="card-header bg-light">
              <h3 class="card-title">Settings</h3>
            </div>
            <div class="card-body">
              <form>
                <div class="form-group mb-3 row">
                  <label class="form-label col-3 col-form-label">Name</label>
                  <div class="col">
                    <input type="text" class="form-control" name="example-disabled-input" value="{}" disabled="">
                  </div>
                </div>
                <div class="form-group mb-3 row">
                  <label class="form-label col-3 col-form-label">Label</label>
                  <div class="col">
                    <input type="text" id="label_{}" class="form-control" value="{}" placeholder="Enter Label">
                    <small class="form-hint">Choose a label that is descriptive of the function</small>
                  </div>
                </div>
                <div class="form-group mb-3 row">
                  <label class="form-label col-3 col-form-label">Description</label>
                  <div class="col">
                    <textarea class="form-control" id="description_{}" placeholder="e.g. This function does X and then Y">{}</textarea>
                    <small class="form-hint">Describe the intention of the function</small>
                  </div>
                </div>
                <div class="form-group mb-3 row">
                  <div class="row">
                    <label class="row">
                      <span class="col form-label">Enabled</span>
                      <span class="col-auto">
                        <label class="form-check form-check-single form-switch">
                          <input id="enabled_{}" class="form-check-input cursor-pointer" type="checkbox" {}>
                        </label>
                      </span>
                    </label>
                  </div>
                </div>
                <div class="form-group mb-3 row">
                  <label class="form-label col-3 col-form-label">Additional Module Imports</label>
                  <div class="col">
                    <textarea class="form-control" id="imports_{}" placeholder="import os\nimport math">{}</textarea>
                    <small class="form-hint">You usually don't need this. We automatically add standard imports to your function</small>
                  </div>
                </div>
                {}
                {}
                {}
              </form>
            </div>
          </div>
        """.format(docs,operator_variables_html,user_input_settings,self.name,self.name,
            self.label,self.name,self.description,self.name,checked,
            self.name,self.imports or "",return_section,addit_input_template,user_input)
        return template

    def create_file(self,path,content=""):
        with open(path, 'w') as f:
            f.write(content)
        return True

    def create_code_folder(self,dir):
        self.create_file(os.path.join(dir,"__init__.py"))
        self.create_main_file(dir)
        self.create_outputs_file(dir)
        return True

    def create_main_file(self,dir):
        file_path = os.path.join(dir,"operator.py")
        return self.create_file(file_path,self.get_code())

    def create_outputs_file(self,dir):
        file_path = os.path.join(dir,"links.py")
        code = ""
        links = self.format_links()
        if links:
            for link_name,info in links.items():
                link = OutputLink.find_by_name(link_name)
                if link:
                    code += "{}\n".format(link.get_code())
        return self.create_file(file_path,code)

    def get_imports(self):
        return "import os\n"

    def modal_inputs(self):
        data = ""
        for input in self.inputs.order_by(Input.date_added.desc()).all():
            data += input.modal_html()
        return data

    def modal_outputs(self):
        '''this function is a bit different from modal_inputs above.
        because there is only a single output on each operator, we must
        grab the output links where the code will reside.
        '''
        data = ""
        for output in self.outputs.order_by(Output.date_added.desc()).all():
            data += output.modal_html()
        return data

    def sidebar_html(self):
        input_count = self.inputs.count()
        output_count = self.outputs.count()
        if self.official:
            icon = """<i data-bs-toggle="tooltip" data-bs-placement="top" title="Official Operator" class='ti ti-circle-check icon text-success mr-1'></i>"""
        else:
            icon = """<span class="text-red mr-1"><i data-bs-toggle="tooltip" data-bs-placement="top" title="Shared Operator" class="ti ti-alert-triangle icon"></i></span>"""
        data = """
            <div type="{}" id="operator_{}" style="border-color:transparent" class="blockelem draggable_operator card card-body d-block mb-2" data-nb-inputs="{}" data-nb-outputs="{}">
              <div class="row">
                <div class="col-2 mt-3">
                  <i class="ti ti-grip-vertical icon"></i>
                </div>
                <div class="col-10">
                  <h4>{}{}</h4>
                  <div class="subheader">{}</div>
                </div>
              </div>
            </div>
        """.format(self.type,self.id,input_count,output_count,icon,
            self.label.capitalize(),self.description.capitalize())
        return data

    def to_json(self):
        template = {
            "top":self.top,
            "left":self.left,
            "properties":self.properties()["properties"],
        }
        return template

    def template(self):
        return {"operator_id":self.name,"properties":self.properties()["properties"]}

    def properties(self):
        icon = "git-merge"
        if self.type == "trigger":
            icon = "urgent"
        elif self.type == "misc":
            icon = "tool"
        active = '<span class="badge bg-green-lt">active</span>'
        if not self.enabled:
            active = '<span class="badge bg-red-lt">inactive</span>'
        template = {
            "properties": {
              "name":self.name,
              "label":self.label,
              "type":self.type,
              "title": '''<div class="row justify-content-between">
                  <div class="col"><h4>{}</h4></div><div class="col text-end"><i class="ti ti-{} icon"></i></div></div>'''.format(self.label,icon),
              "footer": '''<div class="subheader ignore-op-click card-footer"><div class="row"><div class="col-10 ignore-op-click">{}</div>
                  <div class="col-2 ignore-op-click text-end"><div class="nav-item dropdown">
                  <a href="#" class="p-0 ml-2 ignore-op-click" data-bs-toggle="dropdown" aria-label="Open operator menu" aria-expanded="false">
                  <i class="ti ti-dots-vertical icon"></i></a><div class="dropdown-menu dropdown-menu-end dropdown-menu-arrow bg-dark text-white" data-bs-popper="none">
                  <span class="dropdown-header">Quick Actions</span><a href="#" id="{}" class="dropdown-item h6 edit_operator">
                  <i class="ti ti-code mr-2"></i>Edit</a><a href="#" id="{}" class="dropdown-item h6 delete_operator ignore-op-click">
                  <i class="ti ti-trash mr-2"></i>Delete</a></div></div></div></div>'''.format(active,self.name,self.name),
            }
        }
        template["properties"]["inputs"] = self.format_inputs()["inputs"]
        template["properties"]["outputs"] = self.format_outputs()["outputs"]
        return template

    def format_inputs(self):
        data = {"inputs":{}}
        for input in self.inputs.all():
            data["inputs"][input.name] = input.to_json()
        return data

    def format_outputs(self):
        data = {"outputs":{}}
        for output in self.outputs.all():
            data["outputs"][output.name] = output.to_json()
        return data

    def format_links(self):
        links = {}
        for output in self.outputs.all():
            links = {**links,**output.get_links()}
        return links

    def add_input(self):
        name = "Input_{}".format(generate_uuid(length=10))
        input = Input(name=name,label=name)
        self.inputs.append(input)
        db.session.commit()
        return input

    def remove_input_by_name(self,name):
        input = self.inputs.filter(Input.name == name).first()
        if input:
            input.remove_all_links()
            db.session.delete(input)
            db.session.commit()
        return True

    def remove_input_by_id(self,name):
        input = self.inputs.filter(Input.id == id).first()
        if input:
            input.remove_all_links()
            db.session.delete(input)
            db.session.commit()
        return True

    def add_output(self):
        name = "Output_{}".format(generate_uuid(length=10))
        output = Output(name=name,label=name)
        self.outputs.append(output)
        db.session.commit()
        return output

    def remove_output_by_name(self,name):
        output = self.outputs.filter(Output.name == name).first()
        if output:
            output.remove_all_links()
            db.session.delete(output)
            db.session.commit()
        return True

    def remove_output_by_id(self,id):
        output = self.outputs.filter(Output.id == id).first()
        if output:
            output.remove_all_links()
            db.session.delete(output)
            db.session.commit()
        return True

    def add_link(self,to_operator_name,from_output_name,to_input_name):
        '''
          "link_1": {
            "fromOperator": 'operator1',
            "fromConnector": 'output_1',
            "toOperator": 'operator2',
            "toConnector": 'input_1',
          },
        '''
        operator = Operator.find_by_name(to_operator_name)
        if not operator:
            raise ValueError("Operator does not exist")

        if operator == self.operator:
            raise ValueError("Input/Output link must be on different operators")

        input = Input.find_by_name(to_input_name)
        if not input:
            raise ValueError("Input does not exist")

        output = Output.find_by_name(from_output_name)
        if not output:
            raise ValueError("Output does not exist")

        if self.does_link_exist(input.id):
            raise ValueError("Link already exists")

        name = "Link_{}".format(generate_uuid(length=10))
        link = OutputLink(name=name,output_id=self.id,
            input_id=to_input_name,code=default_link_code(name))
        db.session.add(link)
        db.session.commit()
        return {
            "link_id":link.name,
            "link_data":{
                "fromOperator": self.operator.name,
                "fromConnector": output.name,
                "toOperator": operator.name,
                "toConnector": input.name,
            }
        }

    def remove(self):
        for output in self.outputs.all():
            output.remove()
        for input in self.inputs.all():
            input.remove()
        db.session.delete(self)
        db.session.commit()
        return True

class Input(db.Model, LogMixin):
    __tablename__ = 'inputs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    label = db.Column(db.String())
    multiple = db.Column(db.Boolean, default=False)
    outputs = db.relationship('Output', secondary='output_links', backref="input", lazy='dynamic')
    operator_id = db.Column(db.Integer, db.ForeignKey('operators.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def remove(self):
        for link in OutputLink.query.filter(OutputLink.input_id == self.id).all():
            link.remove()
        db.session.delete(self)
        db.session.commit()
        return True

    def to_json(self):
        return {"label":self.label,"multiple":self.multiple}

    @staticmethod
    def find_by_name(name):
        input_exists = Input.query.filter(func.lower(Input.name) == func.lower(name)).first()
        if input_exists:
            return input_exists
        return False

    def form_html(self):
        template = """
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">Input Settings</h3>
            </div>
            <div class="card-body">
              <form>
                <div class="form-group mb-3">
                  <label class="form-label">Email address</label>
                  <div>
                    <input type="email" class="form-control" aria-describedby="emailHelp" placeholder="Enter email">
                    <small class="form-hint">We'll never share your email with anyone else.</small>
                  </div>
                </div>
                <div class="form-group mb-3 ">
                  <label class="form-label">Password</label>
                  <div>
                    <input type="password" class="form-control" placeholder="Password">
                    <small class="form-hint">
                      Your password must be 8-20 characters long, contain letters and numbers, and must not contain
                      spaces, special characters, or emoji.
                    </small>
                  </div>
                </div>
                <div class="form-group mb-3 ">
                  <label class="form-label">Select</label>
                  <div>
                    <select class="form-select">
                      <option>Option 1</option>
                    </select>
                  </div>
                </div>
                <div class="form-footer">
                  <button type="submit" class="btn btn-primary">Submit</button>
                </div>
              </form>
            </div>
          </div>
        """
        return template

    def modal_html(self):
        connected_count = OutputLink.query.filter(OutputLink.input_id == self.id).count()
        template = """
          <div style="border-color:transparent" class="blockelem-hover card card-body d-block">
            <div class="row">
              <div class="col-9 mt-2">
                <h5 class="text-secondary inputHeader">{}</h5>
              </div>
              <div class="col-3">
                <span class="avatar avatar-sm avatar-rounded bg-green-lt">C</span>
              </div>
            </div>
            <p style="font-size:10px" class="text-muted mb-0"><span class="text-green font-weight-bold">{} Operator(s) connected</span></p>
          </div>
          <div class="hr-text mb-3 mt-3"><i class="ti ti-activity"></i></div>
        """.format(self.operator.label,connected_count)
        return template

    def remove_all_links(self):
        links = OutputLink.query.filter(OutputLink.input_id == self.id).all()
        for link in links:
            db.session.delete(link)
            db.session.commit()
        return True

class Output(db.Model, LogMixin):
    __tablename__ = 'outputs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    label = db.Column(db.String())
    multiple = db.Column(db.Boolean, default=False)
    inputs = db.relationship('Input', secondary='output_links', backref="output", lazy='dynamic')
    operator_id = db.Column(db.Integer, db.ForeignKey('operators.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def remove(self):
        for link in OutputLink.query.filter(OutputLink.output_id == self.id).all():
            link.remove()
        db.session.delete(self)
        db.session.commit()
        return True

    def to_json(self):
        return {"label":self.label,"multiple":self.multiple}

    @staticmethod
    def find_by_name(name):
        output_exists = Output.query.filter(func.lower(Output.name) == func.lower(name)).first()
        if output_exists:
            return output_exists
        return False

    def modal_html(self):
        data = ""
        for connector in OutputLink.query.filter(OutputLink.output_id == self.id).order_by(OutputLink.id.desc()).all():
            template = """
              <div id="{}_link" style="border-color:transparent" class="blockelem-hover card card-body d-block modalOutputSidebar">
                <div class="row">
                  <div class="col-8">
                    <h5 id="{}_linkHeader" class="text-secondary outputHeader mt-1">{}</h5>
                  </div>
                  <div class="col-2">
                    <a href="#" onclick="clickLinkOutputCode('{}')"><i id="{}_linkCodeIcon" class="ti ti-code icon text-secondary outputCodeIcon"></i></a>
                  </div>
                  <div class="col-2">
                    <a href="#" onclick="clickLinkOutputSettings('{}')"><i id="{}_linkSettingsIcon" class="ti ti-tools icon text-secondary outputSettingsIcon"></i></a>
                  </div>
                </div>
                <p style="font-size:10px" class="text-muted mb-0">Connected to <span class="text-green font-weight-bold">{}</span></p>
              </div>
              <div class="hr-text mb-3 mt-3"><i class="ti ti-activity"></i></div>
            """.format(connector.name,connector.name,connector.label or connector.name,
                connector.name,connector.name,connector.name,connector.name,connector.input().operator.label)
            data += template
        return data

    def remove_all_links(self):
        links = OutputLink.query.filter(OutputLink.output_id == self.id).all()
        for link in links:
            db.session.delete(link)
            db.session.commit()
        return True

    def does_link_exist(self,input_id):
        return OutputLink.query.filter(OutputLink.input_id == input_id).filter(OutputLink.output_id == self.id).first()

    def get_links(self):
        '''get all connections for the outputs'''
        links = {}
        for connector in OutputLink.query.filter(OutputLink.output_id == self.id).all():
            input = connector.input()
            links[connector.name] = {
                "fromOperator": self.operator.name,
                "fromConnector": self.name,
                "toOperator": input.operator.name,
                "toConnector": input.name,
                "toOperatorLabel":input.operator.label,
                "fromOperatorLabel":self.operator.label,
                "connectorLabel":connector.label
            }
        return links

    def get_links_ex(self):
        '''get all connections for the outputs'''
        links = []
        for connector in OutputLink.query.filter(OutputLink.output_id == self.id).order_by(OutputLink.id.desc()).all():
            input = connector.input()
            links.append({
                "linkName":connector.name,
                "fromOperator": self.operator.name,
                "fromConnector": self.name,
                "toOperator": input.operator.name,
                "toConnector": input.name,
                "toOperatorLabel":input.operator.label,
                "fromOperatorLabel":self.operator.label,
            })
        return links

    def add_link(self,to_operator_name,to_input_name):
        '''
          "link_1": {
            "fromOperator": 'operator1',
            "fromConnector": 'output_1',
            "toOperator": 'operator2',
            "toConnector": 'input_1',
          },
        '''
        operator = Operator.find_by_name(to_operator_name)
        if not operator:
            raise ValueError("Operator does not exist")

        if operator.id == self.operator_id:
            raise ValueError("Input/Output link must be on different operators")

        input = Input.find_by_name(to_input_name)
        if not input:
            raise ValueError("Input does not exist")

        if self.does_link_exist(input.id):
            raise ValueError("Link already exists")

        name = "Link_{}".format(generate_uuid(length=10))
        link = OutputLink(name=name,output_id=self.id,
            input_id=input.id,code=default_link_code(name))
        db.session.add(link)
        db.session.commit()
        return {
            "link_id":link.name,
            "link_data":{
                "fromOperator": self.operator.name,
                "fromConnector": self.name,
                "toOperator": operator.name,
                "toConnector": input.name,
            }
        }

    def remove_link(self,input_id):
        link_exists = self.does_link_exist(input_id)
        if link_exists:
            db.session.delete(link_exists)
            db.session.commit()
        return

class OutputLink(LogMixin,db.Model):
    __tablename__ = 'output_links'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String())
    label = db.Column(db.String(),default="Default Label")
    description = db.Column(db.String())
    imports = db.Column(db.String())
    enabled = db.Column(db.Boolean, default=True)
    code = db.Column(db.JSON(),default="{}")
    output_id = db.Column(db.Integer(), db.ForeignKey('outputs.id', ondelete='CASCADE'),nullable=False)
    input_id = db.Column(db.Integer(), db.ForeignKey('inputs.id', ondelete='CASCADE'),nullable=False)

    def remove(self):
        db.session.delete(self)
        db.session.commit()
        return True

    def get_code(self):
        return "#general imports\n{}\n#operator imports\n{}\n\n{}\n\n{}\n\n{}".format(self.output().operator.workflow.imports or "",
            self.imports or "",default_store_code(),default_locker_code(),self.code)

    def get_output_operator(self):
        output = Output.query.get(self.output_id)
        if not output:
            return "None"
        return output.operator

    def get_input_operator_name(self):
        input = Input.query.get(self.input_id)
        if not input:
            return "None"
        return input.operator.name

    def get_input_connector_name(self):
        input = Input.query.get(self.input_id)
        if not input:
            return "None"
        return input.name

    @staticmethod
    def find_by_name(name):
        link_exists = OutputLink.query.filter(func.lower(OutputLink.name) == func.lower(name)).first()
        if link_exists:
            return link_exists
        return False

    def input(self):
        return Input.query.get(self.input_id)

    def output(self):
        return Output.query.get(self.output_id)

    def form_html(self):
        checked = ""
        if self.enabled:
            checked = "checked"
        template = """
          <div class="card">
            <div class="card-header bg-light">
              <h3 class="card-title">Link Settings</h3>
            </div>
            <div class="card-body">
              <form>
                <div class="form-group mb-3 row">
                  <label class="form-label col-3 col-form-label">Name</label>
                  <div class="col">
                    <input type="text" class="form-control" name="example-disabled-input" value="{}" disabled="">
                  </div>
                </div>
                <div class="form-group mb-3 row">
                  <label class="form-label col-3 col-form-label">Label</label>
                  <div class="col">
                    <input type="text" id="label_{}" class="form-control" value="{}" placeholder="Enter Label">
                    <small class="form-hint">Choose a label that is descriptive of the function</small>
                  </div>
                </div>
                <div class="form-group mb-3 row">
                  <label class="form-label col-3 col-form-label">Description</label>
                  <div class="col">
                    <textarea class="form-control" id="description_{}" placeholder="e.g. This function does X and then Y">{}</textarea>
                    <small class="form-hint">Describe the intention of the function</small>
                  </div>
                </div>
                <div class="form-group mb-3 row">
                  <div class="row">
                    <label class="row">
                      <span class="col form-label">Enabled</span>
                      <span class="col-auto">
                        <label class="form-check form-check-single form-switch">
                          <input id="enabled_{}" class="form-check-input cursor-pointer" type="checkbox" {}>
                        </label>
                      </span>
                    </label>
                  </div>
                </div>
                <div class="form-group mb-3 row">
                  <label class="form-label col-3 col-form-label">Additional Module Imports</label>
                  <div class="col">
                    <textarea class="form-control" id="imports_{}" placeholder="import os\nimport math">{}</textarea>
                    <small class="form-hint">You usually don't need this. We automatically add standard imports to your function</small>
                  </div>
                </div>
              </form>
            </div>
          </div>
        """.format(self.name,self.name,self.label,self.name,self.description,
            self.name,checked,self.name,self.imports or "")
        return template

class AssocTag(LogMixin,db.Model):
    __tablename__ = 'assoc_tags'
    id = db.Column(db.Integer(), primary_key=True)
    tag_id = db.Column(db.Integer(), db.ForeignKey('tags.id', ondelete='CASCADE'))
    operator_id = db.Column(db.Integer(), db.ForeignKey('operators.id', ondelete='CASCADE'))

class Tag(LogMixin,db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), unique=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class WorkflowUser(LogMixin,db.Model):
    __tablename__ = 'workflow_user'
    id = db.Column(db.Integer(), primary_key=True)
    workflow_id = db.Column(db.Integer(), db.ForeignKey('workflows.id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    permission = db.Column(db.Integer(), nullable=False) #1 = Read-only, 2 = RW

    def user(self):
        return User.query.get(self.user_id)

class User(LogMixin,db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean(), nullable=False, server_default='1')
    email = db.Column(db.String(255), nullable=False, unique=True)
    username = db.Column(db.String(100), unique=True)
    email_confirmed_at = db.Column(db.DateTime())
    password = db.Column(db.String(255), nullable=False, server_default='')
    last_password_change = db.Column(db.DateTime())
    first_name = db.Column(db.String(100), nullable=False, server_default='')
    last_name = db.Column(db.String(100), nullable=False, server_default='')
    roles = db.relationship('Role', secondary='user_roles')
    workflows = db.relationship('Workflow', secondary='workflow_user',lazy='dynamic')
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            current_app.logger.warning("SignatureExpired for token")
            return None # valid token, but expired
        except BadSignature:
            current_app.logger.warning("BadSignature for token")
            return None # invalid token
        user = User.query.get(data['id'])
        return user

    def generate_auth_token(self, expiration = 6000):
        s = Serializer(current_app.config['SECRET_KEY'], expires_in = expiration)
        return s.dumps({ 'id': self.id })

    @staticmethod
    def verify_invite_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            current_app.logger.warning("SignatureExpired for token")
            return None # valid token, but expired
        except BadSignature:
            current_app.logger.warning("BadSignature for token")
            return None # invalid token
        return data["email"]

    @staticmethod
    def generate_invite_token(email,expiration = 600):
        s = Serializer(current_app.config['SECRET_KEY'], expires_in = expiration)
        return s.dumps({ 'email': email }).decode('utf-8')

    def has_locker(self,id):
        return LockerAccess.query.filter(LockerAccess.locker_id == id).filter(LockerAccess.user_id == self.id).first()

    def pretty_roles(self):
        data = []
        for role in self.roles:
            data.append(role.name.lower())
        return data

    def can_edit_roles(self):
        return "admin" in self.pretty_roles()

    def has_role(self,roles):
        '''checks if user has any of the listed roles'''
        if not roles:
            return False
        if not isinstance(roles,list) and not isinstance(roles,tuple):
            roles = [roles]
        my_roles = self.pretty_roles()
        for role in roles:
            if role.lower() in my_roles:
                return True
        return False

    def has_roles(self,roles):
        '''checks if user has all of the listed roles'''
        if not roles:
            return False
        if not isinstance(roles,list) and not isinstance(roles,tuple):
            roles = [roles]
        my_roles = self.pretty_roles()
        for role in roles:
            if role.lower() not in my_roles:
                return False
        return True

    def set_roles_by_name(self,roles):
        #roles = ["Admin","Another Role"]
        if not isinstance(roles,list):
            roles = [roles]
        new_roles = []
        for role in roles:
            found = Role.find_by_name(role)
            if found:
                new_roles.append(found)
        self.roles[:] = new_roles
        db.session.commit()
        return True

    def get_roles_for_form(self):
        roles = {}
        for role in Role.query.all():
            if role in self.roles:
                roles[role] = True
            else:
                roles[role] = False
        return roles

    def is_privileged(self):
        if self.has_role(["admin"]):
            return True
        return False

    def set_password(self, password):
        self.password = generate_password_hash(password, method='sha256')
        self.last_password_change = str(datetime.utcnow())

    def check_password(self, password):
        return check_password_hash(self.password, password)

# Define the Role data-model
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)

    @staticmethod
    def find_by_name(name):
        role_exists = Role.query.filter(func.lower(Role.name) == func.lower(name)).first()
        if role_exists:
            return role_exists
        return False

# Define the UserRoles association table
class UserRoles(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))

class UserInvitation(db.Model):
    __tablename__ = 'user_invitations'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    invited_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

class ConfigStore(db.Model,LogMixin):
    __tablename__ = 'config_store'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    name = db.Column(db.String(),nullable=False)
    object_store = db.Column(db.JSON(),default={})
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @staticmethod
    def find_by_name(name):
        store_exists = ConfigStore.query.filter(func.lower(ConfigStore.name) == func.lower(name)).first()
        if store_exists:
            return store_exists
        return False

    def get(self,key):
        '''ConfigStore.get("mykey")'''
        return self.object_store.get(key.lower())

    def insert(self,object):
        '''ConfigStore.insert({"mykey":"myvalue"})'''
        if not isinstance(object,dict):
            return False,"Object must be a dictionary"
        temp = {**{},**self.object_store}
        for key,value in object.items():
            key = key.lower()
            temp[key] = value
        self.object_store = temp
        db.session.commit()
        return True

class Logs(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    namespace = db.Column(db.String(),nullable=False,default="general")
    log_type = db.Column(db.String(),nullable=False,default="info")
    message = db.Column(db.String(),nullable=False)
    meta = db.Column(db.JSON(),default="[]")
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @staticmethod
    def add_log(message,log_type="info",namespace="general",meta={}):
        if log_type.lower() not in ["info","warning","error","critical"]:
            return False
        msg = Logs(namespace=namespace.lower(),message=message,
            log_type=log_type.lower(),meta=meta)
        db.session.add(msg)
        db.session.commit()
        return True

    @staticmethod
    def get_logs(log_type=None,limit=100,as_query=False,span=None,as_count=False,paginate=False,page=1,namespace="general",meta={}):
        '''
        get_logs(log_type='error',namespace="my_namespace",meta={"key":"value":"key2":"value2"})
        '''
        _query = Logs.query.filter(Logs.namespace == namespace.lower()).order_by(Logs.id.desc())
        if log_type:
            if not isinstance(log_type,list):
                log_type = [log_type]
            _query = _query.filter(Logs.log_type.in_(log_type))

        if meta:
            for key,value in meta.items():
                _query = _query.filter(Logs.meta.op('->>')(key) == value)
        if span:
            _query = _query.filter(Logs.date_added >= arrow.utcnow().shift(hours=-span).datetime)
        if as_query:
            return _query
        if as_count:
            return _query.count()
        if paginate:
            return _query.paginate(page=page, per_page=10)
        return _query.limit(limit).all()

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
