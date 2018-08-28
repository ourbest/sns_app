import requests
from dj.utils import api_func_anonymous
from django.conf import settings
from django.http import HttpResponse
from qiniu import Auth, BucketManager

from backend import model_manager
from backend.zhiyue_models import ImageUploader

url = 'https://oapi.dingtalk.com/robot/send?' \
      'access_token=a9485347e2627c97f52ae75899b4a606db9ecdec0b9875ae3fef982a0db962de'


def send_image_audit(image_id):
    db = model_manager.query(ImageUploader).filter(imageId=image_id).first()

    dingding_msg = {
        'msgtype': 'actionCard',
        'actionCard': {
            'title': '确认图片有没有问题(%s)' % db.partnerId if db else '',
            'text': '## 确认图片有没有问题(%s)\n\n![pic](http://ty.appgc.cn/%s/2)\n\n### %s选择是？\n\n'
                    % (db.partnerId if db else '', image_id, image_id),
            'hideAvatar': '1',
            'btnOrientation': '1',
            'btns': [
                {
                    'title': '没有问题',
                    'actionURL': 'https://tg.appgc.cn/api/mark?res=ok&img=%s' % image_id
                },
                {
                    'title': '黄图',
                    'actionURL': 'https://tg.appgc.cn/api/mark?res=color&img=%s' % image_id
                }
            ]
        },
    }
    requests.post(url, json=dingding_msg)


@api_func_anonymous
def mark_status(img, res):
    send_done(img)
    if res == 'ok':
        pass
    else:
        q = Auth(settings.QINIU_AK, settings.QINIU_SK)
        bucket = BucketManager(q)
        bucket_name = 'cimg1'
        for i in range(1, 3):
            if do_rename(bucket, bucket_name, img):
                return HttpResponse('已处理')

    return HttpResponse('OK')


def send_done(img):
    dingding_msg = {
        'msgtype': 'text',
        'text': {
            'content': '%s已处理' % img,
        }
    }
    requests.post(url, json=dingding_msg)


def do_rename(bucket, bucket_name, img):
    try:
        bucket.move(bucket_name, img, bucket_name, 'bad/%s' % img)
        return True
    except:
        pass
