# Generated by Django 2.0 on 2018-06-28 05:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0083_auto_20180531_1933'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomPush',
            fields=[
                ('pushId', models.IntegerField(primary_key=True, serialize=False)),
                ('partnerId', models.IntegerField()),
                ('pushDetail', models.CharField(max_length=255)),
                ('pushType', models.CharField(max_length=20)),
                ('itemId', models.BigIntegerField()),
                ('status', models.IntegerField()),
                ('createTime', models.DateTimeField()),
            ],
            options={
                'db_table': 'policy_CustomPush',
                'managed': False,
            },
        ),
    ]