#!/usr/bin/env bash

mkdir -p logs

python manage.py collectstatic --no-input
python manage.py migrate

gunicorn -k gevent -t 600 -w 2 -b 0.0.0.0:8000 --access-logfile logs/access.log sns_app.wsgi:application
