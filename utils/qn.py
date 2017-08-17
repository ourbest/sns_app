from qiniu import Auth, put_file
from django.conf import settings

AK = settings.QINIU_AK
SK = settings.QINIU_SK
BUCKET = settings.QINIU_BUCKET

q = Auth(AK, SK)


def upload_file(key, local_file):
    token = q.upload_token(BUCKET, key, 3600)
    ret, info = put_file(token, key, local_file)
    return ret.get('key') == key
