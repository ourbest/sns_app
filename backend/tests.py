# Create your tests here.
from datetime import timedelta
from time import sleep

from django.utils import timezone
from logzero import logger

from backend import model_manager, api_helper, stats, zhiyue_models
from backend.models import SnsGroupSplit, SnsGroup, SnsUser, SnsUserGroup, SnsTask, DistArticle, DistArticleStat


def clean_split_data():
    splits = SnsGroupSplit.objects.filter(status=0)
    done = set()
    for x in splits:
        if not done.add(x.group_id):
            x.delete()


def clean_split_data_1(status=1):
    splits = SnsGroupSplit.objects.filter(status=status)
    done = set()
    for x in splits:
        size = len(done)
        done.add(x.group_id)
        if len(done) == size:
            x.delete()


def sync_split():
    groups = SnsGroup.objects.filter(status=1, app_id=1519662)
    for group in groups:
        if group.snsgroupsplit_set.count() == 0 and group.snsusergroup_set.count() == 0:
            group.status = 0
            group.save()


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
    for item in DistArticle.objects.filter(created_at__gte=timezone.now() - timedelta(days=3)):
        qq_stat = stats.get_item_stat(item.app_id, item.item_id, item.started_at)
        wx_stat = stats.get_item_stat(item.app_id, item.item_id, item.started_at)

        db = DistArticleStat.objects.filter(article=item).first()
        if not db:
            db = DistArticleStat(article=item)

        db.qq_pv = qq_stat.get('weizhan')
        db.qq_down = qq_stat.get('download')
        db.qq_user = qq_stat.get('users')

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
