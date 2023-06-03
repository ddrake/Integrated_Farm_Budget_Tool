from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import models
from django.db.models import Q
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from django.utils.functional import lazy
from ext.models import (
    State, County, Subcounty, InsurableCropsForCty, SubcountyAvail,
    ReferencePrices, MyaPreEstimate, MyaPostEstimate, FuturesPrice,
    Budget, BudgetCrop, FarmCropType, MarketCropType, FsaCropType,
    InsCropType, PricePrevyear)
from core.models.premium import Premium
from core.models.gov_pmt import GovPmt
from core.models.indemnity import Indemnity
from .validators import validate_range


def get_current_year():
    return timezone.now().year


def any_changed(instance, *fields):
    """
    Check an instance to see if the values of any of the listed fields changed.
    """
    if not instance.pk:
        return False
    dbinst = instance.__class__._default_manager.get(pk=instance.pk)
    return any((getattr(dbinst, field) != getattr(instance, field)
                for field in fields))


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
    crop_year = models.SmallIntegerField(default=get_current_year)
    report_type = models.SmallIntegerField(
        default=0, choices=REPORT_TYPES,
        help_text=("Pre-Tax cash flow deducts land debt interest and principal " +
                   "payments. Pre-tax Income deducts only interest expense."))
    cropland_acres_owned = models.FloatField(
        default=0, validators=[validate_range(high=99999)])
    cropland_acres_rented = models.FloatField(
        default=0, validators=[validate_range(high=99999)])
    cash_rented_acres = models.FloatField(
        default=0, validators=[validate_range(high=99999)])
    var_rent_cap_floor_frac = models.FloatField(
        default=0, validators=[validate_range(high=1)],
        verbose_name="variable rent floor/cap",
        help_text=("Floor and cap on variable rent as a percent of starting base rent"))
    annual_land_int_expense = models.FloatField(
        default=0, validators=[validate_range(high=999999)],
        verbose_name="land interest expense",
        help_text="Annual owned land interest expense")
    annual_land_principal_pmt = models.FloatField(
        default=0, validators=[validate_range(high=999999)],
        verbose_name="land principal payment",
        help_text="Annual owned land principal payment")
    property_taxes = models.FloatField(
        default=0, validators=[validate_range(high=999999)],)
    land_repairs = models.FloatField(
        default=0, validators=[validate_range(high=999999)],)
    eligible_persons_for_cap = models.SmallIntegerField(
        default=0, validators=[validate_range(high=3)],
        verbose_name="# persons for cap",
        help_text="Number of eligible 'persons' for FSA payment caps.")
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
        default=timezone.now,  # TODO: validate range
        help_text=('The date for which "current" futures prices and other ' +
                   'date-specific values are looked up.'))
    price_factor = models.FloatField(
        default=1, validators=[validate_range(high=10)],
        verbose_name='price sensititivity factor')
    yield_factor = models.FloatField(
        default=1, validators=[validate_range(high=2)],
        verbose_name='yield sensititivity factor')

    def wasde_first_mya_release_on(self):
        return timezone.datetime(self.crop_year, 5, 10).date()

    def rma_discovery_complete_on(self):
        return timezone.datetime(self.crop_year, 3, 1).date()

    def is_post_discovery_end(self):
        return self.model_run_date >= self.rma_discovery_complete_on()

    @property
    def full_name(self):
        return f'{self.farm_name} ({self.crop_year} Crop Year)'

    def __str__(self):
        return self.full_name

    def location(self):
        county_name = County.objects.get(
            state_id=self.state, code=self.county_code).name
        return f'{county_name} County {self.state}'

    def add_insurable_farm_crops(self):
        """
        Add farm crops, market crops and fsa crops to the farm year based on the
        insurable crops, types and practices for the county
        """
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
                    fsa = FsaCrop.objects.create(farm_year=self, fsa_crop_type=fsact)
                    fsas[fsact.id] = fsa
                mkt = MarketCrop.objects.create(
                    farm_year=self, market_crop_type=mktct, fsa_crop=fsa)
                mkts[mktct.id] = mkt
            FarmCrop.objects.create(
                farm_year=self, ins_crop_type_id=row.crop_type_id,
                farm_crop_type=fct, market_crop=mkt, ins_practices=row.practices,
                ins_practice=row.practices[0])

    def calc_gov_pmt(self, pf=None, yf=None):
        """
        Government Payments AB60: Sensitized total government payment after
        application of cap
        """
        if pf is None:
            pf = self.price_factor

        if yf is None:
            yf = self.price_factor

        if self.model_run_date < self.wasde_first_mya_release_on():
            mya_prices = MyaPreEstimate.get_mya_pre_estimate(
                self.crop_year, self.model_run_date, pf)
        else:
            mya_prices = MyaPostEstimate.get_mya_post_estimate(
                self.crop_year, self.model_run_date, pf)
        mya_prices = {k: v for k, v in zip([1, 2, 3], mya_prices)}
        total = 0
        for fc in self.fsa_crops.all():
            mya_price = mya_prices[fc.fsa_crop_type.id]
            total += fc.gov_payment(mya_price, self.model_run_date,  pf, yf)
        total_pmt = round(
            min(FarmYear.FSA_PMT_CAP_PER_PRINCIPAL * self.eligible_persons_for_cap,
                total * (1 - GovPmt.SEQUEST_FRAC)))
        self.apportion_gov_pmt(total_pmt)
        return total_pmt

    def total_planted_acres(self):
        return sum((fc.planted_acres for fc in self.farm_crops.all()))

    def apportion_gov_pmt(self, total_pmt):
        """
        Apportion the government payment among farm crops based on acres, caching
        these values in farm crops.
        """
        total_acres = self.total_planted_acres()
        if total_acres == 0:
            return
        for fc in self.farm_crops.all():
            fc.gov_pmt_portion = fc.planted_acres * total_pmt / total_acres
            print('saving', fc, fc.gov_pmt_portion)
            fc.save()

    def has_ins_price_period_changed(self):
        if not self.pk:
            return False
        db_mrd = FarmYear.objects.get(pk=self.pk).model_run_date
        mrd = self.model_run_date
        rma_end = self.rma_discovery_complete_on()
        return (db_mrd < rma_end <= mrd or mrd < rma_end <= db_mrd)

    def save(self, *args, **kwargs):
        if (self._state.adding and
            FarmYear.objects.filter(crop_year=get_current_year(),
                                    user=self.user).count() >= 10):
            raise PermissionDenied('A user can have at most 10 farms for a crop year')
        super().save(*args, **kwargs)
        if self.farm_crops.count() == 0:
            self.add_insurable_farm_crops()
            self.save()
        if self.has_ins_price_period_changed():
            for fc in self.farm_crops:
                fc.save(price_period_changed=True)

    class Meta:
        constraints = [
            models.UniqueConstraint('farm_name', 'user', 'crop_year',
                                    name='farm_name_unique_for_user_crop_year'),
        ]


