from flask import Flask,request,render_template,jsonify
from config import config
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
import sqlalchemy
import docker

db = automap_base()

def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    registering_blueprints(app)
    configure_extensions(app)

    db_engine = sqlalchemy.create_engine(app.config["SQLALCHEMY_DATABASE_URL"])
    db.prepare(db_engine,reflect=True)
    app.db_session = Session(db_engine)

    app.Workflow = getattr(db.classes,"workflows")
    app.Operator = getattr(db.classes,"operators")
    app.Execution = getattr(db.classes,"executions")
    app.Path = getattr(db.classes,"paths")
    app.Step = getattr(db.classes,"steps")
    app.IntakeForm = getattr(db.classes,"intake_forms")

    app.docker_client = docker.from_env()

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"message":"resource does not exist"}),404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"message":"error"}),500

    return app

def configure_extensions(app):
    return

def registering_blueprints(app):
    from app.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from app.api_v1 import api as api_v1_blueprint
    app.register_blueprint(api_v1_blueprint, url_prefix='/api/v1')
    return
