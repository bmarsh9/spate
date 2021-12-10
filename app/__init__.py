from flask import Flask,request,render_template,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from app.utils.flask_logs import LogSetup
from config import config
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_babel import Babel, lazy_gettext as _l

db = SQLAlchemy()
logs = LogSetup()
babel = Babel()
migrate = Migrate()
mail = Mail()
login = LoginManager()
login.login_view = 'auth.login'

def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    configure_models(app)
    registering_blueprints(app)
    configure_extensions(app)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("layouts/errors/404.html"),404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("layouts/errors/500.html"),500

    @app.errorhandler(401)
    def unauthorized(e):
        if 'Authorization' in request.headers:
            return jsonify({"message":"unauthorized"}),401
        return "bad"

    @app.errorhandler(400)
    def malformed(e):
        if 'Authorization' in request.headers:
            return jsonify({"message":"malformed request"}),400
        return "bad"

    @app.errorhandler(403)
    def forbidden(e):
        if 'Authorization' in request.headers:
            return jsonify({"message":"forbidden"}),403
        return "bad"

    '''
    @app.before_request
    def before_request():
        pass
    '''

    return app

def configure_models(app):
    # Add all models
    all_models = {}
    classes, models, table_names = [], [], []
    for clazz in db.Model._decl_class_registry.values():
        try:
            table_names.append(clazz.__tablename__)
            classes.append(clazz)
        except:
            pass
    for table in db.metadata.tables.items():
        if table[0] in table_names:
            all_models[table[0]] = classes[table_names.index(table[0])]
            models.append(classes[table_names.index(table[0])])
    app.models = all_models
    return

def configure_extensions(app):
    db.init_app(app)
    logs.init_app(app)
    migrate.init_app(app, db)
    babel.init_app(app)
    login.init_app(app)
    return

def registering_blueprints(app):
    from app.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from app.api_v1 import api as api_v1_blueprint
    app.register_blueprint(api_v1_blueprint, url_prefix='/api/v1')

    from app.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    return
