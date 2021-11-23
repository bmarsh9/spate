import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    #SERVER_NAME = "localhost"
    APP_NAME = os.environ.get("APP_NAME","Spate")
    APP_SUBTITLE = os.environ.get("APP_SUBTITLE","Workflows made easy")
    CR_YEAR = os.environ.get("CR_YEAR","2021")
    VERSION = os.environ.get("VERSION","1.0.0")

    LOG_TYPE = os.environ.get("LOG_TYPE", "stream")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING")

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'newllkjlreagjeraihgeorvhlkenvol3u4og98u4g893u4g0u3409u34add'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    BASE_DIR = basedir
    ENABLE_SELF_REGISTRATION = False
    DOC_LINK = "/"

    RESTRICTED_FIELDS = ["password_hash"]

    DEFAULT_EMAIL = os.environ.get("DEFAULT_EMAIL", "admin@example.com")
    DEFAULT_PASSWORD = os.environ.get("DEFAULT_PASSWORD", "admin")

    WORKFLOW_MOUNT_DIRECTORY = os.environ.get("WORKFLOW_MOUNT_DIRECTORY",os.path.join(basedir,"app","workflow_executions"))
    if not os.path.exists(WORKFLOW_MOUNT_DIRECTORY):
        os.mkdir(WORKFLOW_MOUNT_DIRECTORY)

    # network that hosts the postgres_db container (used for local dev)
    POSTGRES_NW = "spate_db_nw"
    LOCAL_DB = True
    BASE_PYTHON_IMAGE = "base-python"

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URL') or \
        "postgresql://db1:db1@postgres_db/db1"

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URL') or \
        "postgresql://db1:db1@postgres_db/db1"
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
