# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-20 08:43
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0018_auto_20170919_1637'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tag', models.CharField(max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.SnsGroup')),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('name', models.CharField(max_length=10, primary_key=True, serialize=False)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='grouptag',
            unique_together=set([('group', 'tag')]),
        ),
    ]