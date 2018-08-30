import requests
from dj.utils import api_func_anonymous
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from qiniu import Auth, BucketManager

from backend import model_manager
from backend.models import AuditImage
from backend.zhiyue_models import ImageUploader, ZhiyueUser, PartnerImage

url = 'https://oapi.dingtalk.com/robot/send?' \
      'access_token=a4386542db725785c6499e83cf8242bde68b3f6359a57ead50fa052ca3a77ed9'


def send_image_audit(image_id):
    if image_id.startswith('e_'):
        return

    app_id = 0
    db = model_manager.query(ImageUploader).filter(imageId=image_id).first()

    if not db:
        pi = model_manager.query(PartnerImage).filter(imageId=image_id).first()
        if pi:
            app_id = pi.partnerId
    else:
        app_id = db.partnerId

    model_manager.save_ignore(AuditImage(image_id, app_id=app_id, user_id=db.userId if db else 0))

    dingding_msg = {
        'msgtype': 'actionCard',
        'actionCard': {
            'title': '确认图片有没有问题(%s)' % db.partnerId if db else '',
            'text': '## 确认图片有没有问题(%s)\n\n![pic](http://ty.appgc.cn/%s/2)\n\n '
                    '[浏览器打开](https://tg.appgc.cn/api/qn/img?img=%s)\n\n### %s选择是？\n\n'
                    % (db.partnerId if db else '', image_id, image_id, image_id),
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
    db = AuditImage.objects.filter(image_id=img).first()
    if db:
        db.status = 1 if 'ok' == res else 2
        model_manager.save_ignore(db)

    if res == 'ok':
        pass
    else:
        add = ''
        db = model_manager.query(ImageUploader).filter(imageId=img).first()
        if db:
            user = model_manager.query(ZhiyueUser).filter(userId=db.userId).first()
            add = '，上传的APP({0})，用户：{2}({1})'.format(db.partnerId, user.userId, user.name)
        # else:
        if res == 'auto':
            add = '，图片是黄图的置信度高，已自动处理'
        else:
            q = Auth(settings.QINIU_AK, settings.QINIU_SK)
            bucket = BucketManager(q)
            bucket_name = 'cimg1'
            for i in range(1, 3):
                if do_rename(bucket, bucket_name, img):
                    send_done(img, add)
                    break

        return HttpResponse('已处理' + add)
    send_done(img)
    return HttpResponse('OK')


def send_done(img, add=''):
    q = AuditImage.objects.filter(status=0)
    extra = ''
    cnt = len(q)
    if cnt:
        extra = '还有以下%s个图片需要处理' % cnt

    dingding_msg = {
        'msgtype': 'text',
        'text': {
            'content': '%s已处理%s%s' % (img, add, extra),
        }
    }
    requests.post(url, json=dingding_msg)

    for x in q:
        send_image_audit(x.image_id)
        break


def do_rename(bucket, bucket_name, img):
    try:
        bucket.move(bucket_name, img, bucket_name, 'bad/%s' % img)
        return True
    except:
        pass


@api_func_anonymous
def show_img(img):
    q = Auth(settings.QINIU_AK, settings.QINIU_SK)
    return HttpResponseRedirect(q.private_download_url('http://ty.appgc.cn/%s' % img, 30))
