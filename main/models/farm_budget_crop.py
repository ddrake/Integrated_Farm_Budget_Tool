from datetime import datetime
from django.core.validators import (
    MinValueValidator as MinVal, MaxValueValidator as MaxVal)
from django.db import models
from ext.models import State, Budget, BudgetCrop, FarmCropType
from .farm_year import FarmYear
from .farm_crop import FarmCrop, BaselineFarmCrop


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


class FarmBudgetCrop(models.Model):
    """
    A possibly user-modfied copy of a budget column named by its budget_crop_type name.
    Cost items are in dollars per acre.  One or two (rotated/non-rotated) budget crops
    are assigned To each farm crop based on matching the farm_crop_type and
    irrigated status of the farm crop to the buddget crop type.
    """
    farm_yield = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(400)],
        help_text='Set this to the final farm yield after harvest')
    # the farm yield value is copied to county yield when the budget crop is copied.
    county_yield = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(400)],
        help_text='Set this to the estimated final county yield after harvest')
    description = models.CharField(max_length=50)
    yield_variability = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(1)])
    other_gov_pmts = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(99999)])
    other_revenue = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    fertilizers = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    pesticides = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    seed = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    drying = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    storage = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    other_direct_costs = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        help_text="Other (hauling, custom operations)")
    machine_hire_lease = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="machine hire or lease")
    utilities = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    machine_repair = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    fuel_and_oil = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    light_vehicle = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    machine_depr = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="machine depreciation")
    labor_and_mgmt = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="labor and management")
    building_repair_and_rent = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    building_depr = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="building depreciation")
    insurance = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    misc_overhead_costs = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    interest_nonland = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="non-land interest cost")
    other_overhead_costs = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    rented_land_costs = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(9999999)])
    farm_crop_type = models.ForeignKey(
        FarmCropType, on_delete=models.CASCADE, null=True)
    farm_crop = models.OneToOneField(
        FarmCrop, on_delete=models.CASCADE, null=True)
    farm_year = models.ForeignKey(
        FarmYear, on_delete=models.CASCADE, null=True)
    budget = models.ForeignKey(Budget, on_delete=models.SET_NULL, null=True)
    budget_crop = models.ForeignKey(BudgetCrop, on_delete=models.SET_NULL, null=True)
    state = models.ForeignKey(
        State, on_delete=models.CASCADE, null=True, related_name='farm_budget_crops')
    is_rot = models.BooleanField(null=True)
    is_irr = models.BooleanField(default=False)
    # This is set to the ext_budget.created_on date when a farm budget crop is added.
    # If a budget for a crop year is updated, we can compare its created_on date with
    # corresponding user budget_date and notify users
    budget_date = models.DateField(null=True)
    baseline_yield_for_var_rent = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(400)],
        verbose_name="baseline yield",
        help_text=('Fixed farm yield used for variable rent ' +
                   'and yield-based cost adjustment'))
    is_farm_yield_final = models.BooleanField(
        default=False, verbose_name="yields final?",
        help_text='Adjust expected yield(s) and check this box after harvest')
    yield_factor = models.FloatField(
        default=1, validators=[MinVal(0), MaxVal(2)],
        verbose_name='yield sensititivity factor',
        help_text=('Modify expected yield(s) prior to harvest, ' +
                   'affecting detailed budget'))
    are_costs_final = models.BooleanField(
        default=False, verbose_name="Costs final?",
        help_text='Adjust costs and check this box (if desired) once costs are known')

    def __str__(self):
        rotstr = (' Rotating' if self.is_rot
                  else '' if self.is_rot is None else ' Continuous,')
        descr = '' if self.description == '' else f' {self.description},'
        return (f'{self.state.abbr},{descr}{rotstr}')

    class Meta:
        ordering = ['farm_crop_type_id']

    def total_power_costs(self):
        """ for farm budget crop detail view """
        return (self.machine_hire_lease + self.utilities + self.machine_repair +
                self.fuel_and_oil + self.light_vehicle + self.machine_depr)

    def total_overhead_costs(self):
        """ for farm budget crop detail view """
        return (self.labor_and_mgmt + self.building_repair_and_rent +
                self.building_depr + self.insurance + self.misc_overhead_costs +
                self.interest_nonland + self.other_overhead_costs)


class BaselineFarmBudgetCrop(models.Model):
    farm_crop_type = models.ForeignKey(FarmCropType, on_delete=models.CASCADE)
    farm_crop = models.ForeignKey(BaselineFarmCrop, on_delete=models.CASCADE,
                                  related_name='budget_crops')
    orig_budget = models.ForeignKey(Budget, on_delete=models.SET_NULL, null=True)
