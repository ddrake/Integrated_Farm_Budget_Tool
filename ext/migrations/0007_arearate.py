# Generated by Django 4.2.1 on 2023-06-15 01:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ext', '0006_priceyield_delete_expectedyield_delete_priceprevyear'),
    ]

    operations = [
        migrations.CreateModel(
            name='AreaRate',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('state_id', models.SmallIntegerField()),
                ('county_code', models.SmallIntegerField()),
                ('crop_id', models.SmallIntegerField(db_column='commodity_id')),
                ('crop_type_id', models.SmallIntegerField(db_column='commodity_type_id')),
                ('practice', models.SmallIntegerField()),
                ('insurance_plan_id', models.SmallIntegerField()),
            ],
            options={
                'db_table': 'ext_arearate',
                'managed': False,
            },
        ),
    ]
