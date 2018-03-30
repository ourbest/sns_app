#!/usr/bin/env bash

mkdir -p logs

if [ "$RQWORKER" = "1"  -o "$1" = "worker" ]
then
    exec ./worker.sh
    exit 0
fi

if [ "$1" = "scheduler" ]
    python manage.py rq-scheduler
    exit 0
then

if [ "$WORKERS" = "" ]
then
    WORKERS=4
fi

python manage.py collectstatic --no-input
#python manage.py migrate


#python manage.py runserver 0.0.0.0:8001 &

gunicorn -k gevent -t 600 -w $WORKERS -b 0.0.0.0:8000 --access-logfile logs/access.log sns_app.wsgi:application
