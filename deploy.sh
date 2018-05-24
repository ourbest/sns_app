#!/usr/bin/env bash

IMAGE=registry.cutt.com/p/tuiguang

docker pull $IMAGE
docker rm -f tuiguang_api
docker run -d \
    -v /data/tmp:/data/tmp \
    -v /data/logs/result:/code/logs/result \
    -v /data/logs2:/code/logs \
    -v /data/local/local_settings.py:/code/sns_app/local_settings.py \
    -e TZ=Asia/Shanghai \
    -e WORKERS=8 \
    -p 8100:8000 \
    --name tuiguang_api \
    $IMAGE

