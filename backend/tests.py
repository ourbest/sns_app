# Create your tests here.
import re
from collections import defaultdict
from datetime import datetime, timedelta
from time import sleep

from dj import times
from django.db import connections, connection
from django.db.models import Count, Sum, F
from django.utils import timezone
from django_rq import job
from .loggs import logger

import backend.daily_stat
import backend.dates
import backend.stat_utils
from backend import model_manager, api_helper, stats, zhiyue_models, zhiyue, remains, cassandras, dates
from backend.models import SnsGroupSplit, SnsGroup, SnsUser, SnsUserGroup, SnsTask, DistArticle, DistArticleStat, \
    ItemDeviceUser, App, AppDailyStat, User, UserDailyStat, OfflineUser, AppUser, UserDailyDeviceUser, PhoneDevice, \
    ChannelUser, ArticleDailyInfo
from backend.user_factory import sync_to_item_dev_user
from backend.zhiyue_models import DeviceUser, CouponInst, CouponLog, ZhiyueUser, AdminPartnerUser, WeizhanItemView


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


def remove_dup_split_data_all():
    splits = SnsGroupSplit.objects.filter(status=0, created_at__gt=timezone.now() - timedelta(days=7))
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


def correct_split():
    sql = """select s.id from backend_snsgroup g, backend_snsgroupsplit s, backend_phonedevice d, backend_user u
      where g.group_id = s.group_id
      and g.app_id != u.app_id
      and s.phone_id = d.id
      and u.id = d.owner_id
      and u.app_id > 1000
      and s.status in (0,1)"""

    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
        for row in rows:
            SnsGroupSplit.objects.filter(pk=row[0]).delete()
            print('delete ', row[0])


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
        backend.daily_stat.make_daily_remain(app.app_id, date)


def sync_all_device_user(date):
    from_date = dates.get_date(date)
    create_range = (from_date, from_date + timedelta(days=1))
    majias = {x.cutt_user_id: x for x in AppUser.objects.filter(type__in=(0, 1))}
    for app in model_manager.get_dist_apps():
        saved = {x.user_id for x in ItemDeviceUser.objects.filter(app=app, created_at__range=create_range)}
        for device_user in model_manager.query(DeviceUser).filter(sourceUserId__in=majias.keys(),
                                                                  partnerId=app.app_id,
                                                                  createTime__range=create_range):
            if device_user.deviceUserId not in saved:
                majia = majias.get(device_user.sourceUserId)
                owner = majia.user
                model_manager.save_ignore(sync_to_item_dev_user(app, owner, device_user, majia))
                found = True
                print('Find %s' % device_user.deviceUserId)


def sync_device_user(date):
    logger.info('同步用户数据')
    from_date = dates.get_date(date)
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

    # if found:
    #     zhiyue.sync_online_from_hive(date)


def sync_bonus_test():
    date = backend.dates.today() - timedelta(days=5)
    for app in App.objects.filter(offline=1):
        users = OfflineUser.objects.filter(app=app, created_at__gt=date)
        backend.daily_stat.save_bonus_info(app, users, until=date)


def sync_user_stat(date):
    from_date = backend.dates.get_date(date)

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
        for val in DeviceUser.objects.using('zhiyue_rw').filter(createTime__gt=backend.dates.today(),
                                                                sourceUserId__gt=0).values(
            'sourceUserId', 'partnerId').annotate(total=Count('deviceUserId')):
            query = 'update datasystem_HighValueUser set appUserNum=%s where userId=%s and partnerId=%s ' \
                    'and time=\'%s\' and userType=2' % \
                    (val['total'], val['sourceUserId'], val['partnerId'], '2018-04-17')

            print(query)
            cursor.execute(query)


