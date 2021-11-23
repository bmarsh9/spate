#!/bin/bash

/bin/bash ./server_config/setup_db.sh db1
python3 manage.py init_db
#python3 manage.py runserver -h 0.0.0.0

#uwsgi
uwsgi --ini start.ini

