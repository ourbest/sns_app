import os
import re
from collections import defaultdict

import requests
from datetime import timedelta, datetime
from math import radians, sin, atan2, cos, sqrt

from dj import times
from django.conf import settings
from django.db import connection, connections
from django.db.models import Sum
from django.template.loader import render_to_string
from django.utils import timezone
from django_rq import job
from .loggs import logger
from qiniu import Auth, put_file

from backend import api_helper, model_manager, group_splitter, zhiyue, stat_utils, caches, dates
from backend.api_helper import ADD_STATUS, deal_add_result, deal_dist_result
from backend.model_manager import save_ignore
from backend.models import DeviceFile, SnsUser, SnsGroup, SnsUserGroup, SnsApplyTaskLog, SnsGroupSplit, WxDistLog, \
    SnsUserKickLog, DeviceTaskData, DailyActive, App, UserDailyStat, AppDailyStat, DeviceWeixinGroup, SnsGroupLost, \
    DeviceWeixinGroupLost, SnsTask, UserDailyResourceStat, AppDailyResourceStat, AppUser, \
    AppWeeklyStat, User, SnsTaskDevice
from backend.stat_utils import get_count, get_user_share_stat, app_daily_stat, classify_data_app
from backend.zhiyue_models import ZhiyueUser, DeviceUser
import os
import re
from collections import defaultdict
from datetime import timedelta, datetime
from math import radians, sin, atan2, cos, sqrt

import requests
from dj import times
from django.conf import settings
from django.db import connection, connections
from django.db.models import Sum
from django.template.loader import render_to_string
from django.utils import timezone
from django_rq import job
from qiniu import Auth, put_file

from backend import api_helper, model_manager, group_splitter, zhiyue, stat_utils, caches, dates
from backend.api_helper import ADD_STATUS, deal_add_result, deal_dist_result
from backend.model_manager import save_ignore
from backend.models import DeviceFile, SnsUser, SnsGroup, SnsUserGroup, SnsApplyTaskLog, SnsGroupSplit, WxDistLog, \
    SnsUserKickLog, DeviceTaskData, DailyActive, App, UserDailyStat, AppDailyStat, DeviceWeixinGroup, SnsGroupLost, \
    DeviceWeixinGroupLost, SnsTask, UserDailyResourceStat, AppDailyResourceStat, AppUser, \
    AppWeeklyStat, User, SnsTaskDevice
from backend.stat_utils import get_count, get_user_share_stat, app_daily_stat, classify_data_app
from backend.zhiyue_models import ZhiyueUser, DeviceUser
from .loggs import logger


@job("default", timeout=3600)
def do_re_import(i_file_id, merge=True):
    file = DeviceFile.objects.filter(id=i_file_id).first()
    if file:
        from backend.apis import _get_content
        text = _get_content(file.qiniu_key)
        file_name = '/data/tmp/tmp_%s.qn' % i_file_id
        with open(file_name, 'wt', encoding='utf-8') as out:
            out.write(text)

        _after_upload(file.device_task, file.device_task.id, file_name, file.device, file.type, merge)

    return ''


@job
def _after_upload(device_task, task_id, tmp_file, device, file_type, merge=True):
    if file_type == 'result':
        logger.info('after upload import temp file %s task_id is %s file type is %s' % (tmp_file, task_id, file_type))
        from backend.apis import import_qun
        with open(tmp_file, 'rt', encoding='utf-8') as f:
            upload_file_content = f.read()
            if device_task:
                logger.info('The type is %s', device_task.task.type_id)
                if device_task.task.type_id == 4:  # 统计
                    do_import_qun_stat(upload_file_content, device.label, device_task.status)
                elif device_task.task.type_id == 1:  # 查群
                    logger.info('查群结果')
                    import_qun(device_task.task.app_id, upload_file_content,
                               None, device_task.device.owner.email, None, None, False)
                elif device_task.task.type_id == 2:  # 加群
                    import_add_result(device_task, upload_file_content)
                elif device_task.task.type_id == 3:  # 分发
                    import_dist_result(device_task, upload_file_content)
                elif device_task.task.type_id == 5:  # 微信分发
                    import_wx_dist_result(device_task, upload_file_content)
                elif device_task.task.type_id == 6:  # 微信统计
                    import_wx_qun(device_task, upload_file_content)

                if merge:
                    api_helper.merge_task_result(device_task.task, upload_file_content)

            if task_id == 'stat':
                do_import_qun_stat(upload_file_content, None, 2)
            elif task_id == 'qun':
                import_qun(device.owner.app_id, upload_file_content, None, device.owner.email, None, None, False)
    os.remove(tmp_file)


