# Generated by Django 4.2.1 on 2023-06-02 19:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0012_remove_farmcrop_cty_expected_yield_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='farmcrop',
            name='price_vol_factor',
        ),
        migrations.RemoveField(
            model_name='farmcrop',
            name='proj_harv_price',
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='building_depr',
            field=models.FloatField(default=0, verbose_name='building depreciation'),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='building_repair_and_rent',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='county_yield',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='drying',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='farm_yield',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='fertilizers',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='fuel_and_oil',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='insurance',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='interest_nonland',
            field=models.FloatField(default=0, verbose_name='non-land interest cost'),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='labor_and_mgmt',
            field=models.FloatField(default=0, verbose_name='labor and management'),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='light_vehicle',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='machine_depr',
            field=models.FloatField(default=0, verbose_name='machine depreciation'),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='machine_hire_lease',
            field=models.FloatField(default=0, verbose_name='machine hire or lease'),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='machine_repair',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='misc_overhead_costs',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='other_direct_costs',
            field=models.FloatField(default=0, help_text='Other (hauling, custom operations)'),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='other_gov_pmts',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='other_overhead_costs',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='other_revenue',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='pesticides',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='rented_land_costs',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='seed',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='storage',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='utilities',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='yield_variability',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmcrop',
            name='adj_yield',
            field=models.FloatField(default=0, help_text='Adjusted yield provided by insurer.', verbose_name='Adjusted yield'),
        ),
        migrations.AlterField(
            model_name='farmcrop',
            name='planted_acres',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmcrop',
            name='prot_factor',
            field=models.FloatField(default=1, help_text='Selected payment factor for county premiums/indemnities.', verbose_name='selected payment factor'),
        ),
        migrations.AlterField(
            model_name='farmcrop',
            name='rate_yield',
            field=models.FloatField(default=0, help_text='Rate yield provided by insurer.'),
        ),
        migrations.AlterField(
            model_name='farmcrop',
            name='rma_cty_expected_yield',
            field=models.FloatField(blank=True, help_text='The RMA expected yield for the county if available', null=True, verbose_name='RMA county expected yield'),
        ),
        migrations.AlterField(
            model_name='farmcrop',
            name='ta_aph_yield',
            field=models.FloatField(default=0, help_text='Trend-adjusted average prodution history yield provided by insurer.', verbose_name='TA APH yield'),
        ),
        migrations.AlterField(
            model_name='farmyear',
            name='annual_land_int_expense',
            field=models.FloatField(default=0, help_text='Annual owned land interest expense', verbose_name='land interest expense'),
        ),
        migrations.AlterField(
            model_name='farmyear',
            name='annual_land_principal_pmt',
            field=models.FloatField(default=0, help_text='Annual owned land principal payment', verbose_name='land principal payment'),
        ),
        migrations.AlterField(
            model_name='farmyear',
            name='cash_rented_acres',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmyear',
            name='cropland_acres_owned',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmyear',
            name='cropland_acres_rented',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmyear',
            name='eligible_persons_for_cap',
            field=models.SmallIntegerField(default=0, help_text="Number of eligible 'persons' for FSA payment caps.", verbose_name='# persons for cap'),
        ),
        migrations.AlterField(
            model_name='farmyear',
            name='land_repairs',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmyear',
            name='price_factor',
            field=models.FloatField(default=1, verbose_name='price sensititivity factor'),
        ),
        migrations.AlterField(
            model_name='farmyear',
            name='property_taxes',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='farmyear',
            name='var_rent_cap_floor_frac',
            field=models.FloatField(default=0, help_text='Floor and cap on variable rent as a percent of starting base rent', verbose_name='variable rent floor/cap'),
        ),
        migrations.AlterField(
            model_name='farmyear',
            name='yield_factor',
            field=models.FloatField(default=1, verbose_name='yield sensititivity factor'),
        ),
        migrations.AlterField(
            model_name='fsacrop',
            name='arcco_base_acres',
            field=models.FloatField(default=0, verbose_name='Base acres in ARC-CO'),
        ),
        migrations.AlterField(
            model_name='fsacrop',
            name='plc_base_acres',
            field=models.FloatField(default=0, verbose_name='Base acres in PLC'),
        ),
        migrations.AlterField(
            model_name='fsacrop',
            name='plc_yield',
            field=models.FloatField(default=0, help_text='Weighted average PLC yield for farm in bushels per acre.', verbose_name='farm avg. PLC yield'),
        ),
        migrations.AlterField(
            model_name='marketcrop',
            name='assumed_basis_for_new',
            field=models.FloatField(default=0, help_text='Assumed basis for non-contracted bushels.'),
        ),
        migrations.AlterField(
            model_name='marketcrop',
            name='avg_contract_price',
            field=models.FloatField(default=0, help_text='Average price for futures contracts.', verbose_name='avg. contract price'),
        ),
        migrations.AlterField(
            model_name='marketcrop',
            name='avg_locked_basis',
            field=models.FloatField(default=0, help_text='Average basis on basis contracts in place.', verbose_name='avg. locked basis'),
        ),
        migrations.AlterField(
            model_name='marketcrop',
            name='basis_bu_locked',
            field=models.FloatField(default=0, help_text='Number of bushels with contracted basis set.', verbose_name='bushels with basis locked'),
        ),
        migrations.AlterField(
            model_name='marketcrop',
            name='contracted_bu',
            field=models.FloatField(default=0, help_text='Current contracted bushels on futures.', verbose_name='contracted bushels'),
        ),
    ]
