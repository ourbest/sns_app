# Generated by Django 2.0 on 2018-05-03 15:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0076_shareeventstat_shareuser'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShareRewardEvent',
            fields=[
                ('partnerId', models.BigIntegerField()),
                ('userId', models.BigIntegerField(primary_key=True, serialize=False)),
                ('createTime', models.DateTimeField()),
            ],
            options={
                'managed': False,
                'db_table': 'partner_ShareRewardEvent',
            },
        ),
        migrations.AddField(
            model_name='shareuser',
            name='enrolled',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='shareuser',
            name='referer_id',
            field=models.BigIntegerField(db_index=True, verbose_name='分享人'),
        ),
    ]