@job
def do_import_qun_stat(ids, device_id, status):
    logger.info('import stat of %s', device_id)
    if not status:
        status = 2

    to_save = defaultdict(list)
    total = 0
    for line in ids.split('\n'):
        line = line.strip()
        if line:
            account = line.split('\t')
            if len(account) == 4 and account[0].isdigit():
                total += 1
                to_save[account[3]].append((account[0], account[1], account[2]))

    device = model_manager.get_phone(device_id)

    for k, accounts in to_save.items():
        sns_user = SnsUser.objects.filter(login_name=k, type=0).first()
        if device and not sns_user:
            logger.info("Sns user %s not found device is %s", k, device_id)
            sns_user = SnsUser(name=k, login_name=k, passwd='_',
                               phone=device.phone_num, device=device,
                               owner=device.owner, app=device.owner.app)
            sns_user.save()

        if sns_user:

            if not device:
                device = sns_user.device

            if sns_user.device != device:
                sns_user.device = device
                sns_user.owner = device.owner
                sns_user.phone = device.label
                sns_user.save()

            all_groups = sns_user.snsusergroup_set.all()
            all_groups_in = [x for x in all_groups if x.status == 0]
            # now_ids = {x.sns_group_id for x in all_groups}
            all_group_ids = set()
            for (qun_num, qun_name, qun_user_cnt) in accounts:
                if qun_num in all_group_ids:
                    continue
                all_group_ids.add(qun_num)
                found = None
                for group in all_groups:
                    if qun_num == group.sns_group_id:
                        # in
                        found = group
                        break

                if not found:
                    # 新增
                    qun = SnsGroup.objects.filter(group_id=qun_num, type=0).first()
                    qun_user_cnt = 0 if not qun_user_cnt.isdigit() else int(qun_user_cnt)
                    if not qun:
                        qun = SnsGroup(group_id=qun_num, group_name=qun_name, type=0, app_id=sns_user.app_id,
                                       group_user_count=qun_user_cnt, status=2, created_at=timezone.now(),
                                       from_user_id=device.owner_id)
                        qun.save()
                        model_manager.process_tag(qun)
                    else:
                        if qun.status != 2:
                            qun.status = 2

                        qun.group_user_count = qun_user_cnt
                        qun.name = qun_name
                        model_manager.save_ignore(qun, True)
                        qun.snsgroupsplit_set.filter(phone=device).update(status=3)

                    SnsUserGroup(sns_group=qun, sns_user=sns_user, status=0, active=1).save()
                    SnsApplyTaskLog.objects.filter(account=sns_user, memo='已发送验证', group=qun).update(status=1)
                else:
                    if found.status != 0:
                        found.status = 0
                        found.active = 1
                        found.save()

                    qun = found.sns_group

                    if qun.status != 2:
                        qun.status = 2
                    qun.group_name = qun_name
                    qun.group_user_count = qun_user_cnt
                    save_ignore(qun)
                    # qun.save()

                    qun.snsgroupsplit_set.filter(phone=device).update(status=3)

            if status == 2:
                logger.info('%s 原有%s, 现有%s', sns_user, len(all_groups_in), len(all_group_ids))
                lost = 0
                for group in all_groups_in:
                    if group.sns_group_id not in all_group_ids:
                        # 被踢了
                        model_manager.set_qun_kicked(group)
                        lost += 1

                if lost:
                    logger.info("QQ %s total lost %s groups", sns_user, lost)
                    model_manager.deal_kicked(device.owner)

    SnsGroupSplit.objects.filter(phone=device, status=1).update(status=0)
    SnsGroupSplit.objects.filter(phone=device, status=2, updated_at=timezone.now() - timedelta(days=7)).update(status=0)
    logger.info('Import done total %s', total)


def do_import_qun(app, ids, email, phone, edit_method, i_ignore_dup):
    logger.info('Import qun of %s', app)
    login_user = None
    if email:
        login_user = model_manager.get_user(email)

    cnt = 0
    total = 0
    exists = {x.group_id for x in SnsGroup.objects.filter(app_id=app)}

    the_app = model_manager.get_app(app)

    device = model_manager.get_phone(phone) if phone else None

    if "edit" == edit_method and device:
        to_delete = SnsGroupSplit.objects.filter(user=login_user, phone=device)
        if not i_ignore_dup:
            to_delete = to_delete.exclude(group__in=exists)

        to_delete.delete()

    split_to_self = login_user.snsuser_set.filter(app=the_app, friend=1).count() if login_user else 0

    for line in ids.split('\n'):
        line = line.strip()
        if line:
            total += 1
            account = line.split('\t')  # re.split('\s+', line) ## 群名称有可能有空格
            try:
                if not account[0].isdigit():
                    continue
                if account[0] in exists:
                    if device and i_ignore_dup == 0:
                        qun = model_manager.get_qun(account[0])
                        if "new" == edit_method:
                            SnsGroupSplit.objects.filter(group=qun, user=login_user, status__in=(0, 1)).delete()

                        if qun.snsgroupsplit_set.filter(status__in=(0, 1, 2)).count() == 0:
                            logger.info(
                                "split %s(%s) to %s at %s" % (qun.group_name, qun.group_id, login_user.name, app))
                            SnsGroupSplit(group=qun, user=login_user, phone=device, app_id=app).save()

                    continue

                logger.info('找到了新群 %s' % line)

                db = SnsGroup(group_id=account[0], group_name=account[1], type=0, app_id=app,
                              group_user_count=account[2], created_at=timezone.now(), from_user=login_user)
                db.save()
                model_manager.process_tag(db)
                cnt += 1

                if len(account) > 3:
                    if not db:
                        db = model_manager.get_qun(account[0])
                    qq_num = account[3]
                    su = SnsUser.objects.filter(login_name=qq_num, type=0).first()
                    if db and su:
                        sug = SnsUserGroup.objects.filter(sns_user=su, sns_group=db).first()
                        if not sug:
                            sug = SnsUserGroup(sns_group=db, sns_user=su, status=0)
                        sug.active = 1
                        sug.save()
                        db.status = 2
                        db.snsgroupsplit_set.filter(status=0).update(status=3)
                        db.save()
                elif split_to_self and login_user and (
                        device or (the_app and the_app.self_qun == 1)) and login_user.app == the_app:
                    logger.info("split %s(%s) to %s at %s" % (db.group_name, db.group_id, login_user.name, app))
                    SnsGroupSplit(group=db, user=login_user, phone=device, app_id=app).save()
            except:
                logger.warning("error save %s" % line, exc_info=1)

    logger.info('共%s个新群' % cnt)

    if not device:
        if split_to_self and the_app and the_app.self_qun == 1 and login_user.app == the_app:
            group_splitter.split_qun_device(email)

    return {
        'count': cnt,
        'total': total,
        'message': '成功'
    }


