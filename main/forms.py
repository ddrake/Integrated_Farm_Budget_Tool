from django.forms import ModelForm
from django import forms

from .models.farm_year import FarmYear
from .models.farm_crop import FarmCrop


class AjaxChoiceIntField(forms.ChoiceField):
    def valid_value(self, value):
        return 1 <= int(value) < 1000


class FarmYearCreateForm(ModelForm):
    county_code = AjaxChoiceIntField()

    class Meta:
        model = FarmYear
        fields = ['farm_name', 'state', 'county_code']


class FarmCropUpdateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subcounty'].choices = self.instance.allowed_subcounties()
        self.fields['ins_practice'].choices = self.instance.allowed_practices()
        self.fields['coverage_type'].choices = self.instance.allowed_coverage_types()

    class Meta:
        model = FarmCrop
        fields = '''planted_acres ins_practice rate_yield adj_yield ta_aph_yield
        ta_use ye_use subcounty coverage_type product_type base_coverage_level
        sco_use eco_level prot_factor price_factor yield_factor'''.split()
