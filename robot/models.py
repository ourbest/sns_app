import datetime

from django.db import models

from backend.models import App, PhoneDevice, SnsTaskType, User, SnsUser, SnsGroup
from robot.utils import tz


class Keyword(models.Model):
    keyword = models.CharField('关键词', max_length=255, primary_key=True)
    created_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.keyword


class Plan(models.Model):
    device = models.ForeignKey(PhoneDevice, on_delete=models.CASCADE)
    type = models.ForeignKey(SnsTaskType, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    sns_user = models.ForeignKey(SnsUser, null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return '%s %s' % (self.type.name, self.start_time.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'))


class Task(models.Model):
    device = models.ForeignKey(PhoneDevice, on_delete=models.CASCADE)
    type = models.ForeignKey(SnsTaskType, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    sns_user = models.ForeignKey(SnsUser, null=True, blank=True, on_delete=models.CASCADE)

    finish_time = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(default=0, help_text='0 - 正在/继续执行，1 - 完成，-1 - 中断，-2 - 打断')
    result = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return '%s %s' % (self.type.name, self.start_time.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'))


class Config(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, primary_key=True)
    from_time = models.TimeField(default=datetime.time(8, 0, 0))
    to_time = models.TimeField(default=datetime.time(20, 0, 0))
    apply_max = models.IntegerField(default=3)
    apply_interval = models.IntegerField(default=600)
    search_max = models.IntegerField(default=5)


class EventLog(models.Model):
    task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL)
    type = models.ForeignKey(SnsTaskType, on_delete=models.CASCADE)
    device = models.ForeignKey(PhoneDevice, null=True, on_delete=models.SET_NULL)
    sns_user = models.ForeignKey(SnsUser, null=True, blank=True, on_delete=models.SET_NULL)
    group = models.ForeignKey(SnsGroup, null=True, blank=True, on_delete=models.SET_NULL)
    created_time = models.DateTimeField(auto_now=True)
