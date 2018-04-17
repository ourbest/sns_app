# Create your tests here.
from collections import defaultdict
from datetime import datetime, timedelta
from time import sleep

from dj import times
from django.db import connections
from django.db.models import Count, Sum
from django.utils import timezone
from django_rq import job
from logzero import logger

import backend.stat_utils
from backend import model_manager, api_helper, stats, zhiyue_models, zhiyue
from backend.models import SnsGroupSplit, SnsGroup, SnsUser, SnsUserGroup, SnsTask, DistArticle, DistArticleStat, \
    ItemDeviceUser, App, AppDailyStat, User, UserDailyStat, OfflineUser, AppUser, UserDailyDeviceUser
from backend.zhiyue import sync_to_item_dev_user
from backend.zhiyue_models import DeviceUser, CouponInst, CouponLog


def clean_finished():
    SnsTask.objects.filter()
    pass


def clean_split_data():
    splits = SnsGroupSplit.objects.filter(status=0)
    done = set()
    for x in splits:
        if not done.add(x.group_id):
            x.delete()


def sync_task():
    for task in SnsTask.objects.filter(article__isnull=True, type_id__in=(3, 5), started_at__isnull=False):
        print('check ' + task.data)
        item_id = api_helper.parse_item_id(task.data)
        print('is item id %s ' % item_id)

        api_helper.parse_dist_article(task.data, task, from_time=task.started_at)
        print('after %s' % task.article)


def do_sync_articles():
    for article in DistArticle.objects.filter(started_at__lt='2017-12-14', started_at__gt='2017-12-09'):
        f = article.snstask_set.first()
        if f.started_at != article.started_at:
            article.started_at = f.started_at
            article.save()


def remove_dup_split_data():
    splits = SnsGroupSplit.objects.filter(status__in=(0, 1, 2), user__app__stage='准备期').order_by("-status")
    done = set()
    for x in splits:
        if x.group_id not in done:
            done.add(x.group_id)
        else:
            x.delete()
            print('delete %s' % x.group_id)


def clean_split_data_1(status=1):
    splits = SnsGroupSplit.objects.filter(status=status)
    done = set()
    for x in splits:
        size = len(done)
        done.add(x.group_id)
        if len(done) == size:
            x.delete()


def sync_split():
    groups = SnsGroup.objects.filter(status=0)
    for group in groups:
        if group.snsusergroup_set.filter(status=0).count() > 0:
            try:
                group.status = 2
                group.save()
                print("%s changed to used" % group)
            except:
                pass

    groups = SnsGroup.objects.filter(status=1)
    for group in groups:
        if group.snsgroupsplit_set.count() == 0 and group.snsusergroup_set.count() == 0:
            try:
                group.status = 0
                group.save()
                print("%s changed" % group)
            except:
                pass

    groups = SnsGroup.objects.filter(status=2)
    for group in groups:
        if group.snsgroupsplit_set.filter(status=3).count() == 0 and \
                group.snsusergroup_set.filter(status=0).count() == 0:
            try:
                group.status = 0
                group.save()
                print("%s changed" % group)
            except:
                pass


def remove_dup_ids():
    with open('data/ids.txt', 'rt') as file:
        qun_ids = set()
        for line in file:
            qun = line.split('\t')[0]
            if qun:
                qun_ids.add(qun)

        qun_ids_done = set()
        for row in SnsGroupSplit.objects.filter(user_id=13, group_id__in=qun_ids):
            if row.group_id not in qun_ids_done:
                qun_ids_done.add(row.group_id)
            else:
                row.delete()


def extract_all_items():
    done = set()
    for task in SnsTask.objects.filter(type__in=(3, 5)):
        the_id = api_helper.parse_item_id(task.data)
        if the_id and the_id not in done:
            try:
                std = task.snstaskdevice_set.filter(started_at__isnull=False).order_by('started_at').first()
                done.add(the_id)
                if std:
                    DistArticle(item_id=the_id, app_id=std.device.owner.app_id,
                                started_at=std.started_at, created_at=std.started_at,
                                title=zhiyue_models.get_article_title(the_id)).save()
            except:
                logger.warning('error saving dist item %s' % the_id, exc_info=1)

    pass


