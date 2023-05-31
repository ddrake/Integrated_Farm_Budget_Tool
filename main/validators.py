from functools import wraps
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_range(low=0, high=None):
    @wraps(validate_range)
    def inner(value):
        if value is not None and value < low or high is not None and value > high:
            raise ValidationError(
                _('value must be >= %(low)s' if high is None
                  else 'value must be >= %(low)s and <= %(high)s'),
                params={'low': low, 'high': high},
            )
    return inner
