# Generated by Django 2.0 on 2018-03-23 11:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0054_auto_20180322_1027'),
    ]

    operations = [
        migrations.CreateModel(
            name='WeizhanItemView',
            fields=[
                ('viewId', models.BigIntegerField(primary_key=True, serialize=False)),
                ('itemType', models.CharField(max_length=20)),
                ('ua', models.CharField(max_length=255)),
                ('itemId', models.BigIntegerField()),
                ('shareUserId', models.BigIntegerField()),
                ('partnerId', models.IntegerField()),
                ('time', models.DateTimeField()),
            ],
            options={
                'managed': False,
                'db_table': 'datasystem_WeizhanItemView',
            },
        ),
        migrations.CreateModel(
            name='ArticleDailyInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stat_date', models.CharField(max_length=15, verbose_name='统计日期')),
                ('item_id', models.BigIntegerField(verbose_name='分发的文章')),
                ('majia_id', models.BigIntegerField(verbose_name='分发马甲')),
                ('majia_type', models.IntegerField(default=0)),
                ('pv', models.IntegerField(default=0)),
                ('uv', models.IntegerField(default=0)),
                ('reshare', models.IntegerField(default=0)),
                ('down', models.IntegerField(default=0, verbose_name='下载页')),
                ('mobile_pv', models.IntegerField(default=0)),
                ('query_time', models.DateTimeField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.App')),
            ],
        ),
        migrations.CreateModel(
            name='RuntimeData',
            fields=[
                ('name', models.CharField(max_length=20, primary_key=True, serialize=False)),
                ('value', models.CharField(max_length=255)),
            ],
        ),
    ]
