#!/usr/bin/env bash

IMAGE=registry.cutt.com/p/marking/backend

docker pull $IMAGE
docker rm -f log_consumer
docker run -d \
    -v /data/tmp:/data/tmp \
    -v /data/logs:/code/logs \
    -v /data/local/local_settings.py:/code/sns_app/local_settings.py \
    -e TZ=Asia/Shanghai \
    --name log_consumer \
    $IMAGE consumer


sleep 2
docker logs log_consumer