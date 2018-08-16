#!/usr/bin/env bash

IMAGE=registry.cutt.com/p/marking/backend

docker pull $IMAGE
docker rm -f dao_sns_app_web_1
docker rm -f tuiguang_api
docker run -d \
    -v /data/tmp:/data/tmp \
    -v /data/logs:/code/logs \
    -v /data/local/local_settings.py:/code/sns_app/local_settings.py \
    -e TZ=Asia/Shanghai \
    -e WORKERS=8 \
    -p 8000:8000 \
    --name tuiguang_api \
    $IMAGE

