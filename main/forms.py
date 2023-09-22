from django.forms import ModelForm
from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, Fieldset, Hidden

from .models.farm_year import FarmYear
from .models.farm_crop import FarmCrop
from .models.farm_budget_crop import FarmBudgetCrop
from .models.market_crop import MarketCrop, Contract


class AjaxChoiceIntField(forms.ChoiceField):
    def valid_value(self, value):
        return 1 <= int(value) < 1000


class FarmYearCreateForm(ModelForm):
    county_code = AjaxChoiceIntField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Create'))

    class Meta:
        model = FarmYear
        fields = ['farm_name', 'state', 'county_code']


class FarmYearUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Update'))
        self.helper.form_id = 'farmyearform'
        self.helper.layout = Layout(
            Field('farm_name'),
            Fieldset('Owned Land Information',
                     'cropland_acres_owned', 'annual_land_int_expense',
                     'annual_land_principal_pmt', 'property_taxes',
                     'land_repairs'),
            Fieldset('Rented Land Information',
                     'cash_rented_acres', 'variable_rented_acres',
                     Field('var_rent_cap_floor_frac', css_class="percent")),
            Fieldset('Non-grain income and expense',
                     'other_nongrain_income', 'other_nongrain_expense'),
            Fieldset('Farm Level Title Settings', 'eligible_persons_for_cap',
                     Field('est_sequest_frac', css_class="percent")),
            Fieldset('Report Controls',
                     'is_model_run_date_manual', 'manual_model_run_date'),
        )

    class Meta:
        model = FarmYear
        fields = '''farm_name cropland_acres_owned variable_rented_acres
                cash_rented_acres var_rent_cap_floor_frac annual_land_int_expense
                annual_land_principal_pmt property_taxes land_repairs
                eligible_persons_for_cap other_nongrain_income
                other_nongrain_expense manual_model_run_date
                is_model_run_date_manual est_sequest_frac'''.split()


class FarmCropUpdateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subcounty'].choices = self.instance.allowed_subcounties()
        self.fields['ins_practice'].choices = self.instance.allowed_practices()
        self.fields['coverage_type'].choices = self.instance.allowed_coverage_types()
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Update'))
        self.helper.form_id = 'id-farmcropform'
        self.helper.layout = Layout(
            Fieldset('Key Values',
                     'planted_acres', 'ins_practice'),
            Fieldset('Crop Insurance Information',
                     'rate_yield', 'adj_yield', 'subcounty', 'ta_use',
                     'ye_use', 'ta_aph_yield'),
            Fieldset('Crop Insurance Choices',
                     'coverage_type', 'product_type', 'base_coverage_level', 'sco_use',
                     'eco_level', Field('prot_factor', css_class="percent")),
        )

    class Meta:
        model = FarmCrop
        fields = '''planted_acres ins_practice rate_yield adj_yield ta_aph_yield
        ta_use ye_use subcounty coverage_type product_type base_coverage_level
        sco_use eco_level prot_factor'''.split()


class FarmBudgetCropUpdateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Update'))
        self.helper.form_id = 'farmbudgetform'
        self.helper.layout = Layout(
            Fieldset('Baseline Yield',
                     'baseline_yield_for_var_rent'),
            Fieldset('Expected Yields',
                     'farm_yield', 'county_yield', 'is_farm_yield_final',
                     Field('yield_factor', css_class='percent')),
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
                     'interest_nonland', 'other_overhead_costs'),
            Fieldset('Land Costs', 'rented_land_costs'),
            Fieldset('Cost Adjustments',
                     Field('yield_variability', css_class='percent'),
                     'are_costs_final'),
        )

    class Meta:
        model = FarmBudgetCrop
        fields = '''farm_yield baseline_yield_for_var_rent county_yield
              other_gov_pmts other_revenue fertilizers pesticides
              seed drying storage other_direct_costs machine_hire_lease
              utilities machine_repair fuel_and_oil light_vehicle
              machine_depr labor_and_mgmt building_repair_and_rent
              building_depr insurance misc_overhead_costs interest_nonland
              other_overhead_costs rented_land_costs yield_variability
              is_farm_yield_final are_costs_final yield_factor'''.split()


class ZeroAcreFarmBudgetCropUpdateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Update'))
        self.helper.form_id = 'farmbudgetform'
        self.helper.layout = Layout(
            Fieldset('Expected Yields',
                     'county_yield', 'is_farm_yield_final',
                     Field('yield_factor', css_class='percent')),
        )

    class Meta:
        model = FarmBudgetCrop
        fields = '''county_yield is_farm_yield_final yield_factor'''.split()


class MarketCropUpdateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Update'))
        self.helper.form_id = 'marketcropform'
        self.helper.layout = Layout(
            Fieldset('Uncontracted Grain',
                     'assumed_basis_for_new',
                     Field('price_factor', css_class='percent')),
        )

    class Meta:
        model = MarketCrop
        fields = '''assumed_basis_for_new
                    price_factor'''.split()


class ContractCreateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        print(f'in form: {kwargs=}')
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Create'))
        self.helper.form_id = 'contractform'
        self.helper.layout = Layout(
            Fieldset('Contract Information',
                     'contract_date', 'bushels', 'price', 'terminal',
                     'contract_number', 'delivery_start_date',
                     'delivery_end_date',
                     Field('is_basis', type='hidden'),
                     Field('market_crop', type='hidden'),
                     )
        )

    class Meta:
        model = Contract
        fields = '''contract_date bushels price terminal
                    contract_number delivery_start_date
                    delivery_end_date is_basis market_crop'''.split()


class ContractUpdateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Update'))
        self.helper.form_id = 'contractform'
        self.helper.layout = Layout(
            Fieldset('Contract Information',
                     'contract_date', 'bushels', 'price', 'terminal',
                     'contract_number', 'delivery_start_date',
                     'delivery_end_date',
                     Field('is_basis', type='hidden'),
                     Field('market_crop', type='hidden'),
                     )
        )

    class Meta:
        model = Contract
        fields = '''contract_date bushels price terminal
                    contract_number delivery_start_date
                    delivery_end_date is_basis market_crop'''.split()
