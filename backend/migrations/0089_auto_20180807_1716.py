# Generated by Django 2.0 on 2018-08-07 09:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0088_userauth'),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyDetailData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_id', models.BigIntegerField()),
                ('sns_type', models.IntegerField()),
                ('title', models.TextField(max_length=255)),
                ('category', models.CharField(max_length=10)),
                ('date', models.CharField(max_length=12)),
                ('total_user', models.IntegerField()),
                ('android_user', models.IntegerField()),
                ('iphone_user', models.IntegerField()),
                ('total_pv', models.IntegerField()),
                ('android_pv', models.IntegerField()),
                ('total_down', models.IntegerField()),
                ('iphone_down', models.IntegerField()),
                ('total_remain', models.IntegerField()),
                ('android_remain', models.IntegerField()),
                ('iphone_remain', models.IntegerField()),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.App')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='dailydetaildata',
            unique_together={('app', 'item_id', 'sns_type', 'date')},
        ),
    ]
