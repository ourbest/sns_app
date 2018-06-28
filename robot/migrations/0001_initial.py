# Generated by Django 2.0 on 2018-06-28 06:10

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('backend', '0084_custompush'),
    ]

    operations = [
        migrations.CreateModel(
            name='Config',
            fields=[
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='backend.User')),
                ('from_time', models.TimeField(default=datetime.time(8, 0))),
                ('to_time', models.TimeField(default=datetime.time(20, 0))),
                ('apply_max', models.IntegerField(default=3)),
                ('apply_interval', models.IntegerField(default=600)),
                ('search_max', models.IntegerField(default=5)),
            ],
        ),
        migrations.CreateModel(
            name='EventLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_time', models.DateTimeField(auto_now=True)),
                ('device', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='backend.PhoneDevice')),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='backend.SnsGroup')),
                ('sns_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='backend.SnsUser')),
            ],
        ),
        migrations.CreateModel(
            name='Keyword',
            fields=[
                ('keyword', models.CharField(max_length=100, primary_key=True, serialize=False, verbose_name='关键词')),
                ('created_time', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Plan',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField()),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.PhoneDevice')),
                ('sns_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='backend.SnsUser')),
                ('type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.SnsTaskType')),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField(auto_now_add=True)),
                ('finish_time', models.DateTimeField(blank=True, null=True)),
                ('status', models.IntegerField(default=0, help_text='0 - 正在/继续执行，1 - 完成，-1 - 中断，-2 - 打断')),
                ('result', models.CharField(blank=True, max_length=255, null=True)),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.PhoneDevice')),
                ('sns_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='backend.SnsUser')),
                ('type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.SnsTaskType')),
            ],
        ),
        migrations.AddField(
            model_name='eventlog',
            name='task',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='robot.Task'),
        ),
        migrations.AddField(
            model_name='eventlog',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.SnsTaskType'),
        ),
    ]
