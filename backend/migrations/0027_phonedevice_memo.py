# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-10-11 09:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0026_auto_20171010_1753'),
    ]

    operations = [
        migrations.AddField(
            model_name='phonedevice',
            name='memo',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='备注'),
        ),
    ]