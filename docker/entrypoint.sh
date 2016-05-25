#!/bin/bash
wait-for-it -t 0 ${DB_HOST:-db}:${DB_PORT:-5432} -- "$@"
