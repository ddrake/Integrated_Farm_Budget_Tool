""" Module util -- utility functions for main model """
import numbers
from datetime import datetime
import numpy as np


def scal(factor):
    """
    check whether a price or yield factor is a scalar or an array
    Rests on the assumption that calls from the sensitivity table will always
    provide both an array of price factors and an array of yield factors
    """
    return factor is None or isinstance(factor, numbers.Number)


def get_current_year():
    return datetime.today().year


def any_changed(instance, *fields):
    """
    Check an instance to see if the values of any of the listed fields changed.
    """
    if not instance.pk:
        return False
    dbinst = instance.__class__._default_manager.get(pk=instance.pk)
    return any((getattr(dbinst, field) != getattr(instance, field)
                for field in fields))


def has_farm_years(user):
    from .farm_year import FarmYear
    if not isinstance(user, int):
        user = user.pk
    return FarmYear.objects.filter(user=user).exists()


def notify_user_of_bugfix(username):
    from django.contrib.auth.models import User
    user = User.objects.get(username=username)
    user.email_user(
        "Bug Fixed!",
        (f"Hi {username}." + "  We noticed you bumped into an Application Error.  "
         "Sorry about that, but thanks for your patience.  "
         "We just wanted to let you know that it should be fixed now.\n\n" +
         "Please don't reply to this email address; it has no inbox.  " +
         "If you're still seeing an issue, please click the 'Help' link at ifbt.farm " +
         "and post a message letting us know the details."))


def default_start_date():
    """ For remainder of 2023, use Jan, 11, but after that, change to Jan 1. """
    year = get_current_year()
    return datetime(year, 1, 11)


def one_like(var):
    return 1 if scal(var) else np.ones_like(var)


def zero_like(var):
    return 0 if scal(var) else np.zeros_like(var)
