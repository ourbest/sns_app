# Generated by Django 2.0 on 2018-08-14 15:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0095_auto_20180814_2302'),
    ]

    operations = [
        migrations.AddField(
            model_name='weizhandownclick',
            name='task_id',
            field=models.IntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='weizhandownclick',
            name='tid',
            field=models.IntegerField(default=0),
        ),
    ]