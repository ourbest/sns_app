# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-10-17 06:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0029_snsapplytasklog_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='phone',
            field=models.CharField(blank=True, help_text='手机号', max_length=20, null=True),
        ),
    ]
