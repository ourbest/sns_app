#!/usr/bin/env bash

mkdir -p logs

if [ "$RQWORKER" = "1"  -o "$1" = "worker" ]
then
    exec ./worker.sh
    exit 0
fi

if [ "$1" = "scheduler" ]
then
    python manage.py rqscheduler
    exit 0
fi

if [ "$WORKERS" = "" ]
then
    WORKERS=4
fi

python manage.py collectstatic --no-input
#python manage.py migrate


#python manage.py runserver 0.0.0.0:8001 &

gunicorn -k gevent -t 120 -w $WORKERS -b 0.0.0.0:8000 --access-logfile /dev/null sns_app.wsgi:application
