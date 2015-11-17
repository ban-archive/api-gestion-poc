# BAN

This is a POC of API for managing the future "Base adresses nationale".

## Install
Make sure you have python >= 3.4 installed.

Create a virtualenv (but you'd better use virtualenvwrapper or pew):

    virtualenv banenv --python=`which python3.4`
    source banenv/bin/activate

Create a psql database

    sudo -u postgres createdb ban -O youruser

Add postgis and hstore extensions

    psql ban
    CREATE EXTENSION postgis;
    CREATE EXTENSION hstore;

Clone repository

    git clone https://github.com/etalab/ban
    cd ban/

Install psycopg2 dependencies

    sudo apt-get build-dep python-psycopg2
    
Install python dependencies

    pip install -r requirements.txt

Install ban locally

    python setup.py develop

## Data setup

Create tables

    ban db:create

Create at least use staff user

    ban auth:createuser

Import municipalities (get the file from
http://www.collectivites-locales.gouv.fr/files/files/epcicom2015.csv)

    ban import:municipalities epcicom2015.csv --departement 33

Import some adresses (get data from http://bano.openstreetmap.fr/BAN_odbl/)

    ban import:oldban BAN_odbl_33-json

## Run the server

For development:

    ban server:run

For production, you need to use either gunicorn or uwsgi.

## Windows install
- download and install python 3.5 from https://www.python.org/downloads/
- download and install git from https://git-scm.com/download/win
- download and install postgresql from http://fr.enterprisedb.com/products-services-training/pgdownload
- launch git-bash
- clone ban project with git clone
