from django.forms import ModelForm
from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, Fieldset

from .models.farm_year import FarmYear
from .models.farm_crop import FarmCrop
from .models.farm_budget_crop import FarmBudgetCrop


class AjaxChoiceIntField(forms.ChoiceField):
    def valid_value(self, value):
        return 1 <= int(value) < 1000


class FarmYearCreateForm(ModelForm):
    county_code = AjaxChoiceIntField()

    class Meta:
        model = FarmYear
        fields = ['farm_name', 'state', 'county_code']


class FarmYearUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Update'))
        self.helper.layout = Layout(
            Field('farm_name'),
            Fieldset('Owned Land Information',
                     'cropland_acres_owned', 'annual_land_int_expense',
                     'annual_land_principal_pmt', 'property_taxes',
                     'land_repairs'),
            Fieldset('Rented Land Information',
                     'cropland_acres_rented', 'cash_rented_acres',
                     'var_rent_cap_floor_frac'),
            Fieldset('Non-grain income and expense',
                     'other_nongrain_income', 'other_nongrain_expense',
                     'eligible_persons_for_cap'),
            Fieldset('Report Controls',
                     'report_type', 'is_model_run_date_manual',
                     'manual_model_run_date'),
        )

    class Meta:
        model = FarmYear
        fields = '''farm_name cropland_acres_owned cropland_acres_rented
                cash_rented_acres var_rent_cap_floor_frac annual_land_int_expense
                annual_land_principal_pmt property_taxes land_repairs
                eligible_persons_for_cap other_nongrain_income
                other_nongrain_expense report_type manual_model_run_date
                is_model_run_date_manual'''.split()


class FarmCropUpdateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subcounty'].choices = self.instance.allowed_subcounties()
        self.fields['ins_practice'].choices = self.instance.allowed_practices()
        self.fields['coverage_type'].choices = self.instance.allowed_coverage_types()
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Update'))
        self.helper.layout = Layout(
            Field('planted_acres'),
            Field('yield_factor'),
            Fieldset('Crop Insurance Information',
                     'rate_yield', 'adj_yield', 'ta_aph_yield', 'subcounty'),
            Fieldset('Crop Insurance Choices',
                     'ta_use', 'ye_use', 'coverage_type', 'product_type',
                     'base_coverage_level', 'sco_use', 'eco_level', 'prot_factor'),
        )

    class Meta:
        model = FarmCrop
        fields = '''planted_acres ins_practice rate_yield adj_yield ta_aph_yield
        ta_use ye_use subcounty coverage_type product_type base_coverage_level
        sco_use eco_level prot_factor yield_factor'''.split()


class FarmBudgetCropUpdateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Update'))
        self.helper.layout = Layout(
            Fieldset('Expected Yields',
                     'farm_yield', 'county_yield'),
            Fieldset('Revenue Items',
                     'other_gov_pmts', 'other_revenue'),
            Fieldset('Direct Costs',
                     'fertilizers', 'pesticides', 'seed', 'drying', 'storage',
                     'other_direct_costs'),
            Fieldset('Power Costs', 'machine_hire_lease', 'utilities',
                     'machine_repair', 'fuel_and_oil', 'light_vehicle',
                     'machine_depr'),
            Fieldset('Overhead Costs', 'labor_and_mgmt', 'building_repair_and_rent',
                     'building_depr', 'insurance', 'misc_overhead_costs',
                     'interest_nonland', 'other_overhead_costs', 'rented_land_costs'),
            Fieldset('Land Costs', 'rented_land_costs'),
        )

    class Meta:
        model = FarmBudgetCrop
        fields = '''farm_yield county_yield
              other_gov_pmts other_revenue fertilizers pesticides
              seed drying storage other_direct_costs machine_hire_lease
              utilities machine_repair fuel_and_oil light_vehicle
              machine_depr labor_and_mgmt building_repair_and_rent
              building_depr insurance misc_overhead_costs interest_nonland
              other_overhead_costs rented_land_costs'''.split()
