# Generated by Django 2.0 on 2018-05-24 10:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0079_auto_20180524_1833'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemdeviceuser',
            name='platform',
            field=models.CharField(default='android', max_length=20, null=True),
        ),
    ]
