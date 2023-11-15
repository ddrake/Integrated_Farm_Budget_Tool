from datetime import datetime
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, Fieldset, HTML

from .models.farm_year import FarmYear
from .models.farm_crop import FarmCrop, FarmBudgetCrop
from .models.market_crop import MarketCrop, Contract
from .models.fsa_crop import FsaCrop


class AjaxChoiceIntField(forms.ChoiceField):
    def valid_value(self, value):
        return 1 <= int(value) < 1000


class FarmYearCreateForm(ModelForm):
    county_code = AjaxChoiceIntField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs = {"novalidate": ''}
        self.helper.add_input(Submit('submit', 'Create'))
        self.helper.layout = Layout(
            Fieldset('Farm Information',
                     'farm_name', 'state', 'county_code',
                     Field('user', type='hidden'),
                     )
        )

    def clean_farm_name(self):
        farmname = self.cleaned_data['farm_name']
        user = self.data['user']
        name_exists = FarmYear.objects.filter(
            crop_year=datetime.now().year,
            farm_name=farmname,
            user=user)
        if name_exists:
            raise ValidationError('Farm Name is unique for a given user and crop year')
        return farmname

    class Meta:
        # Note: The label defined in the model as verbose_name is ignored, probably
        # because of replacing the widget.  I tried adding the label explicitly here
        # labels = {'county_code': 'Primary county'}
        # but it had no effect. Hacked in Javascript for now.
        model = FarmYear
        fields = ['farm_name', 'state', 'county_code', 'user']


class FarmYearUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs = {"novalidate": ''}
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
            Fieldset('Non-grain revenue and expense',
                     'other_nongrain_income', 'other_nongrain_expense'),
            Fieldset('Farm Level Title Settings', 'eligible_persons_for_cap',
                     Field('est_sequest_frac', css_class="percent")),
            Fieldset('Report Controls',
                     'is_model_run_date_manual', 'manual_model_run_date',
                     'basis_increment'),
        )

    class Meta:
        model = FarmYear
        fields = '''farm_name cropland_acres_owned variable_rented_acres
                cash_rented_acres var_rent_cap_floor_frac annual_land_int_expense
                annual_land_principal_pmt property_taxes land_repairs
                eligible_persons_for_cap other_nongrain_income
                other_nongrain_expense manual_model_run_date
                is_model_run_date_manual est_sequest_frac basis_increment'''.split()
        widgets = {
            'cropland_acres_owned': forms.NumberInput(
                attrs={'step': 100, 'min': 0, 'max': 100000}),
            'variable_rented_acres': forms.NumberInput(
                attrs={'step': 100, 'min': 0, 'max': 100000}),
            'cash_rented_acres': forms.NumberInput(
                attrs={'step': 100, 'min': 0, 'max': 100000}),
            'var_rent_cap_floor_frac': forms.NumberInput(
                attrs={'step': 1, 'min': 0, 'max': 100}),
            'annual_land_int_expense': forms.NumberInput(
                attrs={'step': 1000, 'min': 0, 'max': 1000000}),
            'annual_land_principal_pmt': forms.NumberInput(
                attrs={'step': 1000, 'min': 0, 'max': 1000000}),
            'property_taxes': forms.NumberInput(
                attrs={'step': 1000, 'min': 0, 'max': 1000000}),
            'land_repairs': forms.NumberInput(
                attrs={'step': 1000, 'min': 0, 'max': 1000000}),
            'eligible_persons_for_cap': forms.NumberInput(
                attrs={'step': 1, 'min': 0, 'max': 10}),
            'other_nongrain_income': forms.NumberInput(
                attrs={'step': 1000, 'min': 0, 'max': 1000000}),
            'other_nongrain_expense': forms.NumberInput(
                attrs={'step': 1000, 'min': 0, 'max': 1000000}),
            'basis_increment': forms.NumberInput(
                attrs={'step': 0.1, 'min': 0, 'max': 0.5}),
            'est_sequest_frac': forms.NumberInput(
                attrs={'step': 0.1, 'min': 0, 'max': 10}),
        }


