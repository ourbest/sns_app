# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-10-10 09:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0025_auto_20171009_1147'),
    ]

    operations = [
        migrations.AddField(
            model_name='snstaskdevice',
            name='progress',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='snsgroupsplit',
            name='status',
            field=models.IntegerField(default=0, help_text='0 默认 1 已发送 2 已申请 3 已通过 -1 忽略', verbose_name='状态'),
        ),
    ]