class BaselineFarmYear(models.Model):
    """
    When a user sets the baseline for a farm year, all values (fields and method
    results) for the farmyear will be copied to the record in baselines table
    which references the farm year.  The baseline has a similar structure to the
    FarmYear, but all its associated models have only fields and no methods.
    """
    farm_year = models.ForeignKey(FarmYear, on_delete=models.CASCADE)


class FsaCrop(models.Model):
    """
    Priced crop-specific operator input data.  A FsaCrop has many FarmCrops so we
    should be able to get totals pretty easily.
    """
    plc_base_acres = models.FloatField(
        default=0, validators=[validate_range(high=99999)],
        verbose_name="Base acres in PLC")
    arcco_base_acres = models.FloatField(
        default=0,  validators=[validate_range(high=99999)],
        verbose_name="Base acres in ARC-CO")
    plc_yield = models.FloatField(
        default=0, validators=[validate_range(high=400)],
        verbose_name="farm avg. PLC yield",
        help_text="Weighted average PLC yield for farm in bushels per acre.")
    farm_year = models.ForeignKey(FarmYear, on_delete=models.CASCADE,
                                  related_name='fsa_crops')
    fsa_crop_type = models.ForeignKey(FsaCropType, on_delete=models.CASCADE)

    def estimated_county_yield(self):
        """
        Needed for gov_pmt.
        Get weighted average of market crop county yields
        """
        mcdata = [(mc.planted_acres(), mc.estimated_county_yield())
                  for mc in self.market_crops.all()]
        acres, _ = zip(*mcdata)
        if sum(acres) == 0:
            return 0
        return sum((ac*yld for ac, yld in mcdata)) / sum(acres)

    def planted_acres(self):
        return sum((mc.planted_acres() for mc in self.market_crops.all()))

    def is_irrigated(self):
        irr_acres = sum((mc.planted_acres() * (1 if mc.is_irrigated() else 0)
                         for mc in self.market_crops.all()))
        return irr_acres > self.planted_acres() / 2

    def gov_payment(self, sens_mya_price, priced_on, pf=1, yf=1):
        rp = ReferencePrices.objects.get(
            fsa_crop_type_id=self.fsa_crop_type_id,
            crop_year=self.farm_year.crop_year)
        gp = GovPmt(
            self.farm_year.crop_year, self.farm_year.state.id,
            self.farm_year.county_code, self.fsa_crop_type_id,
            self.is_irrigated(), self.plc_base_acres,
            self.arcco_base_acres, self.plc_yield, self.estimated_county_yield(),
            rp.effective_ref_price, rp.natl_loan_rate, sens_mya_price)
        return gp.prog_pmt_pre_sequest(pf, yf)

    def harvest_futures_price(self, priced_on, pf=1):
        """
        Since a farmer could have both winter and spring wheat, with different
        prices, we need some kind of average of market prices here.  A simple
        average should do for now.
        """
        prices = [p.harvest_futures_price_info(priced_on, price_only=True)
                  for p in self.market_crops.all()]
        return sum(prices)/len(prices) * pf

    def __str__(self):
        return f'{self.fsa_crop_type}'