class FarmYearUpdateFormForTitle(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs = {"novalidate": ''}
        self.helper.add_input(Submit('submit', 'Update'))
        self.helper.form_id = 'farmyearform'
        self.helper.layout = Layout(
            Fieldset('Farm Level Title Settings', 'eligible_persons_for_cap',
                     Field('est_sequest_frac', css_class="percent")),
        )

    class Meta:
        model = FarmYear
        fields = '''eligible_persons_for_cap est_sequest_frac'''.split()
        widgets = {
            'eligible_persons_for_cap': forms.NumberInput(
                attrs={'step': 1, 'min': 0, 'max': 10}),
            'est_sequest_frac': forms.NumberInput(
                attrs={'step': 0.1, 'min': 0, 'max': 10}),
        }


class FarmCropUpdateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subcounty'].choices = self.instance.allowed_subcounties()
        self.fields['ins_practice'].choices = self.instance.allowed_practices()
        self.fields['coverage_type'].choices = self.instance.allowed_coverage_types()
        self.helper = FormHelper()
        self.helper.attrs = {"novalidate": ''}
        self.helper.add_input(Submit('submit', 'Update'))
        self.helper.form_id = 'id-farmcropform'
        self.helper.layout = Layout(
            Fieldset('Key Values',
                     'planted_acres', 'ins_practice'),
            Fieldset('Crop Insurance Information',
                     'rate_yield', 'adj_yield', 'subcounty', 'ta_use',
                     'ye_use', 'appr_yield'),
            Fieldset('Crop Insurance Choices',
                     'coverage_type', 'product_type', 'base_coverage_level', 'sco_use',
                     'eco_level', Field('prot_factor', css_class="percent")),
        )

    class Meta:
        model = FarmCrop
        fields = '''planted_acres ins_practice rate_yield adj_yield appr_yield
        ta_use ye_use subcounty coverage_type product_type base_coverage_level
        sco_use eco_level prot_factor'''.split()
        widgets = {
            'planted_acres': forms.NumberInput(
                attrs={'step': 100, 'min': 0, 'max': 100000}),
            'appr_yield': forms.NumberInput(
                attrs={'step': 1, 'min': 0, 'max': 400}),
            'adj_yield': forms.NumberInput(
                attrs={'step': 1, 'min': 0, 'max': 400}),
            'rate_yield': forms.NumberInput(
                attrs={'step': 1, 'min': 0, 'max': 400}),
        }


class FarmBudgetCropUpdateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs = {"novalidate": ''}
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
        widgets = {
            'yield_factor': forms.NumberInput(
                attrs={'step': 10, 'min': 0, 'max': 200}),
        }


class ZeroAcreFarmBudgetCropUpdateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs = {"novalidate": ''}
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
        widgets = {
            'yield_factor': forms.NumberInput(
                attrs={'step': 10, 'min': 0, 'max': 200}),
        }


class MarketCropUpdateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs = {"novalidate": ''}
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
        widgets = {
            'assumed_basis_for_new': forms.NumberInput(
                attrs={'step': 0.01, 'min': -2, 'max': 2}),
            'price_factor': forms.NumberInput(
                attrs={'step': 10, 'min': 0, 'max': 1000}),
        }


class FsaCropUpdateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs = {"novalidate": ''}
        self.helper.add_input(Submit('submit', 'Update'))
        self.helper.form_id = 'fsacropform'

    class Meta:
        model = FsaCrop
        fields = '''plc_base_acres arcco_base_acres plc_yield'''.split()
        widgets = {
            'plc_base_acres': forms.NumberInput(
                attrs={'step': 100, 'min': 0, 'max': 100000}),
            'arcco_base_acres': forms.NumberInput(
                attrs={'step': 100, 'min': 0, 'max': 100000}),
            'plc_yield': forms.NumberInput(
                attrs={'step': 1, 'min': 0, 'max': 400}),
        }


class ContractCreateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mcid = (kwargs.get('initial', None) and
                kwargs['initial'].get('market_crop', None))
        if mcid is None:
            mcid = (kwargs.get('data', None) and
                    kwargs['data'].get('market_crop', None))

        cropname = str(MarketCrop.objects.get(pk=mcid))
        self.helper = FormHelper()
        self.helper.attrs = {"novalidate": ''}
        self.helper.add_input(Submit('submit', 'Create'))
        self.helper.form_id = 'contractform'
        self.helper.layout = Layout(
            HTML(f"""<h1 class="block text-xl mb-2">Add {cropname} Contract</h1>"""),
            Fieldset('Contract Information',
                     'contract_date', 'bushels', 'futures_price', 'basis_price',
                     'terminal', 'contract_number', 'delivery_start_date',
                     'delivery_end_date',
                     Field('market_crop', type='hidden'),
                     )
        )

    class Meta:
        model = Contract
        fields = '''contract_date bushels futures_price basis_price
                    terminal contract_number delivery_start_date
                    delivery_end_date market_crop'''.split()
        widgets = {
            'bushels': forms.NumberInput(
                attrs={'step': 1000, 'min': 0, 'max': 1000000}),
            'futures_price': forms.NumberInput(
                attrs={'step': 0.01, 'min': 1, 'max': 25}),
            'basis_price': forms.NumberInput(
                attrs={'step': 0.01, 'min': -2, 'max': 2}),
        }


class ContractUpdateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs = {"novalidate": ''}
        self.helper.add_input(Submit('submit', 'Update'))
        self.helper.form_id = 'contractform'
        self.helper.layout = Layout(
            HTML("""<h1 class="block text-xl mb-2">Edit Contract</h1>"""),
            Fieldset('Contract Information',
                     'contract_date', 'bushels', 'futures_price', 'basis_price',
                     'terminal', 'contract_number', 'delivery_start_date',
                     'delivery_end_date',
                     Field('market_crop', type='hidden'),
                     )
        )

    class Meta:
        model = Contract
        fields = '''contract_date bushels futures_price basis_price
                    terminal contract_number delivery_start_date
                    delivery_end_date market_crop'''.split()
        widgets = {
            'bushels': forms.NumberInput(
                attrs={'step': 1000, 'min': 0, 'max': 1000000}),
            'futures_price': forms.NumberInput(
                attrs={'step': 0.01, 'min': 1, 'max': 25}),
            'basis_price': forms.NumberInput(
                attrs={'step': 0.01, 'min': -2, 'max': 2}),
        }
