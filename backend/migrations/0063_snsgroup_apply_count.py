# Generated by Django 2.0 on 2018-04-08 03:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0062_kpiperiod_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='snsgroup',
            name='apply_count',
            field=models.IntegerField(default=0, verbose_name='申请次数'),
        ),
    ]