def make_stats():
    for item in DistArticle.objects.all():  # filter(created_at__gte=timezone.now() - timedelta(days=3)):
        # qq_stat = stats.get_item_stat(item.app_id, item.item_id, item.started_at)
        wx_stat = backend.stat_utils.get_item_stat(item.app_id, item.item_id, item.started_at, user_type=1)

        db = DistArticleStat.objects.filter(article=item).first()
        if not db:
            db = DistArticleStat(article=item)

        # db.qq_pv = qq_stat.get('weizhan')
        # db.qq_down = qq_stat.get('download')
        # db.qq_user = qq_stat.get('users')

        db.wx_pv = wx_stat.get('weizhan')
        db.wx_down = wx_stat.get('download')
        db.wx_user = wx_stat.get('users')

        db.save()
        print('stat %s' % item.item_id)
        sleep(1)


def import_qun_test(file):
    with open(file, 'rt', encoding='utf-8') as f:
        lines = f.read()
        login_user = model_manager.get_user('shida.wang@cutt.com')
        app = 1564450
        total = 0
        for line in lines.split('\n'):
            line = line.strip()
            if line:
                total += 1
                account = line.split('\t')  # re.split('\s+', line) ## 群名称有可能有空格
                try:
                    db = SnsGroup.objects.filter(group_id=account[0]).first()
                    if not db:
                        logger.info('找到了新群 %s' % line)
                        db = SnsGroup(group_id=account[0], group_name=account[1], type=0, app_id=app,
                                      group_user_count=account[2], created_at=timezone.now(), from_user=login_user)
                    db.group_name = account[1]
                    db.group_user_count = account[2]
                    db.save()

                    model_manager.process_tag(db)

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
                except:
                    logger.warning("error save %s" % line, exc_info=1)

        logger.info('共%s个新群' % total)


def sync_articles():
    for task in SnsTask.objects.filter(type_id__in=(3, 5), article_id__isnull=True, started_at__isnull=False):
        if task.type_id in (3, 5) and not task.article:
            api_helper.parse_dist_article(task.data, task, task.started_at or task.schedule_at or task.created_at)


@job
def test_job():
    print('ok')


def run():
    test_job.delay()


@job
def sync_location():
    for u in ItemDeviceUser.objects.filter(location=''):
        du = model_manager.query(DeviceUser).filter(deviceUserId=u.user_id).first()
        if du.location:
            u.location = du.location
            u.save()


def sync_offline_location():
    for u in OfflineUser.objects.filter(location=''):
        du = model_manager.query(CouponInst).filter(userId=u.user_id).first()
        if du:
            log = model_manager.query(CouponLog).filter(appId=du.partnerId, couponId=du.couponId,
                                                        num=du.couponNum, lbs__isnull=False).first()
            if log:
                u.location = log.lbs
                u.save()

        # if du and du.location:
        #     pass


def test_remain():
    logger.info('同步留存数据')
    to_time = datetime.now()
    to_time_str = to_time.strftime('%Y-%m-%d')
    from_time_str = (to_time - timedelta(days=1)).strftime('%Y-%m-%d')
    date_range = (from_time_str, to_time_str)
    create_range = ((to_time - timedelta(days=2)).strftime('%Y-%m-%d'), from_time_str)
    report_date = (to_time - timedelta(days=2)).strftime('%Y-%m-%d')  # 留存记录是针对前一天的
    for app in model_manager.get_dist_apps():
        for user in User.objects.filter(app=app, status=0):
            qq_cnt = ItemDeviceUser.objects.filter(type=0, owner=user, created_at__range=create_range).count()
            wx_cnt = ItemDeviceUser.objects.filter(type=1, owner=user, created_at__range=create_range).count()
            UserDailyStat.objects.filter(report_date=report_date, user=user).update(
                qq_remain=qq_cnt, wx_remain=wx_cnt)


def sync_remain_days():
    today = datetime.now()
    for days in range(1, 10):
        date = (today - timedelta(days=days)).strftime('%Y-%m-%d')
        print(date)
        zhiyue.sync_remain_at(date)


def sync_user():
    for x in OfflineUser.objects.filter(owner=0):
        db = model_manager.query(CouponInst).filter(userId=x.user_id).first()
        x.owner = db.shopOwner
        x.save(update_fields=['owner'])


def clear_app_splitter(app_id):
    SnsGroupSplit.objects.filter(group__app_id=app_id, status=0).delete()


def delete_user_splitter(app_id, user_id):
    SnsGroupSplit.objects.filter(group__app_id=app_id, user_id=user_id, status=0).delete()


