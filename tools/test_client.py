from app import create_app
from app.models import *
import os,time
import json

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

def test():
    with app.app_context():
        pass
