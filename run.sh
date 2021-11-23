#!/bin/bash

if [ "$SETUP_DB" == "yes" ]; then
  /bin/bash ./server_config/setup_db.sh db1
  python3 manage.py init_db
fi

#uwsgi
uwsgi --ini start.ini

