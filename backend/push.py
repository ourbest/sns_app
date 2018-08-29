import requests
from dj.utils import api_func_anonymous

from backend import model_manager

DING_URL = 'https://oapi.dingtalk.com/robot/send?' \
           'access_token=709a2470c97ad8df5ff536904bf4fd38823125dd95ea928592d20186a3a034c0'


@api_func_anonymous
def send_notify(app_id, item_id, title, push_time):
    app = model_manager.get_app(app_id)
    msg_title = '{0}有新的推送通过了审核'.format(app.app_name)
    msg_body = """
## {0}
> [{2}](https://tg.appgc.cn/api/item/url?id={3}))
> 推送时间：{4}    
    """.format(app.app_name, app.app_id, title, item_id, push_time)

    phones = [x.user.phone for x in app.userfollowapp_set.select_related('user').exculde(user__phone__isnull=True)]
    dingding_msg = {
        'msgtype': 'markdown',
        'markdown': {
            'title': msg_title,
            'text': msg_body,
        }, 'at': {
            'atMobiles': phones,
            'isAtAll': False
        }
    }
    requests.post(DING_URL, json=dingding_msg)
