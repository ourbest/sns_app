# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-21 03:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0019_auto_20170920_1643'),
    ]

    operations = [
        migrations.AddField(
            model_name='snsgroup',
            name='quiz',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='问题答案'),
        ),
    ]