# def sync_zhongshan_offline():
#     from_dt = model_manager.today() - timedelta(days=31)
#     for x in range(0, 100):
#         from_dt = from_dt + timedelta(days=1)
#         if from_dt > model_manager.today() - timedelta(days=2):
#             break
#
#         date_range = (model_manager.get_date(from_dt), model_manager.get_date(from_dt + timedelta(days=1)))
#
#         date_users = OfflineUser.objects.filter(app_id=1564460, created_at__range=date_range)
#         print("sync", date_range, len(date_users))
#
#         if len(date_users):
#             users = {x.user_id: x for x in date_users}
#             remain_ids = remains.get_remain_ids(1564460, list(users.keys()),
#                               from_dt + timedelta(days=1), device=False)
#             print('remain ', len(remain_ids))
#             OfflineUser.objects.filter(user_id__in=remain_ids).update(remain=1)


def sync_zhongshan_online():
    from_dt = backend.dates.today() - timedelta(days=31)
    for app in [1564467, 1564465, 1564471]:
        remains.remain_week_online(app_id=app, date_range=(from_dt, backend.dates.today() - timedelta(days=2)))


def sync_zhongshan_offline():
    from_dt = backend.dates.today() - timedelta(days=31)
    for app in [1564462, 1564463, 1564467, 1564465, 1564471]:
        remains.remain_week_offline(app_id=app, date_range=(from_dt, backend.dates.today() - timedelta(days=2)))


@job("default", timeout=3600 * 5)
def sync_all():
    sync_zhongshan_offline()
    sync_zhongshan_online()


def sync_title():
    for x in DistArticle.objects.filter(title=''):
        x.title = zhiyue_models.get_article_title(x.item_id)
        model_manager.save_ignore(x, fields=['title'])


def import_test():
    reg = r'(.+)\t\((\d+)\)$'
    groups = list()
    with open('tmp/a.txt', 'r') as lines:
        for line in lines:
            match = re.match(reg, line)
            if match:
                (name, cnt) = match.groups()
                i = int(cnt)
                if i:
                    groups.append([name, i])

    model_manager.sync_wx_groups_imports(PhoneDevice.objects.filter(id=430).first(), groups)


def sync_rizhao():
    coupons = model_manager.query(CouponInst).filter(partnerId=1564469, useDate__range=('2018-04-26', '2018-04-28'))
    print('Total ', len(coupons))
    zhiyue.save_coupon_user(coupons)


def sync_rizhao_off(app_id=1564450):
    offline_users = remains.classify_users(OfflineUser.objects.filter(app_id=app_id))
    for k, v in offline_users.items():
        users = {x.user_id: x for x in v}
        remain_ids = remains.get_remain_ids(app_id, list(users.keys()), k + timedelta(days=1),
                                            device=False)
        OfflineUser.objects.filter(user_id__in=remain_ids).update(remain=1)
        remain_ids = remains.get_remain_ids(app_id, list(users.keys()), k + timedelta(days=7),
                                            device=False)
        OfflineUser.objects.filter(user_id__in=remain_ids).update(remain_7=1)
        remain_ids = remains.get_remain_ids(app_id, list(users.keys()), k + timedelta(days=8),
                                            to_date=k + timedelta(days=14),
                                            device=False)
        OfflineUser.objects.filter(user_id__in=remain_ids).update(remain_14=1)


def check_cassandra(app_id):
    cql = 'insert into cassandra_onlineuser (partnerId, userId, onlinedate, firstup) values (%s,%s,%s,%s) if not exists'
    query = 'select userId from cassandra_onlineuser where partnerId=%s and userId=%s and onlinedate=%s'

    session = cassandras.get_session()

    cnt = 0
    for x in model_manager.query(ZhiyueUser).filter(
            appId=app_id, createTime__gt=dates.today()).order_by('-lastActiveTime')[0:300]:
        rows = session.execute(query, (int(x.appId), x.userId, x.createTime.strftime('%Y-%m-%d')))
        one = rows.one()
        if not one:
            rows = session.execute(cql, (int(x.appId), x.userId, x.createTime.strftime('%Y-%m-%d'), x.createTime))
            r = rows.one()
            if r.applied:
                cnt += 1
                print(app_id, x.userId)

    print(app_id, cnt)


