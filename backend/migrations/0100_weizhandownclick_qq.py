# Generated by Django 2.0 on 2018-08-17 08:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0099_auto_20180817_1549'),
    ]

    operations = [
        migrations.AddField(
            model_name='weizhandownclick',
            name='qq',
            field=models.CharField(default='', max_length=10, null=True),
        ),
    ]
