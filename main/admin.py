from django.contrib import admin

from .models import (FarmYear, FsaCrop, MarketCrop, FarmCrop, FarmBudgetCrop)

# This FarmCropInline idea didn't work, because the _meta choices didn't get set
# in time.


class FarmBudgetCropInline(admin.StackedInline):
    model = FarmBudgetCrop
    extra = 0


class FarmCropAdmin(admin.ModelAdmin):
    model = FarmCrop
    extra = 0
    fieldsets = [
        (
            'General Information',
            {
                'fields': [
                    'planted_acres', 'ins_practice', 'rate_yield', 'adj_yield',
                    'ta_aph_yield', 'ta_use', 'ye_use', 'subcounty',
                ],
            },
        ),
        (
            'Crop insurance selections',
            {
                'fields': ['coverage_type', 'product_type', 'base_coverage_level',
                           'sco_use', 'eco_level', 'prot_factor'],
            },
        ),
    ]
    inlines = [FarmBudgetCropInline]


class MarketCropInline(admin.StackedInline):
    model = MarketCrop
    extra = 0


class FsaCropInline(admin.StackedInline):
    model = FsaCrop
    extra = 0


class FarmYearAdmin(admin.ModelAdmin):
    fields = [
        'farm_name', 'user', 'state', 'county_code', 'crop_year',
        'cropland_acres_owned', 'cropland_acres_rented', 'cash_rented_acres',
        'var_rent_cap_floor_frac', 'annual_land_int_expense',
        'annual_land_principal_pmt', 'property_taxes', 'land_repairs',
        'eligible_persons_for_cap', 'report_type', 'model_run_date',
        'price_factor', 'yield_factor']
    inlines = [MarketCropInline, FsaCropInline]


admin.site.register(FarmYear, FarmYearAdmin)
admin.site.register(FarmCrop, FarmCropAdmin)
admin.site.register(MarketCrop)
admin.site.register(FsaCrop)
# admin.site.register(FarmBudgetCrop)