class BaselineFsaCrop(models.Model):
    farm_year = models.ForeignKey(BaselineFarmYear, on_delete=models.CASCADE)
    fsa_crop_type = models.ForeignKey(FsaCropType, on_delete=models.CASCADE)


class MarketCrop(models.Model):
    """
    A crop which can be marketed and which has a unique set of futures prices
    for a given county.
    """
    contracted_bu = models.FloatField(
        default=0, validators=[validate_range(high=999999)],
        verbose_name="contracted bushels",
        help_text="Current contracted bushels on futures.")
    avg_contract_price = models.FloatField(
        default=0, validators=[validate_range(high=30)],
        verbose_name="avg. contract price",
        help_text="Average price for futures contracts.")
    basis_bu_locked = models.FloatField(
        default=0, validators=[validate_range(high=999999)],
        verbose_name="bushels with basis locked",
        help_text="Number of bushels with contracted basis set.")
    avg_locked_basis = models.FloatField(
        default=0, validators=[validate_range(low=-2, high=2)],
        verbose_name="avg. locked basis",
        help_text="Average basis on basis contracts in place.")
    assumed_basis_for_new = models.FloatField(
        default=0, validators=[validate_range(low=-2, high=2)],
        help_text="Assumed basis for non-contracted bushels.")
    farm_year = models.ForeignKey(FarmYear, on_delete=models.CASCADE,
                                  related_name='market_crops')
    market_crop_type = models.ForeignKey(MarketCropType, on_delete=models.CASCADE)
    fsa_crop = models.ForeignKey(FsaCrop, on_delete=models.CASCADE,
                                 related_name='market_crops')

    def __str__(self):
        return f'{self.market_crop_type}'

    def harvest_futures_price_info(self, priced_on, price_only=False):
        """
        Get the harvest price for the given date from the correct exchange for the
        crop type and county.  Note: insurancedates gives the exchange and ticker.
        """
        rec = FuturesPrice.objects.raw("""
        SELECT fp.id, fp.croptype, fp.exchange, fp.futures_month, fp.ticker,
               fp.priced_on, fp.price, idt.crop_year, idt.state_id, idt.county_code,
               idt.market_crop_type_id
            FROM ext_futuresprice fp
            INNER JOIN ext_insurancedates idt
            ON fp.ticker = idt.ticker
            where crop_year=%s and state_id=%s and county_code=%s
            and fp.market_crop_type_id=%s and fp.priced_on <= %s
            order by priced_on desc limit 1;
        """, params=[self.farm_year.crop_year, self.farm_year.state_id,
                     self.farm_year.county_code, self.market_crop_type_id,
                     priced_on])[0]
        return rec.price if price_only else rec

    def is_irrigated(self):
        irr_acres = sum((fc.planted_acres * (1 if fc.is_irrigated() else 0)
                         for fc in self.farm_crops.all()))
        return irr_acres > self.planted_acres() / 2

    def planted_acres(self):
        return sum((fc.planted_acres for fc in self.farm_crops.all()))

    def estimated_county_yield(self):
        """
        Needed for gov_pmt.
        Get weighted average of market crop county yields
        """
        acre_sum = self.planted_acres()
        if acre_sum == 0:
            return 0
        return (sum((ac*yld for ac, yld in
                     ((fc.planted_acres, fc.estimated_county_yield())
                      for fc in self.farm_crops.all()))) / acre_sum)


