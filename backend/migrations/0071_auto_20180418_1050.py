# Generated by Django 2.0 on 2018-04-18 02:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0070_offlineuser_bonus_view'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='withdrawapply',
            options={'managed': False},
        ),
        migrations.AddField(
            model_name='offlineuser',
            name='remain_14',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='offlineuser',
            name='remain_30',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='offlineuser',
            name='remain_7',
            field=models.IntegerField(default=0),
        ),
    ]
