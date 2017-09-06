# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-31 07:56
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0005_auto_20170829_1815'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActiveDevice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active_at', models.DateTimeField(auto_now=True, verbose_name='最后上线时间')),
                ('status', models.IntegerField(default=0, help_text='0 - 正常， 1 - 工作中', verbose_name='状态')),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.PhoneDevice', verbose_name='设备')),
            ],
        ),
        migrations.CreateModel(
            name='DeviceFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qiniu_key', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('type', models.CharField(max_length=20)),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.PhoneDevice')),
            ],
        ),
        migrations.CreateModel(
            name='SnsTask',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('data', models.TextField(blank=True, null=True)),
                ('status', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='SnsTaskDevice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.IntegerField(default=0)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finish_at', models.DateTimeField(blank=True, null=True)),
                ('data', models.TextField(blank=True, null=True)),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.PhoneDevice')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.SnsTask')),
            ],
        ),
        migrations.CreateModel(
            name='SnsTaskType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=32)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddField(
            model_name='snstask',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.SnsTaskType'),
        ),
        migrations.AddField(
            model_name='devicefile',
            name='task',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.SnsTask'),
        ),
    ]