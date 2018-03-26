from backend.models import SnsUser, User, PhoneDevice
from robot.models import Config, ScheduledTasks
import datetime
from django.utils import timezone
import time
import random
from collections import Iterable

TASK_TIMEOUT = 600  # 秒
ENOUGH_TIME = 3600  # 秒
STATISTICS_TIME = 3 * 3600  # 秒


class Robot:
    def __init__(self, config: Config = None, user: User = None):
        self.config = config if config else Config.objects.get_or_create(owner=user)[0]
        self.user = user if user else self.config.owner

    @property
    def managed_devices(self):
        """被托管的设备"""
        return PhoneDevice.objects.filter(owner=self.user, status=0, in_trusteeship=True)

    def __may_apply_of_sns_user(self, device):
        """
        返回还能加群的帐号的查询集
        :param device: 要查询的设备
        :return:
        """
        return SnsUser.objects.filter(owner=self.user, friend=1, status=0, device=device,
                                      today_apply__lt=self.config.max_num_of_apply)

    def at_working_time(self):
        """判断是否在工作时间"""
        opening_time = self.config.opening_time
        closing_time = self.config.closing_time

        now = datetime.datetime.now()

        t1 = (now.hour - opening_time.hour) * 3600 + (now.minute - opening_time.minute) * 60 + (
                now.second - opening_time.second) * 1

        t2 = (closing_time.hour - now.hour) * 3600 + (closing_time.minute - now.minute) * 60 + (
                closing_time.second - now.second) * 1

        if t1 > 0 and t2 > 0:
            return True
        else:
            return False

    def remaining_working_time(self):
        """当日剩余工作时间，单位：秒"""
        now = datetime.datetime.now()

        opening_time = self.config.opening_time
        closing_time = self.config.closing_time

        running_time = (closing_time.hour - opening_time.hour) * 3600 + (
                closing_time.minute - opening_time.minute) * 60 + (
                               closing_time.second - opening_time.second) * 1

        t = (closing_time.hour - now.hour) * 3600 + (closing_time.minute - now.minute) * 60 + (
                closing_time.second - now.second) * 1

        if t > running_time:
            remaining_running_time = running_time
        elif 0 <= t <= running_time:
            remaining_running_time = t
        else:
            remaining_running_time = 0

        return remaining_running_time

    def __proper_interval(self, rrm, total):
        """
        :param rrm: 剩余工作时间
        :param total: 总任务数
        :return: (时间间隔,是否是最短间隔时间的布尔值)
        """
        interval = rrm // total
        shortest_interval = self.config.shortest_interval_apply_of_device
        interval_time = (interval, False) if interval >= shortest_interval else (shortest_interval, True)

        return interval_time

    def __just_create_secondary_task(self, device_queryset=None):
        """
        仅创建次要任务
        :param device_queryset: 需创建任务的设备的查询集，不传默认所有的托管设备
        :return:
        """
        now_split = [(datetime.datetime.now(), datetime.datetime.now().replace(hour=23, minute=59, second=59))]
        device_queryset = device_queryset if device_queryset else self.managed_devices
        if device_queryset:
            device_dict = {}
            for device in device_queryset:
                time_split = now_split.copy()
                task_list = []
                self.__join_statistics(time_split, task_list, device)
                self.__join_search(time_split, task_list, device)
                if task_list:
                    device_dict[device.id] = task_list

            if device_dict:
                return self.__bulk_save(device_dict)

    def create_scheduled_tasks(self, devices=None):
        """
        创建计划的任务
        """
        if devices and not isinstance(devices, Iterable):
            devices = [devices, ]

        rrm = self.remaining_working_time()
        if rrm <= 0:
            # 不在要求时间内就不在创建加群任务，仅去创建统计和查群任务
            return self.__just_create_secondary_task(device_queryset=devices)

        # 初始值
        max_num = self.config.max_num_of_apply
        at_working_time = self.at_working_time()
        if at_working_time:
            init_seconds = int(time.time())
        else:
            opening_time = self.config.opening_time
            init_seconds = int(time.mktime(datetime.datetime.now().replace(hour=opening_time.hour,
                                                                           minute=opening_time.minute,
                                                                           second=opening_time.second,
                                                                           ).timetuple()
                                           )
                               )
        shortest = self.config.shortest_interval_apply_of_device
        now = timezone.now()
        clt = self.config.closing_time
        closing_time = datetime.datetime.now().replace(hour=clt.hour, minute=clt.minute, second=clt.second,
                                                       microsecond=0)
        # 初始值

        device_dict = {}
        device_queryset = devices if devices else self.managed_devices
        for device in device_queryset:
            task_list = []
            sns_user_queryset = self.__may_apply_of_sns_user(device)
            if sns_user_queryset.exists():
                # 给任务加入序号
                x, y = 0, sns_user_queryset.count()
                for sns_user in sns_user_queryset:
                    order = x
                    for i in range(max_num - sns_user.today_apply):
                        task_list.append({
                            'sns_user_id': sns_user.id,
                            'type': 2,
                            'order': order
                        })
                        order += y
                    x += 1

                # 按order排序
                task_list.sort(key=lambda obj: obj['order'])

                # 加入预计时间
                before = device.last_apply
                if before:
                    time_diff = (now - before).total_seconds() - shortest
                else:
                    time_diff = 0

                seconds = 0 if time_diff >= 0 else abs(time_diff)

                interval = self.__proper_interval(rrm, len(task_list))
                if not interval[1]:
                    seconds = random.randint(*sorted([seconds, interval[0]]))

                time_split = []  # 时间切片

                for task in task_list:
                    task['time'] = datetime.datetime.fromtimestamp(init_seconds + seconds)

                    # 删除掉超过范围时间的加群任务
                    if task['time'] > closing_time:
                        del task_list[task_list.index(task):]
                        break

                    seconds += interval[0]

                    if not time_split:
                        time_split.append(
                            (datetime.datetime.now(), task['time'].replace(second=task['time'].second + 1)))
                    else:
                        time_split.append((time_split[-1][1], task['time'].replace(second=task['time'].second + 1)))

                time_split.append((time_split[-1][1], datetime.datetime.now().replace(hour=23, minute=59, second=59)))

            else:
                time_split = [(datetime.datetime.now(), datetime.datetime.now().replace(hour=23, minute=59, second=59))]
                task_list = []

            self.__join_statistics(time_split, task_list, device)
            self.__join_search(time_split, task_list, device)

            device_dict[device.id] = task_list

        return self.__bulk_save(device_dict)

    @staticmethod
    def __join_statistics(time_split, task_list, device: PhoneDevice):
        return None
        """插入统计任务"""
        if device.today_statistics >= 1:
            return None

        # 算出时间最大的切片
        max_t = 0
        i = 0
        for x in time_split:
            td = (x[1] - x[0]).total_seconds()
            if td > max_t:
                i = time_split.index(x)  # 索引
                max_t = td

        if max_t >= STATISTICS_TIME:
            t = datetime.datetime.fromtimestamp(
                time.mktime(time_split[i][0].timetuple()) + random.randint(0, int(max_t - STATISTICS_TIME)))

            time_split.insert(i + 1, (time_split[i][0], t))
            time_split.insert(i + 2, (
                datetime.datetime.fromtimestamp(time.mktime(t.timetuple()) + STATISTICS_TIME), time_split[i][1]))
            del time_split[i]

            arg = {
                'type': 4,
                'time': t,
                'sns_user_id': None,
            }
            if task_list:
                task_list.insert(i, arg)
            else:
                task_list.append(arg)

    def __join_search(self, time_split, task_list, device: PhoneDevice):
        """插入查群任务"""
        max_num = self.config.max_num_of_search
        num = device.today_search

        for x in time_split:
            if num >= max_num:
                break
            td = (x[1] - x[0]).total_seconds()
            if td >= ENOUGH_TIME:
                num += 1
                i = time_split.index(x)  # 索引位置
                rt = int(td - ENOUGH_TIME)
                rt = rt if rt < 300 else 300
                t = datetime.datetime.fromtimestamp(time.mktime(time_split[i][0].timetuple()) + random.randint(0, rt))

                time_split.insert(i + 1, (time_split[i][0], t))
                time_split.insert(i + 2, (
                    datetime.datetime.fromtimestamp(time.mktime(t.timetuple()) + ENOUGH_TIME), time_split[i][1]))
                del time_split[i]

                dic = {
                    'type': 1,
                    'time': t,
                    'sns_user_id': None,
                }
                if task_list:
                    task_list.insert(i, dic)
                else:
                    task_list.append(dic)

    @staticmethod
    def __bulk_save(device_dict):
        tasks = []
        for device_id, task_list in device_dict.items():
            for task in task_list:
                tasks.append(ScheduledTasks(
                    device_id=device_id,
                    type_id=task['type'],
                    estimated_start_time=task['time'] if timezone.is_aware(task['time']) else timezone.make_aware(
                        task['time']),
                    sns_user_id=task['sns_user_id'],
                ))

        return ScheduledTasks.objects.bulk_create(tasks)

    @staticmethod
    def clear():
        SnsUser.objects.exclude(today_apply=0).update(today_apply=0)
        PhoneDevice.objects.exclude(today_search=0).update(today_search=0)
        ScheduledTasks.objects.all().delete()

    @staticmethod
    def check_timeout(start_time):
        time_diff = (timezone.now() - start_time).total_seconds()
        if 0 <= time_diff <= TASK_TIMEOUT:
            return 1
        elif time_diff > TASK_TIMEOUT:
            return -1
        else:
            return 0

    def update_scheduled_tasks(self, device=None):
        if device:
            ScheduledTasks.objects.filter(device=device).delete()
        else:
            ScheduledTasks.objects.filter(device__owner=self.user).delete()
        return self.create_scheduled_tasks(devices=device)
