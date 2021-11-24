#!/bin/bash

if [ "$SETUP_DB" == "yes" ]; then
  #/bin/bash ./server_config/setup_db.sh $POSTGRES_DB
  python3 manage.py init_db
fi

#uwsgi
uwsgi --ini start.ini

