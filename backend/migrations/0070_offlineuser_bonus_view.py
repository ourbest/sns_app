# Generated by Django 2.0 on 2018-04-13 10:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0069_auto_20180413_1648'),
    ]

    operations = [
        migrations.AddField(
            model_name='offlineuser',
            name='bonus_view',
            field=models.IntegerField(default=0),
        ),
    ]