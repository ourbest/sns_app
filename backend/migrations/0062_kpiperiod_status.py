# Generated by Django 2.0 on 2018-04-03 11:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0061_kpiperiod'),
    ]

    operations = [
        migrations.AddField(
            model_name='kpiperiod',
            name='status',
            field=models.IntegerField(default=0),
        ),
    ]