def sync_majia_user_id():
    for du in ItemDeviceUser.objects.filter(cutt_user_id=0):
        ct = model_manager.query(DeviceUser).filter(deviceUserId=du.user_id).first()
        du.cutt_user_id = ct.sourceUserId
        model_manager.save_ignore(du)


def sync_all_remain(date=None):
    # for x in range(8, 8):
    date = '2018-04-08' if not date else date
    for app in model_manager.get_dist_apps():
        zhiyue.make_daily_remain(app.app_id, date)


def sync_device_user(date):
    logger.info('同步用户数据')
    from_date = model_manager.get_date(date)
    create_range = (from_date, from_date + timedelta(days=1))
    found = False
    for app in model_manager.get_dist_apps():
        majias = {x.cutt_user_id: x for x in AppUser.objects.filter(type__in=(0, 1), user__app=app, user__status=0)}
        if majias:
            saved = {x.user_id for x in ItemDeviceUser.objects.filter(app=app, created_at__range=create_range)}
            for device_user in model_manager.query(DeviceUser).filter(sourceUserId__in=majias.keys(),
                                                                      createTime__range=create_range):
                if device_user.deviceUserId not in saved:
                    majia = majias.get(device_user.sourceUserId)
                    owner = majia.user
                    model_manager.save_ignore(sync_to_item_dev_user(app, owner, device_user, majia))
                    found = True
                    print('Find %s' % device_user.deviceUserId)

    if found:
        zhiyue.sync_online_from_hive(date)


def sync_bonus_test():
    date = model_manager.today() - timedelta(days=5)
    for app in App.objects.filter(offline=1):
        users = OfflineUser.objects.filter(app=app, created_at__gt=date)
        zhiyue.save_bonus_info(app, users, until=date)


def sync_user_stat(date):
    from_date = model_manager.get_date(date)

    reports = {x.user_id: x for x in UserDailyStat.objects.filter(report_date=from_date.strftime('%Y-%m-%d'))}
    changed = set()

    for x in ItemDeviceUser.objects.filter(created_at__range=(from_date, from_date + timedelta(days=1))).values(
            'owner_id', 'type').annotate(total=Count('user_id'), remain=Sum('remain')):
        if x['owner_id'] in reports:
            report = reports[x['owner_id']]
            the_type = x['type']
            if the_type == 0:
                if x['total'] > report.qq_install:
                    report.qq_install = x['total']
                    changed.add(report)

                if x['remain'] > report.qq_remain:
                    report.qq_remain = x['remain']
                    changed.add(report)
            elif the_type == 1:
                if x['total'] > report.wx_install:
                    report.wx_install = x['total']
                    changed.add(report)

                if x['remain'] > report.wx_remain:
                    report.wx_remain = x['remain']
                    changed.add(report)

    for x in changed:
        print('Save %s %s' % (x.app_id, x.user_id))
        x.save()


def sync_app_data(date):
    reports = {x.app_id: x for x in AppDailyStat.objects.filter(report_date=date)}
    changed = set()

    for x in UserDailyStat.objects.filter(report_date=date).values(
            'app_id').annotate(qq_install=Sum('qq_install'), qq_remain=Sum('qq_remain'),
                               wx_install=Sum('wx_install'), wx_remain=Sum('wx_remain')):
        report = reports[x['app_id']]
        if report.qq_remain < x['qq_remain']:
            report.qq_remain = x['qq_remain']
            changed.add(report)
        if report.wx_remain < x['wx_remain']:
            report.wx_remain = x['wx_remain']
            changed.add(report)
        if report.qq_install < x['qq_install']:
            report.qq_install = x['qq_install']
            changed.add(report)
        if report.wx_install < x['wx_install']:
            report.wx_install = x['wx_install']
            changed.add(report)

    for x in changed:
        print('Save %s' % x.app_id)
        x.save()


def sync_high_value_user():
    with connections['partner_rw'].cursor() as cursor:
        for val in DeviceUser.objects.using('zhiyue_rw').filter(createTime__gt=model_manager.today(),
                                                          sourceUserId__gt=0).values(
                'sourceUserId', 'partnerId').annotate(total=Count('deviceUserId')):
            query = 'update datasystem_HighValueUser set appUserNum=%s where userId=%s and partnerId=%s ' \
                    'and time=\'%s\' and userType=2' % \
                    (val['total'], val['sourceUserId'], val['partnerId'], '2018-04-17')

            print(query)
            cursor.execute(query)
