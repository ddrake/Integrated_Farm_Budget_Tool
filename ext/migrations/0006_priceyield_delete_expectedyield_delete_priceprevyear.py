# Generated by Django 4.2.1 on 2023-06-15 00:14

from django.db import migrations, models
import ext.models


class Migration(migrations.Migration):

    dependencies = [
        ('ext', '0005_expectedyield_price'),
    ]

    operations = [
        migrations.CreateModel(
            name='PriceYield',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state_id', models.SmallIntegerField()),
                ('county_code', models.SmallIntegerField()),
                ('crop_id', models.SmallIntegerField(db_column='commodity_id')),
                ('crop_type_id', models.SmallIntegerField(db_column='commodity_type_id')),
                ('practice', models.SmallIntegerField()),
                ('expected_yield', ext.models.SmallFloatField()),
                ('projected_price', ext.models.SmallFloatField()),
                ('price_volatility_factor', models.SmallIntegerField()),
                ('final_yield', ext.models.SmallFloatField()),
                ('harvest_price', ext.models.SmallFloatField()),
                ('crop_year', models.SmallIntegerField()),
                ('price_volatility_factor_prevyr', ext.models.SmallFloatField()),
            ],
            options={
                'db_table': 'ext_priceyield',
                'managed': False,
            },
        ),
        migrations.DeleteModel(
            name='ExpectedYield',
        ),
        migrations.DeleteModel(
            name='PricePrevyear',
        ),
    ]