class BaselineMarketCrop(models.Model):
    market_crop_type = models.ForeignKey(MarketCropType, on_delete=models.CASCADE)
    farm_year = models.ForeignKey(BaselineFarmYear, on_delete=models.CASCADE,
                                  related_name='market_crops')
    fsa_crop = models.ForeignKey(BaselineFsaCrop, on_delete=models.CASCADE,
                                 related_name='market_crops')


class FarmCrop(models.Model):
    """
    Farm crop-specific data.  A column in the operator input sheet.
    It holds references to the associated fsa_crop and farm_year models
    for convenience.
    Its name is just the name of its farm_crop_type (TODO: add method)
    We can get its crop insurance type from the farm_crop_type.
    We can infer its crop insurance practice from its is_irrigated
    and its farm_crop_type is_fac properties.
    We (re)compute and store all premiums only if the crop, practice, type or subcounty
    changes (or if the state or county is changed).  A change in user selections,
    e.g. coverage_type or level is just a quick lookup.
    Todo: Change premiums.py so it returns nested lists instead of numpy arrays.
    """
    COUNTY = 0
    FARM = 1
    COVERAGE_TYPES = [(0, 'County (area)'), (1, 'Farm (enterprise)'), ]
    PRODUCT_TYPES = [(0, 'RP'), (1, 'RP-HPE'), (2, 'YP'), ]
    COVERAGE_LEVELS_F = [
        (.5, '50%'), (.55, '55%'), (.6, '60%'), (.65, '65%'),
        (.7, '70%'), (.75, '75%'), (.8, '80%'), (.85, '85%'),
    ]
    COVERAGE_LEVELS_C = [
        (.7, '70%'), (.75, '75%'), (.8, '80%'), (.85, '85%'), (.9, '90%'), ]
    COVERAGE_LEVELS_ECO = [(.9, '90%'), (.95, '95%'), ]

    @classmethod
    def add_farm_budget_crop(cls, farm_crop_id, budget_crop_id):
        FarmBudgetCrop.objects.filter(farm_crop=farm_crop_id).delete()
        bc = BudgetCrop.objects.get(pk=budget_crop_id)
        d = {k: v for k, v in bc.__dict__.items() if k not in ['_state', 'id']}
        d['county_yield'] = d['farm_yield']
        d['farm_crop_id'] = farm_crop_id
        d['farm_year_id'] = FarmCrop.objects.get(pk=farm_crop_id).farm_year_id
        d['budget_crop_id'] = budget_crop_id
        FarmBudgetCrop.objects.create(**d)

    planted_acres = models.FloatField(
        default=0, validators=[validate_range(high=99999)],)
    ta_aph_yield = models.FloatField(
        default=0, validators=[validate_range(high=400)], verbose_name="TA APH yield",
        help_text="Trend-adjusted average prodution history yield provided by insurer.")
    adj_yield = models.FloatField(
        default=0, validators=[validate_range(high=400)], verbose_name="Adjusted yield",
        help_text="Adjusted yield provided by insurer.")
    rate_yield = models.FloatField(
        default=0, validators=[validate_range(high=400)],
        help_text="Rate yield provided by insurer.")
    ye_use = models.BooleanField(
        default=False, verbose_name='use YE?',
        help_text="Use yield exclusion option? (e.g. exclude 2012 yields)")
    ta_use = models.BooleanField(
        default=False, verbose_name='use TA?',
        help_text="Use trend adjustment option? (apply a trend adjustment to yields).")
    subcounty = models.CharField(
        max_length=8, blank=True, verbose_name="risk class", default='',
        choices=[(v[0], v[0]) for v in Subcounty.objects.all().values_list('id')],
        help_text="Primary risk class (subcounty ID) provided by crop insurer")
    # TODO: we should give the user sensible defaults for these during the period
    # when they are required (prior year value for price volatility and board price
    # for projected price) and hide the form fields once they are known.
    rma_cty_expected_yield = models.FloatField(
        null=True, blank=True,
        validators=[validate_range(high=400)],
        verbose_name="RMA county expected yield",
        help_text="The RMA expected yield for the county if available")
    coverage_type = models.SmallIntegerField(
        choices=COVERAGE_TYPES, null=True, blank=True,
        help_text="Crop insurance coverage type.")
    product_type = models.SmallIntegerField(
        choices=PRODUCT_TYPES, null=True, blank=True,
        help_text="Crop insurance product type.")
    # TODO: use Javascript/AJAX to set choices based on coverage type
    base_coverage_level = models.FloatField(
        null=True, blank=True, choices=COVERAGE_LEVELS_F,
        help_text="Coverage level for selected crop insurance product.")
    sco_use = models.BooleanField(
        default=False, verbose_name="add SCO option?",
        help_text="Add Supplemental coverage option to bring coverage level to 86%?")
    eco_level = models.FloatField(
        null=True, blank=True, choices=COVERAGE_LEVELS_ECO,
        verbose_name="ECO level", help_text="Enhanced coverage level")
    prot_factor = models.FloatField(
        default=1, validators=[validate_range(high=1)],
        verbose_name="selected payment factor",
        help_text="Selected payment factor for county premiums/indemnities.")
    farm_crop_type = models.ForeignKey(FarmCropType, on_delete=models.CASCADE)
    market_crop = models.ForeignKey(MarketCrop, on_delete=models.CASCADE,
                                    related_name='farm_crops')
    farm_year = models.ForeignKey(FarmYear, on_delete=models.CASCADE,
                                  related_name='farm_crops')
    crop_ins_prems = models.JSONField(null=True, blank=True)
    # holds currently selected practice
    # TODO: May need to replace the choices for subcounty if this changes.
    # If so, the currently selected subcounty might need to be cleared (if it's
    # not in the updated choices list.
    ins_crop_type = models.ForeignKey(InsCropType, on_delete=models.CASCADE,
                                      related_name='farm_crop_types')
    ins_practice = models.SmallIntegerField(
        verbose_name='Irrigated?', choices=list(FarmYear.IRR_PRACTICE.items()),
        blank=False)
    ins_practices = ArrayField(models.SmallIntegerField(), null=True)

    # Cached portion of gov payment (set by method in FarmYear)
    gov_pmt_portion = models.FloatField(null=True, blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._meta.get_field('ins_practice').choices = lazy(
            self.ins_practice_choices, list)()

    def __str__(self):
        irr = 'Irrigated' if self.is_irrigated() else 'Non-irrigated'
        return f'{self.farm_crop_type}, {irr}'

    def is_irrigated(self):
        return FarmYear.IRR_PRACTICE[self.ins_practice] == 'Irrigated'

    def ins_practice_choices(self):
        return [(p, FarmYear.IRR_PRACTICE[p]) for p in self.ins_practices]

    def farm_expected_yield(self):
        """
        Computed from budget crops farm yield, county yield and rotating acres
        """
        return (self.farmbudgetcrop.farm_yield if self.has_budget()
                else self.ta_aph_yield)

    def cty_expected_yield(self):
        return (self.farmbudgetcrop.county_yield if self.has_budget()
                else self.ta_aph_yield)

    def prev_year_price_vol(self):
        """
        Return the default price volatility factor (the previous year's value)
        """
        return PricePrevyear.objects.get(
            state_id=self.farm_year.state_id, county_code=self.farm_year.county_code,
            crop_id=self.farm_crop_type.ins_crop_id,
            crop_type_id=self.ins_crop_type_id).price_volatility_factor

    def proj_harv_price(self):
        """
        Return the default projected harvest price and cache its value for indemnity.
        If we are post_discovery_end, the cached value will be overridden by set_prems.
        """
        self.proj_harv_price = self.harvest_price()
        return self.proj_harv_price

    def save(self, *args, **kwargs):
        price_period_changed = (kwargs.get('price_period_changed', False))
        if (self.planted_acres > 0 and self.rate_yield > 0 and self.adj_yield > 0
            and self.ta_aph_yield > 0 and
            (any_changed(self, 'ins_practice', 'rate_yield', 'adj_yield',
                         'ta_aph_yield', 'planted_acres', 'ta_use', 'ye_use',
                         'prot_factor', 'subcounty') or price_period_changed)):
            self.set_prems()
        super().save(*args, **kwargs)

    def set_prems(self):
        p = Premium()
        prems = p.compute_prems(
            state=self.farm_year.state_id,
            county=self.farm_year.county_code,
            crop=self.farm_crop_type.ins_crop_id,
            croptype=self.ins_crop_type_id,
            practice=self.ins_practice,
            rateyield=self.rate_yield,
            adjyield=self.adj_yield,
            tayield=self.ta_aph_yield,
            acres=self.planted_acres,
            tause=self.ta_use,
            yieldexcl=self.ye_use,
            prot_factor=self.prot_factor,
            price_volatility_factor=self.prev_year_price_vol(),
            projected_price=self.proj_harv_price(),
            subcounty=None if self.subcounty == '' else self.subcounty,
            is_post_discovery=self.farm_year.is_post_discovery_end(), )
        if prems is not None:
            names = 'Farm County SCO ECO'.split()
            self.crop_ins_prems = {key: None if ar is None else ar.tolist()
                                   for key, ar in zip(names, prems[:4])}
            self.proj_harv_price = prems[4]
            self.rma_cty_expected_yield = prems[5]

    def harvest_price(self):
        return self.market_crop.harvest_futures_price_info(
            self.farm_year.model_run_date, price_only=True)

    def get_indemnities(self, pf=1, yf=1):
        if self.proj_harv_price is None:
            return 0
        indem = Indemnity(
            self.ta_aph_yield, self.proj_harv_price, self.harvest_price(),
            self.rma_cty_expected_yield, self.prot_factor,
            self.farm_expected_yield(), self.cty_expected_yield())
        indems = indem.compute_indems(pf, yf)
        names = 'Farm County SCO ECO'.split()
        return {key: None if ar is None else ar.tolist()
                for key, ar in zip(names, indems)}

    def allowed_subcounties(self):
        values = SubcountyAvail.objects.filter(
            state_id=self.farm_year.state_id, county_code=self.farm_year.county_code,
            crop_id=self.farm_crop_type.ins_crop,
            croptype_id=self.ins_crop_type,
            practice=self.ins_practice).values_list('subcounty_id')
        return [('', '-'*9)] + [(v[0], v[0]) for v in values]

    def allowed_practices(self):
        return [(prac, FarmYear.IRR_PRACTICE[prac]) for prac in self.ins_practices]

    def get_budget_crops(self):
        return [(it.id, str(it)) for it in
                BudgetCrop.objects.filter(farm_crop_type_id=self.farm_crop_type,
                                          is_irr=self.is_irrigated())]

    def has_budget(self):
        try:
            self.farmbudgetcrop
            return True
        except ObjectDoesNotExist:
            return False

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(prot_factor__gte=0) & Q(prot_factor__lte=1),
                name="prot_factor_in_range")
        ]