def import_wx_dist_result(device_task, lines):
    reg = r'(.+)\t\((\d+)\)$'
    reg2 = r'(.+)\t\((\d+)\)\tY$'
    for line in lines.split('\n'):
        match = re.match(reg, line)
        if match:
            (name, cnt) = match.groups()
            log = WxDistLog(task=device_task, group_name=name if len(name) < 100 else (name[0:90] + '...'),
                            user_count=cnt)
            log.save()
        else:
            match = re.match(reg2, line)
            if match:
                (name, cnt) = match.groups()
                log = WxDistLog(task=device_task, group_name=name if len(name) < 100 else (name[0:90] + '...'),
                                user_count=cnt, dist=1)
                log.save()

    model_manager.sync_wx_log(device_task)


def import_wx_qun(device_task, lines):
    if not lines:
        return

    reg = r'(.+)\t\((\d+)\)$'
    groups = list()
    for line in lines.split('\n'):
        match = re.match(reg, line)
        if match:
            (name, cnt) = match.groups()
            i = int(cnt)
            if i:
                groups.append([name, i])

    model_manager.sync_wx_groups_imports(device_task.device, groups)


def import_dist_result(device_task, lines):
    """
    1列群号，2列结果，3列QQ号，结果：已分发、被禁言、被踢出
    :param device_task:
    :param lines:
    :return:
    """
    kicked = 0
    add = False
    dist_ed_qq = set()

    old_db = DeviceTaskData.objects.filter(device_task=device_task).first()

    if not old_db:
        return 0

    content = old_db.lines
    should_done = set()

    has_unknown = 0

    removed = list()

    for line in content.split('\n'):
        line = line.strip()
        if line.find('QQ_') == 0:
            should_done.add(line.split('=')[1])

    for line in lines.split('\n'):
        line = line.strip()
        if line:
            if line.find('删除帐号=') == 0:
                qq_id = line[len('删除帐号='):]
                if qq_id in should_done:
                    SnsUserKickLog(sns_user=model_manager.get_qq(qq_id), device_task=device_task).save()
                    dist_ed_qq.add(qq_id)
                    removed.append(qq_id)
                else:
                    has_unknown += 1
                continue
            try:
                values = re.split('\s+', line)
                if len(values) == 3:
                    [qun_id, status, qq_id] = values
                    qun = model_manager.get_qun(qun_id)
                    if not qun:
                        logger.warning('日志中的群号没有记录%s' % qun_id)
                        continue
                    qq = model_manager.get_qq(qq_id)

                    if status in ADD_STATUS:
                        add = True
                        deal_add_result(device_task, qq, qun, status)
                    else:
                        dist_ed_qq.add(qq_id)
                        if deal_dist_result(device_task, qq, qun, status):
                            kicked += 1
            except:
                logger.warning('error import line %s' % line, exc_info=1)

    message = ''
    if add:
        model_manager.reset_qun_status(device_task)

    if has_unknown:
        #     should_done.discard(dist_ed_qq)
        #     if has_unknown == len(should_done):
        #         for qq_id in should_done:
        #             SnsUserKickLog(sns_user=model_manager.get_qq(qq_id), device_task=device_task).save()
        #             removed.add(qq_id)
        # else:
        removed.append('%s个未知QQ' % has_unknown)

    if len(removed):
        message += '（%s）账号从QQ移除了😭，' % (' '.join(removed))

    if kicked:
        model_manager.deal_kicked(device_task.device.owner)
        message += '此次分发检测到被踢了%s个群😢，' % kicked

    if message:
        api_helper.webhook(device_task, '注意：' + message + '请检查', force=len(removed) > 0)

    return kicked


def import_add_result(device_task, lines):
    """
    1列 群号，2列 属性，3列QQ号
    属性有这些：付费群，不存在，不允许加入，需要回答问题，已发送验证，满员群，已加群，无需验证已加入
    :param device_task:
    :param lines:
    :return:
    """
    for line in lines.split('\n'):
        line = line.strip()
        try:
            values = re.split('\s+', line)
            if len(values) == 3:
                [qun_id, status, qq_id] = values
                qun = model_manager.get_qun(qun_id)
                qq = model_manager.get_qq(qq_id)
                db = SnsApplyTaskLog.objects.filter(device=device_task.device,
                                                    device_task=device_task,
                                                    account=qq, group=qun).first()
                if not db:
                    deal_add_result(device_task, qq, qun, status)
        except:
            logger.warning('error import line %s' % line, exc_info=1)

    model_manager.reset_qun_status(device_task)


