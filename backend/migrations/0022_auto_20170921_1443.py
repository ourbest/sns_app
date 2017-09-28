# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-21 06:43
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0021_auto_20170921_1225'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.SnsGroup')),
                ('sns_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.SnsUser')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.SnsTask')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='taskgroup',
            unique_together=set([('task', 'group')]),
        ),
    ]