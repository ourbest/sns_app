# Generated by Django 2.0 on 2018-04-09 13:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0065_auto_20180408_2021'),
    ]

    operations = [
        migrations.AddField(
            model_name='app',
            name='center',
            field=models.CharField(max_length=100, null=True, verbose_name='城市中心坐标'),
        ),
    ]
