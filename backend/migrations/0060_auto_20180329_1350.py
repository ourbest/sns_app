# Generated by Django 2.0 on 2018-03-29 05:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0059_offlineuser'),
    ]

    operations = [
        migrations.AddField(
            model_name='phonedevice',
            name='in_trusteeship',
            field=models.BooleanField(default=False, verbose_name='托管'),
        ),
        migrations.AlterField(
            model_name='offlineuser',
            name='remain',
            field=models.IntegerField(default=0),
        ),
    ]