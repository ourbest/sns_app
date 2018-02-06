#!/usr/bin/env bash

mkdir -p logs

python manage.py collectstatic --no-input
python manage.py migrate


python manage.py runserver 0.0.0.0:8001 &

gunicorn -k gevent -t 600 -w 4 -b 0.0.0.0:8000 --access-logfile logs/access.log sns_app.wsgi:application
