from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import (
    MinValueValidator as MinVal, MaxValueValidator as MaxVal)
from django.db import models
from django.utils.translation import gettext_lazy as _
from ext.models import (
    State, County, InsurableCropsForCty, MyaPreEstimate, MyaPost,
    FarmCropType, MarketCropType, FsaCropType, InsuranceDates)
from core.models.gov_pmt import GovPmt
from . import util


# ---------
# Farm Year
# ---------
class FarmYear(models.Model):
    """
    Holds non-crop-specific values for a crop year for a farm
    A user can have multiple FarmYears, including up to 10 farms for the
    same crop year, but we don't do any aggregation over a user's farms
    for a given crop year.
    A FarmYear has FarmCrops FarmBudgetCrops, MarketCrops and FsaCrops.
    A farm year includes FarmCrops if and only if they can be insured.
    """
    IRR_PRACTICE = {2: 'Irrigated', 3: 'Non-Irrigated', 53: 'Non-Irrigated',
                    43: 'Non-Irrigated', 94: 'Irrigated', 95: 'Irrigated'}
    FSA_PMT_CAP_PER_PRINCIPAL = 125000
    PRETAX_INCOME = 0
    PRETAX_CASH_FLOW = 1
    REPORT_TYPES = [(PRETAX_INCOME, 'Pre-tax income'),
                    (PRETAX_CASH_FLOW, 'Pre-tax cash flow')]
    farm_name = models.CharField(max_length=60)
    county_code = models.SmallIntegerField(
        verbose_name="primary county",
        help_text="The county where most farm acres are located")
    crop_year = models.SmallIntegerField(default=util.get_current_year)
    report_type = models.SmallIntegerField(
        default=0, choices=REPORT_TYPES,
        help_text=("Pre-Tax cash flow deducts land debt interest and principal " +
                   "payments. Pre-tax Income deducts only interest expense."))
    cropland_acres_owned = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(99999)])
    cropland_acres_rented = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(99999)])
    cash_rented_acres = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(99999)])
    var_rent_cap_floor_frac = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(1)],
        verbose_name="variable rent floor/cap",
        help_text=("Floor and cap on variable rent as a percent of starting base rent"))
    annual_land_int_expense = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="land interest expense",
        help_text="Annual owned land interest expense")
    annual_land_principal_pmt = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="land principal payment",
        help_text="Annual owned land principal payment")
    property_taxes = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],)
    land_repairs = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],)
    eligible_persons_for_cap = models.SmallIntegerField(
        default=1, validators=[MinVal(0), MaxVal(3)],
        verbose_name="# persons for cap",
        help_text="Number of eligible 'persons' for FSA payment caps.")
    other_nongrain_income = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],)
    other_nongrain_expense = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='farm_years')

    # Note: we don't reproduce state of the model as of this date.  User choices do
    # not change.  We set futures prices, possibly price volatility
    # and projected price and some other fields (e.g. MYA price) according to this date.
    # Since we don't have pricing before January 2023 or after the current date, the
    # model run date must be clamped between these values.
    # At some point we may want to trigger an update based on this field changing.
    # Should it be inactive for old crop years?
    model_run_date = models.DateField(
        default=datetime.today,  # TODO: validate range
        help_text=('The date for which "current" futures prices and other ' +
                   'date-specific values are looked up.'))
    is_model_run_date_manual = models.BooleanField(
        default=False,
        help_text='Set the model run date manually (advanced).')
    price_factor = models.FloatField(
        default=1, validators=[MinVal(0), MaxVal(10)],
        verbose_name='price sensititivity factor')
    yield_factor = models.FloatField(
        default=1, validators=[MinVal(0), MaxVal(2)],
        verbose_name='yield sensititivity factor')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.totalplantedacres = None

    def report_type_name(self):
        return dict(FarmYear.REPORT_TYPES)[self.report_type]

    def get_model_run_date(self):
        # TODO: add logic to handle old farm years
        if not self.is_model_run_date_manual:
            self.model_run_date = datetime.today().date()
        return (self.model_run_date.date() if hasattr(self.model_run_date, 'date') else
                self.model_run_date)

    def wasde_first_mya_release_on(self):
        return datetime(self.crop_year, 5, 10).date()

    @property
    def full_name(self):
        return f'{self.farm_name} ({self.crop_year} Crop Year)'

    def __str__(self):
        return self.full_name

    def location(self):
        county_name = County.objects.get(
            state_id=self.state, code=self.county_code).name
        return f'{county_name} County {self.state}'

    def total_planted_acres(self):
        if self.totalplantedacres is None:
            self.totalplantedacres = sum((fc.planted_acres
                                          for fc in self.farm_crops.all()))
        return self.totalplantedacres

    def add_insurable_farm_crops(self):
        """
        Add farm crops, market crops and fsa crops to the farm year based on the
        insurable crops, types and practices for the county
        """
        from . import fsa_crop as fsacrop
        from . import market_crop as marketcrop
        from . import farm_crop as farmcrop
        fsas = {}
        mkts = {}
        for row in (InsurableCropsForCty.objects
                    .filter(state_id=self.state_id, county_code=self.county_code)
                    .order_by('id')):
            fct = FarmCropType.objects.get(
                ins_crop_id=row.crop_id, is_winter=row.crop_type_id == 11,
                is_fac=row.is_fac)
            mktct = MarketCropType.objects.get(pk=fct.market_crop_type_id)
            fsact = FsaCropType.objects.get(pk=mktct.fsa_crop_type_id)
            if mktct.id in mkts:
                mkt = mkts[mktct.id]
            else:
                if fsact.id in fsas:
                    fsa = fsas[fsact.id]
                else:
                    fsa = fsacrop.FsaCrop.objects.create(
                        farm_year=self, fsa_crop_type=fsact)
                    fsas[fsact.id] = fsa
                mkt = marketcrop.MarketCrop.objects.create(
                    farm_year=self, market_crop_type=mktct, fsa_crop=fsa)
                mkts[mktct.id] = mkt

            insdt = InsuranceDates.objects.get(
                state_id=self.state_id, county_code=self.county_code,
                market_crop_type_id=mktct.id)
            proj_price_disc_end = insdt.proj_price_disc_end
            harv_price_disc_end = insdt.harv_price_disc_mth_end
            cty_yield_final = datetime(self.crop_year+1,
                                       (4 if mktct.id in (3, 4) else 6), 16).date()
            farmcrop.FarmCrop.objects.create(
                farm_year=self, ins_crop_type_id=row.crop_type_id,
                farm_crop_type=fct, market_crop=mkt, ins_practices=row.practices,
                ins_practice=row.practices[0], proj_price_disc_end=proj_price_disc_end,
                harv_price_disc_end=harv_price_disc_end,
                cty_yield_final=cty_yield_final)

    def calc_gov_pmt(self, pf=None, yf=None, is_per_acre=False):
        """
        Compute the total, capped government payment and cache apportioned values
        in the corresponding FSA crops.
        ALWAYS call this method, before reading the values from the FSA crops, since
        no cache invalidation is performed.
        """
        if pf is None:
            pf = self.price_factor
        if yf is None:
            yf = self.price_factor
        if self.get_model_run_date() < self.wasde_first_mya_release_on():
            mya_prices = MyaPreEstimate.get_mya_pre_estimate(
                self.crop_year, self.get_model_run_date(), pf=pf)
        else:
            mya_prices = MyaPost.get_mya_post_estimate(
                self.crop_year, self.get_model_run_date(), pf=pf)
        total = sum((fc.gov_payment(mya_prices[i], yf=yf)
                     for i, fc in enumerate(self.fsa_crops.all())))
        total_pmt = round(
            min(FarmYear.FSA_PMT_CAP_PER_PRINCIPAL * self.eligible_persons_for_cap,
                total * (1 - GovPmt.SEQUEST_FRAC)))
        result = total_pmt / self.total_planted_acres() if is_per_acre else total_pmt
        return result

    # -----------------------
    # Expense-related methods
    # -----------------------
    def total_owned_land_expense(self, include_principal=False):
        return (self.annual_land_int_expense + self.property_taxes + self.land_repairs +
                self.annual_land_principal_pmt if include_principal else 0)

    def frac_var_rent(self):
        return (0 if self.cropland_acres_rented == 0 else
                (self.cropland_acres_rented - self.cash_rented_acres) /
                self.cropland_acres_rented)

    # ---------------------
    # Validation and saving
    # ---------------------

    def clean(self):
        first_date = datetime(self.crop_year, 1, 11).date()
        last_date = (datetime.now() + timedelta(days=1)).date()
        isdatetime = hasattr(self.model_run_date, 'date')
        model_run_date = (self.model_run_date.date() if isdatetime else
                          self.model_run_date)
        if model_run_date < first_date:
            raise ValidationError({'model_run_date': _(
                "The earliest a model run date can be set " +
                "is Jan 11 of the crop year.")})
        if model_run_date > last_date:
            raise ValidationError({'model_run_date': _(
                "The model run date cannot be in the future.")})

    def save(self, *args, **kwargs):
        if (self._state.adding and
            FarmYear.objects.filter(crop_year=util.get_current_year(),
                                    user=self.user).count() >= 10):
            raise PermissionDenied('A user can have at most 10 farms for a crop year')
        super().save(*args, **kwargs)
        if self.farm_crops.count() == 0:
            self.add_insurable_farm_crops()
            self.save()

    class Meta:
        constraints = [
            models.UniqueConstraint('farm_name', 'user', 'crop_year',
                                    name='farm_name_unique_for_user_crop_year'), ]
        ordering = ['-crop_year', 'farm_name']


class BaselineFarmYear(models.Model):
    """
    When a user sets the baseline for a farm year, all values (fields and method
    results) for the farmyear will be copied to the record in baselines table
    which references the farm year.  The baseline has a similar structure to the
    FarmYear, but all its associated models have only fields and no methods.
    """
    farm_year = models.ForeignKey(FarmYear, on_delete=models.CASCADE)
