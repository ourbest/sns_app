# Generated by Django 2.0 on 2018-04-20 10:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0074_offlinedailystat_user_cash_num'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChannelUser',
            fields=[
                ('user_id', models.BigIntegerField(primary_key=True, serialize=False)),
                ('channel', models.CharField(max_length=50)),
                ('created_at', models.DateTimeField()),
                ('remain', models.IntegerField(default=0)),
                ('ip', models.CharField(default='', max_length=20)),
                ('city', models.CharField(default='', max_length=50)),
                ('location', models.CharField(default='', max_length=100, null=True)),
                ('remain_7', models.IntegerField(default=0)),
                ('remain_14', models.IntegerField(default=0)),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.App')),
            ],
        ),
    ]
