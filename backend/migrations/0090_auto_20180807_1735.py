# Generated by Django 2.0 on 2018-08-07 09:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0089_auto_20180807_1716'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailydetaildata',
            name='android_down',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='dailydetaildata',
            name='iphone_pv',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]