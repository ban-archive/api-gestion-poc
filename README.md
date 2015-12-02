[![Build Status](https://travis-ci.org/etalab/ban.svg)](https://travis-ci.org/etalab/ban)

# BAN

This is a POC of API for managing the future "Base adresses nationale".

## Install
### Linux

Install system dependencies

    sudo apt-get build-dep python-psycopg2
    sudo apt-get install python3.4 python3.4-dev python-virtualenv postgresql-9.4 postgis

Create a virtualenv (but you'd better use virtualenvwrapper or pew):

    virtualenv banenv --python=`which python3.4`
    source banenv/bin/activate
    
Install developpement tools
    
    pip install ipython ipdb


Create a psql database

    sudo -u postgres createdb ban -O youruser

Add postgis and hstore extensions

    psql ban
    CREATE EXTENSION postgis;
    CREATE EXTENSION hstore;

### Windows

Install system dependencies

- download and install python 3.4 from https://www.python.org/downloads/release/python-343/
- download and install git from https://git-scm.com/download/win
- download and install postgresql from http://fr.enterprisedb.com/products-services-training/pgdownload
- download and install postgreGIS from http://postgis.net/windows_downloads/

-Configure your environment variables:
    setx path "%PATH%;C:\New Folder" (user variable)
or  set path "%PATH%;C:\New Folder" (system variable)

Create a virtualenv

    pip install virtualenv
    virtualenv banenv
    banenv/Scripts/activate.bat

Install developpement tools
    
    pip install ipython pyreadline ipdb

Create a psql database

    createdb -U youruser ban 

Add postgis and hstore extensions

    psql ban youruser
    CREATE EXTENSION postgis;
    CREATE EXTENSION hstore;


## Project configuration

Clone repository

    git clone https://github.com/etalab/ban
    cd ban/

Install python dependencies

    pip install -r requirements.txt

Install ban locally

    python setup.py develop


## Data setup

Create tables

    ban db:create

Create at least use staff user

    ban auth:createuser --is-staff

Import municipalities (get the file from
http://www.collectivites-locales.gouv.fr/files/files/epcicom2015.csv)

    ban import:municipalities epcicom2015.csv --departement 33

Import some adresses (get data from http://bano.openstreetmap.fr/BAN_odbl/)

    ban import:oldban BAN_odbl_33-json

## Run the server

For development:

    ban server:run

For production, you need to use either gunicorn or uwsgi.

Load the API root to get the available endpoints:

    http http://localhost:5959/
