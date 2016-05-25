#!/bin/bash
set -e

# Create user and database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE USER ban;
    ALTER USER ban WITH ENCRYPTED PASSWORD 'ban';
    CREATE DATABASE ban;
    GRANT ALL PRIVILEGES ON DATABASE ban TO ban;
EOSQL

# Install hstore extension
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -d ban <<-EOSQL
    CREATE EXTENSION postgis;
    CREATE EXTENSION hstore;
EOSQL
