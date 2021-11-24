#!/usr/bin/env bash

#################### Setup postgres ####################
#psql -h localhost -d $DATABASE -U $USER

sudo su postgres <<EOF
psql -c "CREATE USER $USER WITH PASSWORD '$PASSWORD';"
psql -c "ALTER USER $USER superuser;"
createdb -O$USER -Eutf8 $DATABASE
echo "Postgres user and database created."
EOF

#################### Start postgres ####################
/usr/lib/postgresql/12/bin/postgres -D /var/lib/postgresql/12/main -c config_file=/etc/postgresql/12/main/postgresql.conf
