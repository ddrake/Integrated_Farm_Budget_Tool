""" Module util -- utility functions for main model """
import numbers
from datetime import datetime
from collections import defaultdict
import numpy as np


def scal(factor):
    """
    check whether a price or yield factor is a scalar or an array
    Rests on the assumption that calls from the sensitivity table will always
    provide both an array of price factors and an array of yield factors
    """
    return factor is None or isinstance(factor, numbers.Number)


def get_current_year():
    """
    Because we may want to test a farm year for a future crop year,
    this utility should be used ONLY to set the defaults for a farm year.
    It cannot easily be moved to the farm year model because migrations depend on
    it being defined here.
    """
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


def notify_users_of_budget_updates(budgetids, prevyr=False):
    from .farm_crop import FarmBudgetCrop

    fbcs = FarmBudgetCrop.objects.filter(budget_crop_id__in=budgetids)
    user_budget_info = defaultdict(list)
    for fbc in fbcs:
        user_budget_info[fbc.farm_year.user_id].append(
            (fbc.farm_year.user, fbc.farm_year, fbc.farm_crop, fbc.budget_crop))
    usernames = []
    for id, lst in user_budget_info.items():
        user = lst[0][0]
        body = (f"Hi {user.username}.  One or more of your budgets have new "
                "versions available to replace ")
        if prevyr:
            body += ("placeholder budgets, "
                     "which were obtained by modifying 2023 budgets:\n\n")
        else:
            body += ("previously-published 2024 university-based budgets:\n\n")

        for _, farmyear, farmcrop, bc in sorted(lst, key=lambda x: str(x[1])):
            body += f"• {str(farmyear)}: {str(farmcrop)}\n"
        body += ("\nTo update a budget, "
                 "go to bottom of the Crop Acreage / Crop Insurance page, and "
                 "first de-select the current selection "
                 "by clicking the empty budget at the top of the drop-down list, "
                 "then click on the originally selected item to re-select your budget. "
                 "\n\nAny customizations you may have made will be lost upon update, "
                 "so you may prefer not to update budgets "
                 "which have extensive changes.")

        usernames.append(user.username)

        user.email_user(
            "Updated Budget(s) Avaialable", body)
    return usernames


def default_start_date():
    """ Jan 1 of the current year is hereby the default start date for farm years. """
    year = get_current_year()
    return datetime(year, 1, 1)


def one_like(var):
    return 1 if scal(var) else np.ones_like(var)


def zero_like(var):
    return 0 if scal(var) else np.zeros_like(var)
