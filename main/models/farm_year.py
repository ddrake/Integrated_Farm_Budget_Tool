from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import (
    MinValueValidator as MinVal, MaxValueValidator as MaxVal)
from django.db import models
from django.utils.translation import gettext_lazy as _
from ext.models import (
    State, County, InsurableCropsForCty, MyaPreEstimate, MyaPost,
    FarmCropType, MarketCropType, FsaCropType, InsuranceDates, ReferencePrices)
from core.models.gov_pmt import GovPmt
from . import util


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
    cropland_acres_owned = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(99999)])
    variable_rented_acres = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(99999)],
        verbose_name="variable rent acres")
    cash_rented_acres = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(99999)],
        verbose_name="straight cash rent acres")
    var_rent_cap_floor_frac = models.FloatField(
        default=0, validators=[
            MinVal(0),
            MaxVal(1, message="Ensure this value is less than or equal to 100")],
        verbose_name="variable rent floor/cap",
        help_text=("Floor and cap on variable rent as a percent of starting base rent"))
    annual_land_int_expense = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="land interest expense",
        help_text="Annual owned land interest expense in dollars")
    annual_land_principal_pmt = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="land principal payment",
        help_text="Annual owned land principal payment in dollars")
    property_taxes = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        help_text="Annual property taxes in dollars")
    land_repairs = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        help_text="Annual land repair costs in dollars")
    eligible_persons_for_cap = models.SmallIntegerField(
        default=1, validators=[MinVal(0), MaxVal(10)],
        verbose_name="# entities for FSA cap",
        help_text="Number of eligible entities for FSA payment cap")
    other_nongrain_income = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="other nongrain revenue",
        help_text="Other non-grain revenue in dollars")
    other_nongrain_expense = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        help_text="Other non-grain expense in dollars")
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='farm_years')
    manual_model_run_date = models.DateField(
        default=datetime.today,
        help_text=(_('Manually-set date for which "current" futures prices<br>' +
                     'and other date-specific values are looked up.')))
    is_model_run_date_manual = models.BooleanField(
        default=False,
        help_text='Use the manually-set model run date (advanced).')
    sensitivity_data = models.JSONField(null=True, blank=True)
    est_sequest_frac = models.FloatField(
        default=0.062, validators=[
            MinVal(0),
            MaxVal(0.1, message="Ensure this value is less than or equal to 10")],
        verbose_name='estimated sequestration percent',
        help_text='Estimated reduction to computed total pre-cap title payment')
    # Dict of numerical data For computing variance or displaying benchmark budget.
    # Includes revenue values, but not key data.
    # This field is updated each time a budget is computed.
    current_budget_data = models.JSONField(null=True, blank=True)
    # If the user sets or updates the benchmark, we simply copy the current budget data
    # to the benchmark budget data.
    baseline_budget_data = models.JSONField(null=True, blank=True)
    # Dict of dicts with text and styles info.  Keys are 'cur', 'base' and 'var'
    # value for 'cur' is current budget; 'base' and 'var' values are initially None.
    # Each subdict contains all information (including revenue and key data) display or
    # print a "budget".
    # After user has set a baseline, subdicts for baseline 'base' and variance 'var'
    # are set to dicts in subsequent budget runs and stored for PDF generation.
    # It's not necessary to generate 'base' each run, since it only changes if the user
    # updates the baseline.
    # If the user updates the baseline, 'base' is
    # set to the value of 'cur' by the AJAX view code.
    budget_text = models.JSONField(null=True, blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.totalplantedacres = None
        self.totalnondcplantedacres = None
        self.facplantedacres = None

    def get_model_run_date(self):
        mmrd = self.manual_model_run_date
        if not self.is_model_run_date_manual:
            mmrd = datetime.today().date()
        return mmrd.date() if hasattr(mmrd, 'date') else mmrd

    def has_budget(self):
        return (self.budget_text is not None and
                self.budget_text['cur'] is not None)

    def has_baseline_budget(self):
        return (self.budget_text is not None and
                self.budget_text['base'] is not None)

    def update_baseline(self):
        """
        Called by POST from dashboard (button active after first budget run).
        Set or update the benchmark budget to the current budget data.
        Update the budget_text dict setting 'base' to 'cur'.
        I think there is no need to copy or deepcopy due to JSON conversion
        """
        self.baseline_budget_data = self.current_budget_data
        self.budget_text['base'] = self.budget_text['cur']
        self.save()

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
        return f'{county_name} County, {self.state}'

    def total_rented_acres(self):
        return self.cash_rented_acres + self.variable_rented_acres

    def total_farm_acres(self):
        return self.total_rented_acres() + self.cropland_acres_owned

    def total_planted_acres(self):
        if self.totalplantedacres is None:
            self.totalplantedacres = sum((fc.planted_acres
                                          for fc in self.farm_crops.all()))
        return self.totalplantedacres

    def fac_planted_acres(self):
        if self.facplantedacres is None:
            self.facplantedacres = sum((fc.planted_acres for fc in self.farm_crops.all()
                                        if fc.farm_crop_type.is_fac))
        return self.facplantedacres

    def total_fs_planted_acres(self):
        if self.totalnondcplantedacres is None:
            self.totalnondcplantedacres = sum((fc.planted_acres
                                               for fc in self.farm_crops.all()
                                               if not fc.farm_crop_type.is_fac))
        return self.totalnondcplantedacres

    def add_insurable_farm_crops(self):
        """
        Add farm crops, market crops and fsa crops to the farm year based on the
        insurable crops, types and practices for the county
        """
        from .fsa_crop import FsaCrop
        from .market_crop import MarketCrop
        from .farm_crop import FarmCrop
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
                    rp = ReferencePrices.objects.filter(crop_year=self.crop_year,
                                                        fsa_crop_type=fsact)[0]
                    fsa = FsaCrop.objects.create(
                        farm_year=self, fsa_crop_type=fsact,
                        effective_ref_price=rp.effective_ref_price,
                        natl_loan_rate=rp.natl_loan_rate
                    )
                    fsas[fsact.id] = fsa
                mkt = MarketCrop.objects.create(
                    farm_year=self, market_crop_type=mktct, fsa_crop=fsa)
                mkts[mktct.id] = mkt

            insdt = InsuranceDates.objects.get(
                state_id=self.state_id, county_code=self.county_code,
                market_crop_type_id=mktct.id, crop_year=self.crop_year)
            proj_price_disc_end = insdt.proj_price_disc_end
            harv_price_disc_end = insdt.harv_price_disc_mth_end
            cty_yield_final = datetime(self.crop_year+1,
                                       (4 if mktct.id in (3, 4) else 6), 16).date()
            FarmCrop.objects.create(
                farm_year=self, ins_crop_type_id=row.crop_type_id,
                farm_crop_type=fct, market_crop=mkt, ins_practices=row.practices,
                ins_practice=row.practices[0], proj_price_disc_end=proj_price_disc_end,
                harv_price_disc_end=harv_price_disc_end,
                cty_yield_final=cty_yield_final)

    def calc_gov_pmt(self, pf=None, yf=None, is_per_acre=False, mya_prices=None,
                     cty_yields=None):
        """
        Compute the total, capped government payment and cache apportioned values
        in the corresponding FSA crops.
        ALWAYS call this method, before reading the values from the FSA crops, since
        no cache invalidation is performed.
        If (pre-sensitized) mya_prices are provided, use them.
        """
        if mya_prices is None:
            if pf is None:
                pf = [fc.price_factor() for fc in self.fsa_crops.all()]
            mrd = self.get_model_run_date()
            if mrd < self.wasde_first_mya_release_on():
                mya_prices = MyaPreEstimate.get_mya_pre_estimates(
                    self.crop_year, mrd, pf=pf)
            else:
                mya_prices = MyaPost.get_mya_post_estimates(
                    self.crop_year, mrd, pf=pf)
        if cty_yields is None:
            if yf is None:
                yf = [fc.yield_factor() for fc in self.fsa_crops.all()]
            total = sum((fc.gov_payment(mya_prices[i], yf=yf[i])
                         for i, fc in enumerate(self.fsa_crops.all())))
        else:
            total = sum((fc.gov_payment(mya_prices[i], cty_yield=cty_yields[i])
                         for i, fc in enumerate(self.fsa_crops.all())))
        total_pmt = round(
            min(FarmYear.FSA_PMT_CAP_PER_PRINCIPAL * self.eligible_persons_for_cap,
                total * (1 - GovPmt.SEQUEST_FRAC)))
        return total_pmt / self.total_planted_acres() if is_per_acre else total_pmt

    # -----------------------
    # Expense-related methods
    # -----------------------
    def total_owned_land_expense(self):
        return (self.annual_land_int_expense + self.property_taxes + self.land_repairs +
                self.annual_land_principal_pmt)

    def frac_var_rent(self):
        rented = self.total_rented_acres()
        return 0 if rented == 0 else ((rented - self.cash_rented_acres) / rented)

    # ---------------------
    # Validation and saving
    # ---------------------

    def clean(self):
        mmrd = self.manual_model_run_date
        first_date = datetime(self.crop_year, 1, 11).date()
        last_date = (datetime.now() + timedelta(days=1)).date()
        isdatetime = hasattr(mmrd, 'date')
        model_run_date = mmrd.date() if isdatetime else mmrd
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