@job
def do_save_daily_active():
    daily_stats = zhiyue.do_get_app_stat()
    for daily_stat in daily_stats:
        iphone = int(daily_stat.get('iphone', 0))
        android = int(daily_stat.get('android', 0))
        DailyActive(app_id=daily_stat['app_id'], iphone=iphone,
                    android=android, total=iphone + android).save()

    # do_save_active_id()


@job
def do_save_active_id():
    ids = [str(x.pk) for x in model_manager.get_dist_apps()]
    zhiyue_users = model_manager.query(ZhiyueUser).filter(appId__in=ids, platform__in=['iphone', 'android'],
                                                          lastActiveTime__gt=timezone.now() - timedelta(minutes=15))
    for x in zhiyue_users:
        caches.redis_client.zadd('shq-ol', x.lastActiveTime.timestamp(), x.userId)

    caches.redis_client.zremrangebyscore('shq-ol', 0, (timezone.now() - timedelta(days=1)).timestamp())

    for x in model_manager.query(DeviceUser).filter(deviceUserId__in=[x.userId for x in zhiyue_users]).exclude(
            location=''):
        if x.location:
            caches.redis_client.set('loc-%s' % x.deviceUserId, x.location, 3600 * 24)


@job
def sync_user_region(user):
    if not user.region and user.location:
        response = requests.post('http://10.9.21.184/api/lbs/region',
                                 {'appId': user.app_id, 'lbs': user.location})
        if response.status_code == 200:
            user.region = response.json()['data']
            if user.region:
                user.save(update_fields=['region'])


@job
def make_heat_data():
    # today = model_manager.today().timestamp()
    #
    # keys = ['loc-%s' % x.decode() for x in caches.redis_client.zrangebyscore('shq-ol', today, today + 3600 * 24)]
    # loc = merge_loc([to_loc(x.decode()) for x in caches.redis_client.mget(keys) if x])
    # js = 'heatData = %s;' % (json.dumps(loc))
    # with open('/tmp/heat.js', 'w') as f:
    #     f.write(js)
    #
    # now = datetime.now()
    # min = now.minute
    # ts = int(now.replace(second=0, minute=int(min / 10) * 10).timestamp())
    # key = 'heat/%s%s.js' % (now.strftime('%Y%m%d%H'), ts)
    # upload_to_qn('/tmp/heat.js', key)
    pass


def to_loc(x):
    split = x.split(',')
    return {
        'lng': float(split[0]),
        'lat': float(split[1]),
        'count': 1
    }


@job
def do_daily_stat(date, resource=True):
    date = dates.yesterday() if not date else datetime.strptime(date, '%Y-%m-%d')

    for app in model_manager.get_dist_apps():
        stat = stat_utils.app_daily_stat(app.app_id, date, include_sum=True)
        qq_stat = stat['qq']
        wx_stat = stat['wx']

        for index, qs in enumerate(qq_stat):
            if qs['uid']:
                ws = wx_stat[index]

                UserDailyStat.objects.filter(report_date=date.strftime('%Y-%m-%d'), app=app,
                                             user_id=qs['uid']).delete()

                db = UserDailyStat.objects.filter(report_date=date.strftime('%Y-%m-%d'), app=app,
                                                  user_id=qs['uid']).first()

                if not db:
                    db = UserDailyStat(report_date=date.strftime('%Y-%m-%d'), app=app, user_id=qs['uid'],
                                       qq_pv=qs['weizhan'], wx_pv=ws['weizhan'], qq_down=qs['download'],
                                       wx_down=ws['download'], qq_install=qs['users'], wx_install=ws['users'])
                    db.save()
                else:
                    db.qq_pv = qs['weizhan']
                    db.wx_pv = ws['weizhan']
                    db.qq_down = qs['download']
                    db.wx_down = ws['download']
                    db.qq_install = qs['users']
                    db.wx_install = ws['users']
                    model_manager.save_ignore(db)
            else:
                ws = wx_stat[index]
                db = AppDailyStat.objects.filter(report_date=date.strftime('%Y-%m-%d'), app=app).first()
                if not db:
                    db = AppDailyStat(report_date=date.strftime('%Y-%m-%d'), app=app,
                                      qq_pv=qs['weizhan'], wx_pv=ws['weizhan'],
                                      qq_down=qs['download'], wx_down=ws['download'],
                                      qq_install=qs['users'], wx_install=ws['users'])
                    db.save()
                else:
                    db.qq_pv = qs['weizhan']
                    db.wx_pv = ws['weizhan']
                    db.qq_down = qs['download']
                    db.wx_down = ws['download']
                    db.qq_install = qs['users']
                    db.wx_install = ws['users']
                    model_manager.save_ignore(db)

    if resource:
        make_resource_stat(date + timedelta(1))


