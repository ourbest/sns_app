# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-21 04:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0020_snsgroup_quiz'),
    ]

    operations = [
        migrations.AddField(
            model_name='snsuser',
            name='dist',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='snsuser',
            name='friend',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='snsuser',
            name='search',
            field=models.IntegerField(default=0),
        ),
    ]
