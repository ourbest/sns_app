# Generated by Django 2.0 on 2018-04-08 12:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0064_offlineuser_owner'),
    ]

    operations = [
        migrations.CreateModel(
            name='CouponLog',
            fields=[
                ('appId', models.IntegerField()),
                ('couponId', models.IntegerField()),
                ('num', models.CharField(max_length=10)),
                ('actionTime', models.DateTimeField(primary_key=True, serialize=False)),
                ('userId', models.BigIntegerField()),
                ('action', models.IntegerField()),
                ('lbs', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'partner_CouponLog',
                'managed': False,
            },
        ),
        migrations.AddField(
            model_name='itemdeviceuser',
            name='location',
            field=models.CharField(default='', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='offlineuser',
            name='location',
            field=models.CharField(default='', max_length=100, null=True),
        ),
    ]