def make_resource_stat(today):
    # today = times.localtime(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
    today_range = (today - timedelta(days=1), today)
    for app in App.objects.filter(stage__in=('留守期', '分发期', '准备期')):
        # 记录资源的情况
        users = app.user_set.filter(status=0)
        user_stats = []
        for user in users:
            group_cnt = SnsUserGroup.objects.filter(sns_user__device__owner=user, status=0, sns_user__status=0).count()
            group_uniq_cnt = SnsUserGroup.objects.filter(sns_user__device__owner=user, status=0,
                                                         sns_user__status=0).values(
                'sns_group_id').distinct().count()
            wx_group_cnt = DeviceWeixinGroup.objects.filter(device__owner=user).count()
            wx_group_uniq_cnt = DeviceWeixinGroup.objects.filter(device__owner=user).values('name').count()
            qq_apply_cnt = SnsApplyTaskLog.objects.filter(device__owner=user,
                                                          created_at__range=today_range,
                                                          memo__in=('已发送验证', '无需验证已加入')).count()
            qq_lost_cnt = SnsGroupLost.objects.filter(sns_user__owner=user,
                                                      created_at__range=today_range).count()
            wx_lost_cnt = DeviceWeixinGroupLost.objects.filter(device__owner=user,
                                                               created_at__range=today_range).count()

            qq_cnt = SnsTask.objects.filter(creator=user, status=2, started_at__range=today_range, type=3).count()
            wx_cnt = SnsTask.objects.filter(creator=user, status=2, started_at__range=today_range, type=5).count()

            UserDailyResourceStat.objects.filter(app=app, user=user, stat_date=today).delete()
            s = UserDailyResourceStat(app=app, stat_date=today, user=user, qq_cnt=qq_cnt, wx_cnt=wx_cnt,
                                      phone_cnt=user.phonedevice_set.filter(status=0).count(),
                                      qq_acc_cnt=user.snsuser_set.filter(status=0).count(),
                                      qq_group_cnt=group_cnt, qq_uniq_group_cnt=group_uniq_cnt,
                                      wx_group_cnt=wx_group_cnt, wx_uniq_group_cnt=wx_group_uniq_cnt,
                                      qq_apply_cnt=qq_apply_cnt, qq_lost_cnt=qq_lost_cnt, wx_lost_cnt=wx_lost_cnt)
            s.save()
            user_stats.append(s)

        group_total = SnsGroup.objects.filter(app=app).count()
        group_new = SnsGroup.objects.filter(app=app, created_at__range=today_range).count()
        group_uniq_cnt = SnsUserGroup.objects.filter(sns_user__app=app, status=0, sns_user__status=0).values(
            'sns_group_id').distinct().count()
        group_cnt = SnsUserGroup.objects.filter(sns_user__app=app, status=0, sns_user__status=0).count()
        wx_uniq_cnt = DeviceWeixinGroup.objects.filter(device__owner__app=app).values('name').distinct().count()
        wx_group_cnt = DeviceWeixinGroup.objects.filter(device__owner__app=app).count()

        AppDailyResourceStat.objects.filter(app=app, stat_date=today).delete()
        s = AppDailyResourceStat(app=app, stat_date=today, qq_cnt=0, wx_cnt=0, phone_cnt=0, qq_acc_cnt=0,
                                 qq_group_cnt=group_cnt, qq_uniq_group_cnt=group_uniq_cnt, qq_group_new_cnt=group_new,
                                 wx_group_cnt=wx_group_cnt, wx_uniq_group_cnt=wx_uniq_cnt, qq_group_total=group_total,
                                 qq_apply_cnt=0, qq_lost_cnt=0, wx_lost_cnt=0)
        for x in user_stats:
            s.qq_cnt += x.qq_cnt
            s.wx_cnt += x.wx_cnt
            s.phone_cnt += x.phone_cnt
            s.qq_acc_cnt += x.qq_acc_cnt
            s.qq_apply_cnt += x.qq_apply_cnt
            s.qq_lost_cnt += x.qq_lost_cnt
            s.wx_lost_cnt += x.wx_lost_cnt
        s.save()


