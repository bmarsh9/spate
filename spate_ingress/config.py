import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    APP_NAME = "Spate"
    APP_SUBTITLE = "Workflow made easy"
    CR_YEAR = "2021"

    LOG_TYPE = os.environ.get("LOG_TYPE", "stream")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING")

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'newllkjlreagjeraihgeorvhlkenvol3u4og98u4g893u4g0u3409u34add'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    BASE_DIR = basedir

    SQLALCHEMY_DATABASE_URL = os.environ.get("SQLALCHEMY_DATABASE_URL","postgresql://db12:db12@10.0.10.171/db12")
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