def get_remain_time(app_id):
    do_get_remain_time(OfflineUser, app_id)
    do_get_remain_time(ItemDeviceUser, app_id)
    do_get_remain_time(ChannelUser, app_id)


def do_get_remain_time(obj, app_id):
    yesterday = dates.yesterday() - timedelta(2)
    user_ids = [x.user_id for x in obj.objects.filter(app_id=app_id, remain=1,
                                                      created_at__range=(yesterday, yesterday + timedelta(1)))]
    before_10 = 0
    after_10 = 0
    for k, v in cassandras.get_online_time(app_id, user_ids, yesterday + timedelta(1)).items():
        if times.localtime(v).hour < 9:
            before_10 += 1
        else:
            after_10 += 1

    if user_ids:
        print(before_10, after_10, before_10 / len(user_ids))


def sync_old_device_user():
    for x in ItemDeviceUser.objects.filter(pk__lt=116823):
        zu = model_manager.query(ZhiyueUser).filter(userId=x.user_id).first()
        if zu and zu.platform == 'iphone':
            x.platform = 'iphone'
            x.save(update_fields=['platform'])


def get_article_daily_stat():
    sql = """
        select * from backend_articledailyinfo d, backend_distarticle da where
        d.item_id = da.item_id where stat_date=current_date() - interval 1 day 
        """


def sync_app_user_app_id():
    for x in AppUser.objects.select_related('user').all():
        x.app = x.user.app
        x.save()


def sync_partner_admin_user():
    for x in AppUser.objects.select_related('user').all():
        db = model_manager.query(AdminPartnerUser).filter(loginUser=x.user.email, user_id=x.user_id).first()
        if db and db.partnerId != x.app_id:
            x.app_id = db.partnerId
            x.save(update_fields=['app_id'])


def sync_groups():
    select = 'select group_id from saved_group'
    with connection.cursor() as cursor:
        cursor.execute(select)
        rows = cursor.fetchall()
        for row in rows:
            group = SnsGroup.objects.filter(group_id=row[0]).first()
            if group and group.status == 1:
                group.status = 0
                model_manager.save_ignore(group)


def sync_pv(ids):
    last_id = 0
    size = 10000
    while size == 10000:
        stat_date = dates.today().strftime('%Y-%m-%d')
        data = {'%s_%s' % (x.item_id, x.majia_id): x for x in ArticleDailyInfo.objects.filter(stat_date=stat_date)}
        majia_dict = {x.cutt_user_id: x for x in AppUser.objects.all()}

        values = model_manager.query(WeizhanItemView).filter(pk__gt=last_id,
                                                             time__gt=dates.today(),
                                                             time__lt=dates.today() + timedelta(hours=9)).order_by(
            'pk')[0:10000]
        for item in values:
            last_id = item.viewId
            if item.itemId and item.itemId in ids and item.shareUserId and item.shareUserId in majia_dict:
                key = '%s_%s' % (item.itemId, item.shareUserId)
                if key not in data:
                    data[key] = ArticleDailyInfo(item_id=item.itemId,
                                                 app_id=item.partnerId,
                                                 majia_id=item.shareUserId,
                                                 user=majia_dict[item.shareUserId].user,
                                                 majia_type=majia_dict[item.shareUserId].type,
                                                 stat_date=stat_date)
                value = data[key]

                ua = item.ua.lower()
                if item.itemType in ('article', 'articlea', 'articleb'):
                    value.pv += 1
                    if 'android' in ua or 'iphone' in ua:
                        value.mobile_pv += 1
                        if 'android' in ua:
                            value.android_pv += 1
                        else:
                            value.iphone_pv += 1
                elif item.itemType.endswith('-down') or item.itemType.endswith('-mochuang'):
                    value.down += 1
                    if 'android' in ua:
                        value.android_down += 1
                    elif 'iphone' in ua:
                        value.iphone_down += 1
                elif item.itemType.endswith('-reshare'):
                    value.reshare += 1
        size = len(values)
        print('sync %s values' % size)