@job("default", timeout=3600)
def do_get_item_stat_values(app):
    stat_utils.sync_article_stat()

    # item_apps = dict()
    # article_dict = dict()

    # from_time = timezone.now() - timedelta(days=7)
    # query = DistArticle.objects.filter(started_at__gte=from_time)
    #
    # if app:
    #     query = query.filter(app_id=app)
    # for item in query:
    #     if item.app_id not in item_apps:
    #         item_apps[item.app_id] = list()
    #
    #     items = item_apps[item.app_id]
    #     items.append(item.item_id)
    #     article_dict[item.item_id] = item

    # for app_id, items in item_apps.items():
    #     qq_stats = batch_item_stat(app_id, items, from_time)
    #     wx_stats = {x['item_id']: x for x in batch_item_stat(app_id, items, from_time, user_type=1)}
    #
    #     for qq_stat in qq_stats:
    #         article = article_dict.get(qq_stat['item_id'])
    #         db = DistArticleStat.objects.filter(article=article).first()
    #         if not db:
    #             db = DistArticleStat(article=article)
    #
    #         db.qq_pv = qq_stat.get('weizhan')
    #         db.qq_down = qq_stat.get('download')
    #         db.qq_user = qq_stat.get('users')
    #         wx_stat = wx_stats.get(article.item_id)
    #         if wx_stat:
    #             db.wx_pv = wx_stat.get('weizhan')
    #             db.wx_down = wx_stat.get('download')
    #             db.wx_user = wx_stat.get('users')
    #
    #         user_ids = {x.creator_id for x in article.snstask_set.all()}
    #         db.dist_user_count = len(user_ids)
    #
    #         db.save()

    with connection.cursor() as cursor:
        tbl_name = 'tmp_stat_tbl_%s' % int(timezone.now().timestamp())
        tmp_tbl = 'CREATE TABLE %s (id bigint, owners bigint, groups bigint, devices bigint, users bigint)' % tbl_name
        tmp_tbl_2 = '''insert into %s (id, owners, groups, devices, users) select a.* from backend_distarticlestat s,
(select a.id, count(distinct t.creator_id) owners, count(l.group_id) groups,
 count(distinct d.`device_id`) devices, sum(group_user_count) users
from 
  backend_snsgroup g,
  backend_disttasklog l, backend_snstaskdevice d, 
  backend_snstask t, backend_distarticle a
where g.group_id = l.group_id and success=1 and d.task_id=t.id and l.task_id=t.id and t.article_id=a.id and t.type_id=3
and a.`created_at` > current_date - interval 7 day and d.created_at > now() - interval 8 HOUR group by a.id) a
where s.`article_id` = a.id''' % tbl_name
        query = '''update backend_distarticlestat s, %s a
set s.`dist_qq_user_count` = a.owners,
s.`dist_qq_phone_count` = a.devices,
s.`dist_qun_count` = a.groups,
s.dist_qun_user = a.users
where s.`article_id` = a.id
''' % tbl_name
        cursor.execute(tmp_tbl)
        cursor.execute(tmp_tbl_2)
        cursor.execute(query)
        cursor.execute('drop table %s' % tbl_name)

        query = '''update backend_distarticlestat s,
(select a.id, count(distinct t.creator_id) owners, count(distinct d.`device_id`) devices
from backend_snstaskdevice d, 
  backend_snstask t, backend_distarticle a
where d.task_id = t.id and t.article_id=a.id and t.type_id=5
and a.`created_at` > current_date - interval 7 day and d.created_at > now() - interval 8 HOUR group by a.id) a
set s.dist_wx_user_count = a.owners,
s.dist_wx_phone_count = devices
where s.article_id=a.id'''

        cursor.execute(query)


def batch_item_stat(app_id, items, from_time, user_type=0):
    date_end = from_time + timedelta(days=7)
    ids = [x.cutt_user_id for x in AppUser.objects.filter(user__app_id=app_id, type=user_type)]
    query = 'SELECT itemId, itemType, count(1) as cnt FROM datasystem_WeizhanItemView ' \
            'WHERE itemId in (%s) AND shareUserId in (%s) AND time BETWEEN \'%s\' AND \'%s\' ' \
            'GROUP BY itemId, itemType' % (
                ','.join(map(str, items)), ','.join(map(str, ids)), times.to_date_str(from_time),
                times.to_str(date_end, '%Y-%m-%d %H:%M:%S'))
    device_user_query = 'select sourceItemId, count(1) as cnt from datasystem_DeviceUser ' \
                        'where sourceItemId in (%s) and sourceUserId in (%s) ' \
                        'and createTime between \'%s\' AND \'%s\' GROUP BY sourceItemId' % (
                            ','.join(map(str, items)), ','.join(map(str, ids)), times.to_date_str(from_time),
                            times.to_date_str(date_end, '%Y-%m-%d %H:%M:%S'))
    data = dict()
    if not ids:
        return []
    if items:
        with connections['zhiyue'].cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                data['%s_%s' % (row[0], row[1])] = row[2]

            cursor.execute(device_user_query)
            rows = cursor.fetchall()
            for row in rows:
                data['%s_du' % (row[0],)] = row[1]
    return [{
        'item_id': x,
        'weizhan': get_count(data, x, ''),
        'reshare': get_count(data, x, '-reshare'),
        'download': get_count(data, x, '-down') + get_count(data, x, '-mochuang') + data.get(
            '%s_%s' % (x, 'tongji-down'), 0),
        'users': data.get('%s_du' % x, 0),
    } for x in items]


def send_follow_mail(date, user, app_stats, summary, sum_yesterday):
    ids = {x.app_id for x in user.userfollowapp_set.all()}
    if ids:
        app_stats = [x for x in app_stats if x['id'] in ids]
        summary = [x for x in summary if x['id'] in ids]
        sum_yesterday = [x for x in sum_yesterday if x['id'] in ids]
        send_report_mail(date, app_stats, sum_yesterday, summary, user.email)


