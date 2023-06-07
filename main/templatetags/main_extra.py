from django import template
from django.template.defaultfilters import floatformat

register = template.Library()


@register.filter(is_safe=True)
def pct(value, arg=0):
    """ Formats as a percent to desired decimal places (default 0) """
    if value is None:
        return None
    return floatformat(value * 100.0, arg) + '%'
