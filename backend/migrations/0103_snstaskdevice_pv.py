# Generated by Django 2.1 on 2018-09-02 12:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0102_auditimage_dingtalktoken_imageuploader_mpsentitem_partnerimage_userfollowapp'),
    ]

    operations = [
        migrations.AddField(
            model_name='snstaskdevice',
            name='pv',
            field=models.IntegerField(default=0, null=True, verbose_name='pv'),
        ),
    ]