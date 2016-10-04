#!/bin/bash
# This all-in-one script automatically perform the following task:
# - database initialization
# - load data for a given "departement"
# - run the develoment server
# set -e

ban db:create
ban auth:createuser --is-staff

curl -O http://www.collectivites-locales.gouv.fr/files/files/epcicom2015.csv
ban import:municipalities epcicom2015.csv --departement $DEPARTEMENT

curl -SL http://bano.openstreetmap.fr/BAN_odbl/BAN_odbl_${DEPARTEMENT}-json.bz2 | bunzip2 > BAN_odbl_${DEPARTEMENT}.json
ban import:oldban BAN_odbl_${DEPARTEMENT}.json

ban server:run