@job("default", timeout=3600)
def do_gen_daily_report():
    # pid = os.fork()
    # if pid == 0:
    print('Generate report ...')
    yesterday = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    date = times.to_str(yesterday, '%Y-%m-%d')

    # print(yesterday)

    app_stats = []
    summary = []

    sum_yesterday = []

    for app in model_manager.get_dist_apps():
        item_stats = []
        stat = app_daily_stat(app.app_id, date, True)
        app_stats.append({
            'id': app.app_id,
            'app': app.app_name,
            'items': item_stats,
            'sum': stat,
        })

        summary.append({
            'id': app.app_id,
            'app': app.app_name,
            'qq': [x for x in stat['qq'] if x['name'] == '合计'][0],
            'wx': [x for x in stat['wx'] if x['name'] == '合计'][0],
        })
        for user in app.user_set.filter(status=0):
            item_stats += get_user_share_stat(yesterday, user)
            # sum_stats.append(get_user_stat(date, app.app_id))

        yesterday_stat = AppDailyStat.objects.filter(
            report_date=times.to_str(yesterday - timedelta(days=1), '%Y-%m-%d'), app=app).first()

        if yesterday_stat and (yesterday_stat.qq_remain == 0 or True):
            zhiyue.sync_report_online_remain(yesterday_stat)

            sum_yesterday.append({
                'id': app.app_id,
                'app': app.app_name,
                'weizhan': yesterday_stat.qq_pv + yesterday_stat.wx_pv,
                'users': yesterday_stat.qq_install + yesterday_stat.wx_install,
                'remain': yesterday_stat.qq_remain + yesterday_stat.wx_remain
            })

    if settings.DAILY_REPORT_EMAIL:
        send_report_mail(date, app_stats, sum_yesterday, summary, settings.DAILY_REPORT_EMAIL)

    for user in User.objects.filter(status__gte=0):
        if user.email not in settings.DAILY_REPORT_EMAIL:
            send_follow_mail(date, user, app_stats, summary, sum_yesterday)

    print('Done.')
    make_daily_detail()
    # os._exit(0)


def send_report_mail(date, app_stats, sum_yesterday, summary, mail):
    try:
        html = render_to_string('daily_report.html',
                                {'stats': app_stats, 'sum': summary, 'sum_yesterday': sum_yesterday})
        api_helper.send_html_mail('%s线上推广日报' % date, mail, html)
    except:
        logger.warning('error send email to ' % mail, exc_info=1)


def make_daily_detail():
    query = '''insert ignore into backend_dailydetaildata
(app_id, item_id, sns_type, title, category, date, total_user,
android_user, iphone_user, total_pv, android_pv, iphone_pv, total_down,
android_down, iphone_down, total_remain, iphone_remain, android_remain)
select
  b.app,
  b.item_id,
  b.type,
  REPLACE(c.title, '\n', '') title,
  coalesce(c.category, ''),
  b.stat_date,
  coalesce(total, 0),
  coalesce(android, 0),
  coalesce(iphone, 0),
  pv,
  apv,
  ipv,
  down,
  adown,
  idown,
  coalesce(remain, 0),
  coalesce(iremain, 0),
  coalesce(aremain, 0)
from
  backend_distarticle c,
  (select
     ai.item_id,
     ai.majia_type        type,
     ai.app_id            app,
     ai.stat_date,
     sum(ai.pv)           pv,
     sum(ai.mobile_pv)    mpv,
     sum(ai.down)         down,
     sum(ai.android_down) adown,
     sum(ai.android_pv)   apv,
     sum(ai.iphone_down)  idown,
     sum(ai.iphone_pv)    ipv
   from backend_articledailyinfo ai
   where ai.stat_date = current_date - interval 1 day
   group by majia_type, ai.app_id, ai.stat_date, ai.item_id) b
  left join (select
               app_id,
               item_id,
               type,
               date(created_at)                         stat_date,
               count(*)                                 total,
               sum(if(platform = 'android', 1, 0))      android,
               sum(if(platform = 'iphone', 1, 0))       iphone,
               sum(remain)                              remain,
               sum(if(platform = 'android', remain, 0)) aremain,
               sum(if(platform = 'iphone', remain, 0))  iremain
             from backend_itemdeviceuser du
             where du.created_at between current_date - interval 1 day and current_date
             group by type, item_id, app_id, date(created_at)) a
    on a.item_id = b.item_id and a.type = b.type and a.app_id = b.app
       and a.stat_date = b.stat_date
where b.item_id = c.item_id'''

    with connections['default'].cursor() as cursor:
        cursor.execute('update backend_dailydetaildata d, backend_distarticle a set '
                       'd.category = a.category where d.item_id=a.item_id '
                       'and a.category is not NULL '
                       'and d.category != \'\' '
                       'and a.category != d.category')
        cursor.execute(query)


