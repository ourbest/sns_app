from backend import model_manager
from backend.models import User
from backend.zhiyue_models import HighValueUser


def app_daily_stat(app, date, include_sum=False):
    qq_stats = []
    wx_stats = []
    qq_sum = {
        'share': 0,
        'weizhan': 0,
        'download': 0,
        'reshare': 0,
        'users': 0,
        'name': '合计',
        'uid': 0,
    }

    wx_sum = {
        'share': 0,
        'weizhan': 0,
        'download': 0,
        'reshare': 0,
        'users': 0,
        'name': '合计',
        'uid': 0,
    }
    for user in User.objects.filter(app=app, status=0):
        stats = get_user_stat(date, user)
        qq_stat = {
            'share': 0,
            'weizhan': 0,
            'download': 0,
            'reshare': 0,
            'users': 0,
            'uid': user.id,
            'name': user.name,
        }

        qq_stats.append(qq_stat)
        wx_stat = {
            'share': 0,
            'weizhan': 0,
            'download': 0,
            'reshare': 0,
            'users': 0,
            'uid': user.id,
            'name': user.name,
        }

        wx_stats.append(wx_stat)
        for qq in stats:
            stat = qq_stat if qq['type'] == 'QQ' else wx_stat
            sum = qq_sum if qq['type'] == 'QQ' else wx_sum
            stat['share'] += qq['share']
            stat['weizhan'] += qq['weizhan']
            stat['download'] += qq['download']
            stat['reshare'] += qq['reshare']
            stat['users'] += qq['users']

            sum['share'] += qq_stat['share']
            sum['weizhan'] += qq['weizhan']
            sum['download'] += qq['download']
            sum['reshare'] += qq['reshare']
            sum['users'] += qq['users']

    if len(qq_stats) or include_sum:
        qq_stats.append(qq_sum)
        wx_stats.append(wx_sum)
    return {
        'qq': qq_stats,
        'wx': wx_stats,
    }


def get_user_stat(date, the_user):
    cutt_users = list(the_user.appuser_set.all())
    cutt_user_dict = {x.cutt_user_id: x for x in cutt_users}

    return [{
        'id': x.userId,
        'name': x.name,
        'type': '微信' if 1 == cutt_user_dict.get(x.userId).type else 'QQ',
        'share': x.shareNum,
        'weizhan': x.weizhanNum,
        'download': x.downPageNum,
        'reshare': x.secondShareNum,
        'users': x.appUserNum,
    } for x in model_manager.query(HighValueUser).filter(partnerId=the_user.app_id, time=date, userType=2,
                                                         userId__in=[x.cutt_user_id for x in cutt_users])]
