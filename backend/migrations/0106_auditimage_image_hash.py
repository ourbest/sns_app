# Generated by Django 2.0 on 2018-09-10 14:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0105_auditimage_ua'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditimage',
            name='image_hash',
            field=models.CharField(db_index=True, default='', max_length=64),
        ),
    ]