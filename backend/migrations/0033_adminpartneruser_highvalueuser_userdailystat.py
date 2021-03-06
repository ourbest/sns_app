# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-10-24 07:52
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0032_auto_20171018_1521'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminPartnerUser',
            fields=[
                ('loginUser', models.CharField(max_length=255)),
                ('user', models.ForeignKey(db_column='userId', on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='backend.ZhiyueUser')),
                ('partnerId', models.IntegerField()),
            ],
            options={
                'managed': False,
                'db_table': 'partner_AdminPartnerUser',
            },
        ),
        migrations.CreateModel(
            name='HighValueUser',
            fields=[
                ('name', models.CharField(max_length=255)),
                ('userId', models.IntegerField(primary_key=True, serialize=False)),
                ('deviceUserId', models.IntegerField()),
                ('partnerId', models.IntegerField()),
                ('shareNum', models.IntegerField()),
                ('weizhanNum', models.IntegerField()),
                ('downPageNum', models.IntegerField()),
                ('appUserNum', models.IntegerField()),
                ('commentNum', models.IntegerField()),
                ('agreeNum', models.IntegerField()),
                ('viewNum', models.IntegerField()),
                ('secondShareNum', models.IntegerField()),
                ('userType', models.IntegerField(help_text='userType=1 内容产生用户 ，userType=2 内容传播用户')),
                ('time', models.DateTimeField()),
            ],
            options={
                'managed': False,
                'db_table': 'datasystem_HighValueUser',
            },
        ),
        migrations.CreateModel(
            name='UserDailyStat',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_date', models.CharField(max_length=20)),
                ('qq_pv', models.IntegerField()),
                ('wx_pv', models.IntegerField()),
                ('qq_down', models.IntegerField()),
                ('wx_down', models.IntegerField()),
                ('qq_install', models.IntegerField()),
                ('wx_install', models.IntegerField()),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.App')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.User')),
            ],
        ),
    ]
