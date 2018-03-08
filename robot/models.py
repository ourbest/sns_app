from django.db import models
from django.db.models import CASCADE

from backend.models import App


class Area(models.Model):
    shq_id = models.IntegerField('生活圈ID')
    area = models.CharField('地区名', max_length=32)
    created_time = models.DateTimeField('创建时间', auto_now_add=True)
    app = models.ForeignKey(App, on_delete=CASCADE)
    isDelete = models.BooleanField('是否删除', default=False)


class Keyword(models.Model):
    """
    搜索功能的关键词库
    """
    keyword = models.CharField('搜群关键词', max_length=255)
    created_time = models.DateTimeField('创建时间', auto_now_add=True)
    isDelete = models.BooleanField('是否删除', default=False)


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
