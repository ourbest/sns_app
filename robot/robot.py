import re
from datetime import timedelta, datetime
from random import choice, randint

from backend import api_helper
from backend.models import PhoneDevice
from backend import model_manager
from robot.models import Plan
from robot import models_manager
from robot.utils import tz, logger


class PlanManager:
    _OVERDUE = timedelta(minutes=1)

    def __init__(self, device: PhoneDevice):
        self.device = device

    def create_plans(self):
        logger.debug('create plans')

        producer = PlanProducer(self.device)
        producer.run()
        products = producer.get_products(order_by='start_time')

        return Plan.objects.bulk_create([
            Plan(device=x['device'],
                 type_id=x['type_id'],
                 start_time=x['start_time']
                 ) for x in products
        ])

    def refresh_plans(self):
        plans = models_manager.get_plans(self.device)
        if plans:
            if self._be_overdue(plans[0].start_time):
                self.delete_device_plans()
            else:
                return plans
        return self.create_plans()

    def get_executable_plan(self):
        plans = self.refresh_plans()
        if plans and datetime.now(tz) >= plans[0].start_time:
            return plans[0]

    def _be_overdue(self, dt):
        return datetime.now(tz) > dt + self._OVERDUE

    def delete_device_plans(self):
        return models_manager.delete_plans_by_device(self.device)


class PlanProducer:
    produce_apply = True
    produce_search = True
    produce_count = True

    def __init__(self, device: PhoneDevice):
        self.device = device
        self._products = []

    def __getattr__(self, item):
        if item == 'config':
            self.config = models_manager.get_config(self.device.owner)
        return self.__dict__[item]

    def get_products(self, order_by=None, reverse=False):
        val = self._products
        self._products = list()

        if order_by:
            val.sort(key=lambda dict_obj: dict_obj[order_by], reverse=reverse)

        return val

    def add_product(self, obj):
        self._products.append(obj)

    def _get_time_nodes(self):
        # 可用的时间范围
        now_time = datetime.now(tz)
        end_time = now_time.replace(hour=23, minute=59, second=59, microsecond=999999)

        # 加群的时间范围
        _from = self.config.from_time
        _to = self.config.to_time
        apply_from_time = now_time.replace(hour=_from.hour, minute=_from.minute, second=_from.second,
                                           microsecond=_from.microsecond)
        apply_to_time = now_time.replace(hour=_to.hour, minute=_to.minute, second=_to.second,
                                         microsecond=_to.microsecond)

        # 统计的时间范围
        count_from_time = now_time.replace(hour=0, minute=0, second=0, microsecond=0)
        count_to_time = now_time.replace(hour=4, minute=0, second=0, microsecond=0)

        return now_time, end_time, apply_from_time, apply_to_time, count_from_time, count_to_time

    def run(self):
        time_nodes = self._get_time_nodes()
        now_time, end_time, apply_from_time, apply_to_time, count_from_time, count_to_time = time_nodes

        apply_num = self._get_apply_num() if apply_to_time >= now_time else 0
        search_num = self._get_search_num()
        count_num = self._get_count_num() if count_to_time >= now_time else 0

        totals = apply_num + search_num + count_num
        if totals == 0:
            return

        # 规定各项任务占用时间
        apply_time = timedelta(minutes=5)
        search_time = timedelta(hours=1)
        count_time = timedelta(hours=3)

        # 每个任务之间的间隔时间
        interval = ((end_time - now_time) - (
                apply_num * apply_time + search_num * search_time + count_num * count_time)) / totals
        interval = interval if interval > timedelta(0) else timedelta(0)

        # 该设备上一次加群的时间（为严格控制设备加群的频率）
        last_apply_time = models_manager.get_last_apply_time(self.device) if apply_num > 0 else None

        # time_nodes排序
        sorted_time_nodes = sorted(time_nodes)

        # 第一个任务开始时间（额外加一点随机时间）
        start_time = now_time + timedelta(seconds=randint(0, int(interval.total_seconds())))

        while True:
            if start_time > end_time or apply_num + search_num + count_num <= 0:
                return

            # 加群任务仅添加在加群的时间范围内，其他任务也允许出现在这个时间范围内
            if apply_from_time <= start_time <= apply_to_time:
                x, y, z = apply_num, search_num, count_num
            else:
                x, y, z = 0, search_num, count_num

            # 统计任务仅添加在统计的时间范围内，其他任务仅允许在已添加统计任务或无统计任务后出现在这个时间范围内
            if count_from_time <= start_time <= count_to_time and count_num > 0:
                x, y, z = 0, 0, z
            else:
                x, y, z = x, y, 0

            select_list = [
                *['apply'] * x,
                *['search'] * y,
                *['count'] * z,
            ]
            try:
                select = choice(select_list)
            except IndexError:
                # len(select_list) == 0 抛错
                # 说明start_time在该时间上内没有任务可选，任务开始时间应跳到下一个时间节点或范围
                for tn in sorted_time_nodes:
                    # 如果start_time在一个时间节点上，加一秒跳入下一个时间范围
                    if start_time == tn:
                        start_time += timedelta(seconds=1)
                        break

                    # 如果start_time在一个时间范围内，跳到下一个时间节点上
                    elif start_time < tn:
                        start_time = tn
                        break

                # start_time大于任意time_node
                else:
                    return
            else:
                if select == 'apply':
                    apply_num -= 1
                    task_type = 2
                    invl = apply_time

                    if last_apply_time is not None and (start_time - last_apply_time) < timedelta(
                            seconds=self.config.apply_interval):
                        start_time = last_apply_time + timedelta(seconds=self.config.apply_interval)
                    last_apply_time = start_time

                elif select == 'search':
                    search_num -= 1
                    task_type = 1
                    invl = search_time

                elif select == 'count':
                    count_num -= 1
                    task_type = 4
                    invl = count_time

                else:
                    raise Exception

                self._add_product(task_type, start_time)

                start_time += interval + invl

    def _add_product(self, task_type, start_time):
        self.add_product({
            'device': self.device,
            'type_id': task_type,
            'start_time': start_time,
        })

    def _get_apply_num(self) -> int:
        if not self.produce_apply or self.config.apply_max <= 0:
            return 0

        qqs = models_manager.get_applicable_qqs(self.device)
        if not qqs:
            return 0

        applied_num = models_manager.get_applied_num_at_today(qqs)
        num = len(qqs) * self.config.apply_max - applied_num
        return num if num > 0 else 0

    def _get_search_num(self) -> int:
        if not self.produce_search or self.config.search_max <= 0:
            return 0

        searched_num = models_manager.get_searched_num_at_today(self.device)
        num = self.config.search_max - searched_num
        return num if num > 0 else 0

    def _get_count_num(self) -> int:
        if not self.produce_count:
            return 0

        counted_num = models_manager.get_counted_num_at_today(self.device)
        return 1 if counted_num == 0 else 0


