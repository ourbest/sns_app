#!/usr/bin/env bash

IMAGE=registry.cutt.com/p/marking/backend

docker pull $IMAGE
docker rm -f tuiguang_worker_1
docker run -d \
    -v /data/tmp:/data/tmp \
    -v /data/logs:/code/logs \
    -v /data/local/local_settings.py:/code/sns_app/local_settings.py \
    -e TZ=Asia/Shanghai \
    -e RQWORKER=1 \
    --name tuiguang_worker_1 \
    $IMAGE

sleep 1

docker rm -f tuiguang_worker_2
docker run -d \
    -v /data/tmp:/data/tmp \
    -v /data/logs:/code/logs \
    -v /data/local/local_settings.py:/code/sns_app/local_settings.py \
    -e TZ=Asia/Shanghai \
    -e RQWORKER=1 \
    --name tuiguang_worker_2 \
    $IMAGE

sleep 2
docker logs tuiguang_worker_2