class BaselineFarmCrop(models.Model):
    farm_crop_type = models.ForeignKey(FarmCropType, on_delete=models.CASCADE)
    market_crop = models.ForeignKey(BaselineMarketCrop, on_delete=models.CASCADE,
                                    related_name='farm_crops')
    farm_year = models.ForeignKey(BaselineFarmYear, on_delete=models.CASCADE,
                                  related_name='farm_crops')


class FarmBudgetCrop(models.Model):
    """
    A possibly user-modfied copy of a budget column named by its budget_crop_type name.
    Cost items are in dollars per acre.  One or two (rotated/non-rotated) budget crops
    are assigned To each farm crop based on matching the farm_crop_type and
    irrigated status of the farm crop to the buddget crop type.
    """
    farm_yield = models.FloatField(
        default=0, validators=[validate_range(high=400)])
    # the farm yield value is copied to county yield when the budget crop is copied.
    county_yield = models.FloatField(
        default=0, validators=[validate_range(high=400)])
    description = models.CharField(max_length=50)
    yield_variability = models.FloatField(
        default=0, validators=[validate_range(high=1)])
    other_gov_pmts = models.FloatField(
        default=0, validators=[validate_range(high=99999)])
    other_revenue = models.FloatField(
        default=0, validators=[validate_range(high=999999)])
    fertilizers = models.FloatField(
        default=0, validators=[validate_range(high=999999)])
    pesticides = models.FloatField(
        default=0, validators=[validate_range(high=999999)])
    seed = models.FloatField(
        default=0, validators=[validate_range(high=999999)])
    drying = models.FloatField(
        default=0, validators=[validate_range(high=999999)])
    storage = models.FloatField(
        default=0, validators=[validate_range(high=999999)])
    other_direct_costs = models.FloatField(
        default=0, validators=[validate_range(high=999999)],
        help_text="Other (hauling, custom operations)")
    machine_hire_lease = models.FloatField(
        default=0, validators=[validate_range(high=999999)],
        verbose_name="machine hire or lease")
    utilities = models.FloatField(
        default=0, validators=[validate_range(high=999999)])
    machine_repair = models.FloatField(
        default=0, validators=[validate_range(high=999999)])
    fuel_and_oil = models.FloatField(
        default=0, validators=[validate_range(high=999999)])
    light_vehicle = models.FloatField(
        default=0, validators=[validate_range(high=999999)])
    machine_depr = models.FloatField(
        default=0, validators=[validate_range(high=999999)],
        verbose_name="machine depreciation")
    labor_and_mgmt = models.FloatField(
        default=0, validators=[validate_range(high=999999)],
        verbose_name="labor and management")
    building_repair_and_rent = models.FloatField(
        default=0, validators=[validate_range(high=999999)])
    building_depr = models.FloatField(
        default=0, validators=[validate_range(high=999999)],
        verbose_name="building depreciation")
    insurance = models.FloatField(
        default=0, validators=[validate_range(high=999999)])
    misc_overhead_costs = models.FloatField(
        default=0, validators=[validate_range(high=999999)])
    interest_nonland = models.FloatField(
        default=0, validators=[validate_range(high=999999)],
        verbose_name="non-land interest cost")
    other_overhead_costs = models.FloatField(
        default=0, validators=[validate_range(high=999999)])
    rented_land_costs = models.FloatField(
        default=0, validators=[validate_range(high=9999999)])
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

    def __str__(self):
        rotstr = (' Rotating' if self.is_rot
                  else '' if self.is_rot is None else ' Continuous,')
        descr = '' if self.description == '' else f' {self.description},'
        return (f'{self.state.abbr},{descr}{rotstr}')


class BaselineFarmBudgetCrop(models.Model):
    farm_crop_type = models.ForeignKey(FarmCropType, on_delete=models.CASCADE)
    farm_crop = models.ForeignKey(BaselineFarmCrop, on_delete=models.CASCADE,
                                  related_name='budget_crops')
    orig_budget = models.ForeignKey(Budget, on_delete=models.SET_NULL, null=True)