class TaskManager:
    def __init__(self, task):
        self.task = task

    def create_content(self) -> str:
        data = self._get_task_data()
        if data is None:
            return 'no task data'

        content = '[task]\nid=%(id)s\ntype=%(type)s\n[data]' % \
                  {'id': self.task.pk, 'type': self.task.type_id}

        for key, val in data.items():
            if isinstance(val, list):
                for x in val:
                    content += '\n' + key + '=' + str(x)
            else:
                content += '\n' + key + '=' + str(val)

        return content

    def _get_task_data(self):
        task_type = self.task.type_id
        if task_type == 1:
            return self._get_search_data()
        elif task_type == 2:
            return self._get_apply_data()
        elif task_type == 4:
            return self._get_count_data()

    def _get_apply_data(self) -> dict or None:
        model_manager.reset_qun_status(device_task=None, device=self.task.device)

        qq = models_manager.get_applicable_qq(self.task.device_id)
        if not qq:
            self.set_error('未获取到可加群QQ')
            return

        self.set_sns_user(qq.login_name)

        groups = [x.group_id for x in model_manager.get_qun_idle(user=None, size=5, device=self.task.device)]
        if not groups:
            self.set_error('未获取到待加群')
            return

        return {'client': qq.provider, 'QQ_1': qq.login_name, 'QUN_1': groups}

    def _get_search_data(self) -> dict or None:
        keyword = models_manager.get_keyword(self.task.device.owner.app.app_name)
        if not keyword:
            self.set_error('未获取到关键词')
            return

        self.set_result('%s(0/0)' % keyword)
        return {'keyword': keyword}

    @staticmethod
    def _get_count_data() -> dict or None:
        return {}

    TASK_STATUS = ('finish', 'break', 'error')

    def handle_status(self, status, error_msg):
        if self.task.status == 0:
            if status == self.TASK_STATUS[0]:
                self.set_finish()
            elif status == self.TASK_STATUS[1]:
                self.set_break()
            elif status == self.TASK_STATUS[2]:
                self.set_error(error_msg)
            else:
                logger.warn('status=%s must be in %s' % (status, self.TASK_STATUS))

    def handle_result(self, result):
        task_type = self.task.type_id
        if task_type in (1, 2):
            pattern = re.compile(r'(\d+)\t(.+)\t(\d+)$')
        elif task_type == 4:
            pattern = re.compile(r'(\d+)\t(.+)\t(\d+)\t(\d+)$')
        else:
            logger.warn('task_type<%s> be not in [1, 2, 4]' % task_type)
            return

        ret = re.match(pattern, result)
        if not ret:
            logger.warn('正则失败<pattern:%s><result:%s>' % (repr(pattern.pattern), repr(result)))
            return

        if task_type == 1:
            group_id, group_name, group_user_count = ret.groups()
            self._handle_search_result(group_id, group_name, group_user_count)
        elif task_type == 2:
            group_id, apply_ret, qq_num = ret.groups()
            if apply_ret not in api_helper.ADD_STATUS:
                logger.warn('因加群结果"%s"不在%s内，所以加群结果未处理' % (apply_ret, api_helper.ADD_STATUS))
                return

            self._handle_apply_result(group_id, apply_ret, qq_num)
        elif task_type == 4:
            group_id, group_name, group_user_count, qq_num = ret.groups()
            self._handle_count_result(group_id, group_name, group_user_count, qq_num)

    def _handle_search_result(self, group_id, group_name, group_user_count):
        group = model_manager.get_qun(group_id)
        if not group:
            self.__set_search_result(group_user_count)

        user = self.task.device.owner
        app_id = user.app_id
        api_helper.save_group(group_id, group_name, group_user_count, app_id, user)

    def _handle_apply_result(self, group_id, apply_ret, qq_num):
        self.set_result('%s/%s' % (group_id, apply_ret))

        group = model_manager.get_qun(group_id)
        qq = model_manager.get_qq(qq_num)
        if not group or not qq:
            logger.debug('group:%s, qq:%s' % (group, qq))
            return

        model_manager.increase_apply_count(group)
        api_helper.deal_add_result(device_task=None, qq=qq, qun=group, status=apply_ret, device=self.task.device)

    def _handle_count_result(self, group_id, group_name, group_user_count, qq_num):
        api_helper.deal_count_result(group_id, group_name, group_user_count, qq_num, self.task.device)
        self.__set_count_result(group_user_count)

    def set_error(self, msg):
        self.task.status = -1
        self.task.result = msg
        self.task.save()

    def set_finish(self):
        self.task.status = 1
        self.task.finish_time = datetime.now(tz)
        self.task.save()

        models_manager.record_event(device_id=self.task.device_id, type_id=self.task.type_id, task_id=self.task.pk,
                                    sns_user_id=self.task.sns_user_id)

    def set_break(self):
        self.task.status = -2
        self.task.save()

    def set_sns_user(self, sns_user):
        self.task.sns_user = sns_user
        self.task.save()

    def set_result(self, ret):
        self.task.result = ret
        self.task.save()

    def __set_search_result(self, group_user_count):
        ret = re.match(r'(.+)\((\d+)/(\d+)\)$', self.task.result or '')
        if ret:
            keyword = ret.group(1)
            group_total = int(ret.group(2)) + 1
            user_total = int(ret.group(3)) + int(group_user_count)
            self.set_result('%s(%s/%s)' % (keyword, group_total, user_total))
        else:
            logger.warn("匹配结果不符合预期[%s]" % self.task.result)

    def __set_count_result(self, group_user_count):
        ret = re.match(r'(\d+)/(\d+)$', self.task.result or '')
        if ret:
            group_total, user_total = [int(x) for x in ret.groups()]
            group_total += 1
            user_total += int(group_user_count)
            self.set_result('%s/%s' % (group_total, user_total))
        else:
            self.set_result('0/0')


class Robot:
    _OVERDUE = timedelta(minutes=10)

    def __init__(self, device):
        self.device = device

    def get_task(self) -> str:
        task = self._get_task()
        if not task:
            return 'no task'

        return TaskManager(task).create_content()

    def _get_task(self):
        unfinished = models_manager.get_unfinished_task(self.device)
        if unfinished:
            if self._be_overdue(unfinished.start_time):
                TaskManager(unfinished).set_error('未执行超时')
                return self._get_task()
            else:
                return unfinished

        plan = PlanManager(self.device).get_executable_plan()
        return models_manager.plan_change_to_task(plan) if plan else None

    def _be_overdue(self, dt):
        return datetime.now(tz) > dt + self._OVERDUE
