#!/usr/bin/env bash

IMAGE=registry.cutt.com/p/marking/backend

docker pull $IMAGE
docker rm -f tuiguang_api_for_phone
docker run -d \
    -v /data/tmp:/data/tmp \
    -v /data/logs2:/code/logs \
    -v /data/local/local_settings.py:/code/sns_app/local_settings.py \
    -e TZ=Asia/Shanghai \
    -e WORKERS=4 \
    -p 8100:8000 \
    --name tuiguang_api_for_phone \
    $IMAGE

