import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    APP_NAME = os.environ.get("APP_NAME","Spate Ingress")
    APP_SUBTITLE = os.environ.get("APP_SUBTITLE","Workflows made easy")
    CR_YEAR = os.environ.get("CR_YEAR","2021")
    VERSION = os.environ.get("VERSION","1.0.0")

    LOG_TYPE = os.environ.get("LOG_TYPE", "stream")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING")

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'newllkjlreagjeraihgeorvhlkenvol3u4og98u4g893u4g0u3409u34add'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    BASE_DIR = basedir

    SQLALCHEMY_DATABASE_URL = os.environ.get("SQLALCHEMY_DATABASE_URL","postgresql://db1:db1@postgres_db/db1")
    SHARED_TOKEN = os.environ.get("SHARED_TOKEN","changeme")

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