@job
def make_weekly_stat(to_date=None):
    """
    周日到周六的数据，周一跑
    :return:
    """
    if not to_date:
        to_date = dates.today() - timedelta(days=2)

    from_date = (to_date - timedelta(days=6)).strftime('%Y-%m-%d')
    to_date = to_date.strftime('%Y-%m-%d')
    logger.info('Make weekly stat of from %s to %s' % (from_date, to_date))
    # to_date_1 = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    # from_date_1 = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    values = list(AppDailyStat.objects.filter(report_date__range=(from_date, to_date)).values(
        'app_id').annotate(qq_pv=Sum('qq_pv'), wx_pv=Sum('wx_pv'),
                           qq_down=Sum('qq_down'), wx_down=Sum('wx_down'),
                           wx_user=Sum('wx_install'), qq_user=Sum('qq_install'),
                           wx_remain=Sum('wx_remain'), qq_remain=Sum('qq_remain')))

    res_sum = {x['app_id']: x for x in
               list(AppDailyResourceStat.objects.filter(stat_date__range=(from_date, to_date)).values(
                   'app_id').annotate(qq_cnt=Sum('qq_cnt'), wx_cnt=Sum('wx_cnt'),
                                      qq_apply_cnt=Sum('qq_apply_cnt'), qq_lost_cnt=Sum('qq_lost_cnt'),
                                      qq_group_new_cnt=Sum('qq_group_new_cnt')))}

    for value in values:
        app_id = value['app_id']
        stat = AppWeeklyStat(app_id=app_id, stat_date='{} 到 {}'.format(from_date, to_date),
                             qq_pv=value['qq_pv'], wx_pv=value['wx_pv'],
                             qq_down=value['qq_down'], wx_down=value['wx_down'],
                             qq_user=value['qq_user'], wx_user=value['wx_user'],
                             qq_remain=value['qq_remain'], wx_remain=value['wx_remain'])

        user_cnt = User.objects.filter(app_id=app_id, status=0).count()
        stat.operators = user_cnt
        res = AppDailyResourceStat.objects.filter(app_id=app_id).order_by("-pk").first()
        stat.qq_group_cnt = res.qq_group_cnt
        stat.wx_group_cnt = res.wx_group_cnt
        stat.qq_uniq_group_cnt = res.qq_uniq_group_cnt
        stat.wx_uniq_group_cnt = res.wx_uniq_group_cnt
        stat.qq_group_total = res.qq_group_total
        stat.phone_cnt = res.phone_cnt
        stat.qq_acc_cnt = res.qq_acc_cnt
        stat.qq_members = res.qq_members
        stat.wx_members = res.wx_members
        stat.qq_cnt = res_sum[app_id]['qq_cnt']
        stat.wx_cnt = res_sum[app_id]['wx_cnt']
        stat.qq_apply_cnt = res_sum[app_id]['qq_apply_cnt']
        stat.qq_lost_cnt = res_sum[app_id]['qq_lost_cnt']
        stat.qq_group_new_cnt = res_sum[app_id]['qq_group_new_cnt']

        stat.save()

    send_stat_mail()


@job
def send_stat_mail(to_date=None):
    if not to_date:
        to_date = dates.today() - timedelta(days=2)
    data = []
    from_str = (to_date - timedelta(days=6)).strftime('%Y-%m-%d')
    to_str = to_date.strftime('%Y-%m-%d')
    time_range = '{} 到 {}'.format(from_str, to_str)
    logger.info('Send weekly stat of %s' % time_range)
    for app in model_manager.get_dist_apps():
        best = '''
        select a.`title`, a.`category`, wx_user+qq_user as users, wx_pv+qq_pv as pv, 
        (`wx_user` + qq_user) / (`wx_pv`+qq_pv) as rate from backend_distarticlestat s, backend_distarticle a
        where s.article_id=a.id and a.`last_started_at` between current_date - interval 8 day 
        and current_date - interval 1 day
        and a.app_id={} and `wx_user` + qq_user > 10
        order by users desc limit 10
        '''.format(app.app_id)

        worst = '''
        select a.`title`, a.`category`, wx_user+qq_user as users, wx_pv+qq_pv as pv, 
        (`wx_user` + qq_user) / (`wx_pv`+qq_pv) as rate from backend_distarticlestat s, backend_distarticle a
        where s.article_id=a.id and a.`last_started_at` between current_date - interval 8 day 
        and current_date - interval 1 day
        and a.app_id={} and `wx_user` + qq_user < 5
        order by pv desc limit 10
        '''.format(app.app_id)
        # best_articles = list()
        with connection.cursor() as cursor:
            cursor.execute(best)
            rows = cursor.fetchall()
            best_articles = [{
                'title': r[0],
                'category': r[1],
                'users': r[2],
                'pv': r[3],
                'rate': r[4]
            } for r in rows]

            cursor.execute(worst)
            rows = cursor.fetchall()
            worst_articles = [{
                'title': r[0],
                'category': r[1],
                'users': r[2],
                'pv': r[3],
                'rate': r[4]
            } for r in rows]

        st = AppWeeklyStat.objects.filter(app_id=app.app_id, stat_date=time_range).first()

        data.append({
            'name': app.app_name,
            'stats': classify_data_app(app),
            'best': best_articles,
            'worst': worst_articles,
            'stat': st,
        })
    html = render_to_string('article_weekly_report.html', {'stats': data})

    api_helper.send_html_mail('{}分发周报'.format(time_range), settings.DAILY_REPORT_EMAIL, html)


def echo(word):
    print('%s at %s' % (word, datetime.now()))


def reload_phone_task(task_id):
    for device_task in SnsTaskDevice.objects.filter(task_id=task_id).select_related('device'):
        from backend import task_manager
        task_manager.reload_next_task(device_task.device.label)


R = 6373.0


def merge_loc(arr, src=list()):
    for loc1 in arr:
        done = False
        for x in src:
            if distance(loc1, x) < 5:
                x['count'] += 1
                done = True

        if not done:
            src.append(loc1)

    return src


def distance(loc1, loc2):
    lat1 = radians(float(loc1['lat']))
    lon1 = radians(float(loc1['lng']))
    lat2 = radians(float(loc2['lat']))
    lon2 = radians(float(loc2['lng']))

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def upload_to_qn(file, key):
    q = Auth(settings.QINIU_AK, settings.QINIU_SK)
    token = q.upload_token(settings.QINIU_BUCKET, key)
    put_file(token, key, file)


def send_report():
    for app in App.objects.filter(offline=1):
        pass
