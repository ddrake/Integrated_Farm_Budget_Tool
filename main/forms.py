from django.forms import ModelForm
from django import forms

from .models import FarmYear, FarmCrop


class AjaxChoiceField(forms.ChoiceField):
    def valid_value(self, value):
        return True


class FarmYearCreateForm(ModelForm):
    county_code = AjaxChoiceField()

    class Meta:
        model = FarmYear
        fields = ['farm_name', 'state', 'county_code']


class FarmCropUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subcounty'].choices = self.instance.allowed_subcounties()

    class Meta:
        model = FarmCrop
        fields = ['planted_acres', 'ins_practice', 'ta_aph_yield', 'adj_yield',
                  'rate_yield', 'ye_use', 'ta_use', 'subcounty', ]
