# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-10-12 09:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0027_phonedevice_memo'),
    ]

    operations = [
        migrations.AddField(
            model_name='app',
            name='self_qun',
            field=models.IntegerField(default=1, verbose_name='自行导入群'),
        ),
        migrations.AddField(
            model_name='app',
            name='stage',
            field=models.CharField(default='准备期', max_length=20, verbose_name='所处时期'),
        ),
    ]
