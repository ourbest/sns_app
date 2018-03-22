import os
import re
from collections import defaultdict
from datetime import timedelta

from django.utils import timezone
from django_rq import job
from logzero import logger

from backend import api_helper, model_manager, group_splitter
from backend.api_helper import ADD_STATUS, deal_add_result, deal_dist_result
from backend.model_manager import save_ignore
from backend.models import DeviceFile, SnsUser, SnsGroup, SnsUserGroup, SnsApplyTaskLog, SnsGroupSplit, WxDistLog, \
    SnsUserKickLog, DeviceTaskData


@job
def do_re_import(i_file_id):
    file = DeviceFile.objects.filter(id=i_file_id).first()
    if file:
        from backend.apis import _get_content
        text = _get_content(file.qiniu_key)
        file_name = '/data/tmp/tmp_%s.qn' % i_file_id
        with open(file_name, 'wt', encoding='utf-8') as out:
            out.write(text)

        _after_upload(file.device_task, file.device_task.id, file_name, file.device, file.type)

    return ''


@job
def _after_upload(device_task, task_id, tmp_file, device, file_type):
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
                for group in all_groups:
                    lost = 0
                    if group.sns_group_id not in all_group_ids:
                        # 被踢了
                        model_manager.set_qun_kicked(group)
                        lost += 1
                    logger.info("total lost %s", lost)

                    if lost:
                        model_manager.deal_kicked(device.owner)

    SnsGroupSplit.objects.filter(phone=device, status=1).update(status=0)
    SnsGroupSplit.objects.filter(phone=device, status=2, updated_at=timezone.now() - timedelta(days=2)).update(status=0)
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

                        SnsGroupSplit(group=qun, user=login_user, phone=device).save()

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
                    SnsGroupSplit(group=db, user=login_user, phone=device).save()
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
    for line in lines.split('\n'):
        match = re.match(reg, line)
        if match:
            (name, cnt) = match.groups()
            log = WxDistLog(task=device_task, group_name=name if len(name) < 100 else (name[0:90] + '...'),
                            user_count=cnt)
            log.save()

    model_manager.sync_wx_log(device_task)


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
