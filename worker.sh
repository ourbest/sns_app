#!/bin/sh


python manage.py rqworker --name WORKER_`date +"%m%d%s"`