# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-26 09:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0022_auto_20170921_1443'),
    ]

    operations = [
        migrations.AddField(
            model_name='snstask',
            name='schedule_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='snstaskdevice',
            name='schedule_at',
            field=models.DateTimeField(null=True),
        ),
    ]
