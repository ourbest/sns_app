from django.db import models
from django.db.models import CASCADE
import datetime
from backend.models import App
from backend.models import App, PhoneDevice, SnsTaskType, User, SnsUser


class Area(models.Model):
    shq_id = models.IntegerField('生活圈ID')
    area = models.CharField('地区名', max_length=32)
    created_time = models.DateTimeField('创建时间', auto_now_add=True)
    app = models.ForeignKey(App, on_delete=CASCADE)
    isDelete = models.BooleanField('是否删除', default=False)

    def __str__(self):
        return '%s(%s)' % (self.area, self.app_id)


class Keyword(models.Model):
    """
    搜索功能的关键词库
    """
    keyword = models.CharField('搜群关键词', max_length=255)
    created_time = models.DateTimeField('创建时间', auto_now_add=True)
    isDelete = models.BooleanField('是否删除', default=False)

    def __str__(self):
        return self.keyword


class Search(models.Model):
    """
    搜索时实际使用的词条
    """
    word = models.CharField('搜索词', max_length=255)
    group_increment = models.IntegerField('群增量', default=0)
    group_user_increment = models.IntegerField('群人数增量', default=0)
    search_count = models.IntegerField('搜索次数', default=0)
    status = models.IntegerField('状态', default=0, help_text='0 - 使用中 1 - 已禁用')
    last_time = models.DateTimeField('最近一次的搜索时间', null=True, blank=True)
    area = models.ForeignKey(Area, on_delete=CASCADE)
    keyword = models.ForeignKey(Keyword, on_delete=CASCADE)

    def __str__(self):
        return self.word


class ScheduledTasks(models.Model):
    """
    一天：计划的任务
    临时的任务列表
    """
    device = models.ForeignKey(PhoneDevice, verbose_name='设备', on_delete=models.CASCADE)
    type = models.ForeignKey(SnsTaskType, verbose_name='任务类型', on_delete=models.CASCADE)
    estimated_start_time = models.DateTimeField('预计执行时间', null=True, blank=True)
    sns_user = models.ForeignKey(SnsUser, verbose_name='帐号', null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return '<%s,%s,%s>' % (self.estimated_start_time.strftime('%H:%M'), self.device.phone_num, self.type.name)


class TaskLog(models.Model):
    """
    实际的任务列表
    """
    device = models.ForeignKey(PhoneDevice, on_delete=models.CASCADE)
    type = models.ForeignKey(SnsTaskType, on_delete=models.CASCADE)
    start_time = models.DateTimeField('开始时间', auto_now_add=True)
    sns_user = models.ForeignKey(SnsUser, null=True, blank=True, on_delete=models.CASCADE)

    finish_time = models.DateTimeField('完成时间', null=True, blank=True)
    status = models.IntegerField('状态', default=0, help_text='0 - 正在/继续执行，1 - 完成，-1 - 中断，-2 - 打断')
    result = models.CharField('结果', max_length=255, null=True, blank=True)

    def __str__(self):
        return '<%s,%s>' % (self.device.phone_num, self.type.name)


class Config(models.Model):
    """
    配置
    """
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    opening_time = models.TimeField('上班时间', default=datetime.time(8, 0, 0))
    closing_time = models.TimeField('下班时间', default=datetime.time(20, 0, 0))
    max_num_of_apply = models.IntegerField('最大加群数/天·QQ', default=3)
    shortest_interval_apply_of_device = models.IntegerField('设备的最短间隔加群', default=600)
    max_num_of_search = models.IntegerField('最大查群次数/天·设备', default=5)

    def __str__(self):
        return self.owner.name


class OperationDevice(models.Model):
    """
    设备操作记录
    """
    device = models.ForeignKey(PhoneDevice, on_delete=models.CASCADE)
    last_apply = models.DateTimeField('最近一次加群的时间', null=True, blank=True)
    today_search = models.IntegerField('今日查群次数', default=0)
    today_statistics = models.IntegerField('今日统计次数', default=0)


class OperationSnsUser(models.Model):
    """
    帐号操作记录
    """
    sns_user = models.ForeignKey(SnsUser, on_delete=models.CASCADE)
    today_apply = models.IntegerField('今日加群数', default=0)
