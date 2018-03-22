#!/bin/sh

if [ "$SENTRY_DSN" == "" ]
then
    SENTRY_DSN=https://fe9e540bdac242f8b8368969898b18ed:8cf5e54884964a5793998a1f5dfcabb7@sentry.io/243100
fi

python manage.py rqworker