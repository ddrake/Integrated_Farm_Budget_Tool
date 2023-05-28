from django.forms import ModelForm
from django import forms

from .models import FarmYear


class AjaxChoiceField(forms.ChoiceField):
    def valid_value(self, value):
        return True


class FarmYearCreateForm(ModelForm):
    county_code = AjaxChoiceField()

    class Meta:
        model = FarmYear
        fields = ['farm_name', 'state', 'county_code']
