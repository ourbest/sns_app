# Generated by Django 2.0 on 2018-08-14 16:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0096_auto_20180814_2302'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='weizhanclick',
            unique_together={('item_id', 'uuid', 'uid', 'tid')},
        ),
        migrations.AlterUniqueTogether(
            name='weizhandownclick',
            unique_together={('item_id', 'type', 'tid', 'idx', 'uuid', 'uid', 'task_id')},
        ),
    ]
