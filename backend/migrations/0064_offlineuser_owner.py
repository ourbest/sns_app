# Generated by Django 2.0 on 2018-04-08 03:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0063_snsgroup_apply_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='offlineuser',
            name='owner',
            field=models.BigIntegerField(default=0, verbose_name='扫描人'),
        ),
    ]
