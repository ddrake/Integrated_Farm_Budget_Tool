from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q
from django.utils import timezone
from ext.models import (State, Subcounty, InsCrop, InsCropType,
                        InsurableCropsForCty, SubcountyAvail)
from core.models.premium import Premium
from core.models.gov_pmt import GovPmt
from core.models.indemnity import Indemnity
from core.models.util import call_postgres_func


def get_current_year():
    return timezone.now().year


# ---------
# Farm Year
# ---------
class FarmYear(models.Model):
    """
    Holds non-crop-specific values for a crop year for a farm
    A user can have multiple FarmYears, including multiple farms for the
    same crop year, but we don't currently try to do any aggregation over
    a user's farms for a given crop year.
    A FarmYear has many FarmCrops and many FsaCrops so we should be able
    to add any needed totalizer methods.
    I think the farm year should include FarmCrops and FsaCrops if and
    only if they can be insured.  E.g. a Champaign County user would not
    see FAC beans.  A Madison County user would see that crop but could
    set the acres to zero if so desired.
    We may want to break out a form that lets the user first input a minimal
    set of data (farm_name, crop_year, state and county) sufficient for
    determining the set of insurable crops.
    We probably need a method that creates those insurable farm_crops
    with default values and associates them with the current instance.
    """
    FSA_PMT_CAP_PER_PRINCIPAL = 125000
    PRETAX_INCOME = 0
    PRETAX_CASH_FLOW = 1
    REPORT_TYPES = [(PRETAX_INCOME, 'Pre-tax income'),
                    (PRETAX_CASH_FLOW, 'Pre-tax cash flow')]
    farm_name = models.CharField(max_length=60)
    # TODO: We'll want to populate a counties drop-down via AJAX when the
    # user selects or changes the state.
    county_code = models.SmallIntegerField(
        verbose_name="primary county",
        help_text="The county where most farm acres are located")
    crop_year = models.SmallIntegerField(default=get_current_year)
    report_type = models.SmallIntegerField(
        default=0, choices=REPORT_TYPES,
        help_text=("Pre-Tax cash flow deducts land debt interest and principal " +
                   "payments. Pre-tax Income deducts only interest expense.")
    )
    cropland_acres_owned = models.FloatField(default=0)
    cropland_acres_rented = models.FloatField(default=0)
    cash_rented_acres = models.FloatField(default=0)
    var_rent_cap_floor_frac = models.FloatField(
        default=0, verbose_name="variable rent floor/cap",
        help_text=("Floor and cap on variable rent as a percent of starting base rent")
    )
    annual_land_int_expense = models.FloatField(
        default=0, verbose_name="land interest expense",
        help_text="Annual owned land interest expense")
    annual_land_principal_pmt = models.FloatField(
        default=0, verbose_name="land principal payment",
        help_text="Annual owned land principal payment")
    property_taxes = models.FloatField(default=0)
    land_repairs = models.FloatField(default=0)
    eligible_persons_for_cap = models.SmallIntegerField(
        default=0, verbose_name="# persons for cap",
        help_text="Number of eligible 'persons' for FSA payment caps.")
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # When a user sets the baseline for a crop year, copies are made of the farmyear and
    # all related model records and is_baseline is set True.  These records are never
    # updated, but remain a static snapshot.  In particular, prices are fixed.
    # If the user later chooses to set a new
    # baseline for the year, these records are deleted and replaced by the new baseline
    # records.  At any time, the user can view a report on variance with respect to
    # the baseline for the crop year.  Once a baseline has been set, some fields
    # e.g. planted acres, is_irr, should no longer be allowed to change.  I guess we
    # could warn, "If you change that value, your baseline budget will be deleted."
    # TODO: Add method create_baseline()
    is_baseline = models.BooleanField(default=False)
    master_farm_year = models.ForeignKey('FarmYear', on_delete=models.CASCADE,
                                         null=True, blank=True)
    # Note: we don't reproduce state of the model as of this date.  User choices do
    # not change.  We set futures prices, possibly price volatility
    # and projected price and some other fields (e.g. MYA price) according to this date.
    model_run_date = models.DateField(
        default=timezone.now,
        help_text=('The date for which "current" futures prices and other ' +
                   'date-specific values are looked up.'))
    price_factor = models.FloatField(default=1,
                                     verbose_name='price sensititivity factor')
    yield_factor = models.FloatField(default=1,
                                     verbose_name='yield sensititivity factor')

    @property
    def full_name(self):
        return f'{self.farm_name} ({self.crop_year} Crop Year)'

    def __str__(self):
        return self.full_name

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
                ins_crop_id=row.crop_id, ins_crop_type_id=row.crop_type_id,
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
                farm_year=self, farm_crop_type=fct, market_crop=mkt,
                ins_practices=row.practices, ins_practice=row.practices[0])

    def total_gov_pmt(self, pf=1, yf=1):
        """
        Government Payments AB60: Sensitized total government payment after
        application of cap
        """
        # TODO: store the pre_sequest amounts with fsa_crop_type so we can
        # apportion based on acres
        total = 0
        for pc in self.pricedcrops_set:
            total += pc.gov_payment(pf, yf)
        return round(
            min(FarmYear.FSA_PMT_CAP_PER_PRINCIPAL * self.number_of_principals,
                total * (1 - GovPmt.SEQUEST_FRAC)))

    def apportion_gov_pmt(self):
        """
        Apportion the government payment among priced crops based on acres.
        """
        # TODO:
        # def total_gov_pmt_crop(self, pf=1, yf=1):
        #     tot = self.total_gov_pmt(pf, yf)
        #     return (0 if tot == 0 else
        #             tot * self.prog_pmt_pre_sequest_crop(pf, yf) /
        #             self.prog_pmt_pre_sequest(pf, yf))

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.farmcrop_set.count() == 0:
            self.add_insurable_farm_crops()
            self.save()

    class Meta:
        constraints = [
            models.UniqueConstraint('farm_name', 'user', 'crop_year',
                                    name='farm_name_unique_for_user_crop_year'),
        ]


# -------------
# FSA Crop Type
# -------------
class FsaCropType(models.Model):
    """
    Aggregates for government payment, marketing assumptions, basis
    'Corn', 'Beans', 'Wheat'
    """
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class ReferencePrices(models.Model):
    """
    Reference prices needed to compute government payments
    """
    crop_year = models.SmallIntegerField()
    fsa_crop_type = models.ForeignKey(FsaCropType, on_delete=models.CASCADE)
    natl_loan_rate = models.FloatField()
    effective_ref_price = models.FloatField()


class MyaPreEstimate(models.Model):
    """
    Used to get sensitized MYA prices when the model_run_date is before
    the May WASDE report
    """
    crop_year = models.SmallIntegerField()
    month = models.SmallIntegerField()
    year = models.SmallIntegerField()
    actual_farm_price = models.FloatField(null=True)
    nearby_futures_month = models.CharField(max_length=8)
    five_year_avg_basis = models.FloatField()
    five_year_avg_weight = models.FloatField()
    fsa_crop_type = models.ForeignKey(FsaCropType, on_delete=models.CASCADE)

    def get_mya_pre_estimate(self, crop_year, for_date, pf=1):
        """
        Get the sensitized MYA prices for each FSA crop type for the crop year
        and the given date.
        """
        names = ('''corn_mya_price beans_mya_price wheat_mya_price''').split()
        cmd = 'SELECT ' + ', '.join(names) + """
                  FROM
                  public.main_mya_pre_estimate(%s, %s)
                  AS (corn_mya_price double precision, beans_mya_price double precision,
                      wheat_mya_price double precision);
              """
        record = call_postgres_func(cmd, crop_year, for_date)
        return tuple(None if it is None else float(it) * pf for it in record)


class MyaPostEstimate(models.Model):
    """
    Used to get sensitized MYA prices when the model_run_date is after
    the May WASDE report
    """
    crop_year = models.SmallIntegerField()
    forecast_month = models.CharField(max_length=8)
    wasde_release_date = models.DateField(verbose_name='WASDE release date')
    wasde_estimated_price = models.FloatField(null=True)
    assumed_pct_locked = models.FloatField()
    fsa_crop_type = models.ForeignKey(FsaCropType, on_delete=models.CASCADE)

    def get_mya_post_estimate(self, crop_year, for_date, pf=1):
        """
        Get the sensitized MYA prices for each FSA crop type for the crop year
        and the given date.
        """
        rows = (MyaPostEstimate.objects
                .filter(wasde_release_date__lte=for_date, crop_year=crop_year)
                .order_by("-wasde_release_date", "fsa_crop_type")[:3])
        mya_prices = [row.wasde_estimated_price *
                      (row.assumed_pct_locked + pf * (1 - row.assumed_pct_locked))
                      for row in rows]
        return mya_prices


class FsaCrop(models.Model):
    """
    Priced crop-specific operator input data.  A FsaCrop has many FarmCrops so we
    should be able to get totals pretty easily.
    """
    plc_base_acres = models.FloatField(default=0, verbose_name="Base acres in PLC")
    arcco_base_acres = models.FloatField(default=0, verbose_name="Base acres in ARC-CO")
    plc_yield = models.FloatField(
        default=0, verbose_name="farm avg. PLC yield",
        help_text="Weighted average PLC yield for farm in bushels per acre.")
    farm_year = models.ForeignKey(FarmYear, on_delete=models.CASCADE)
    fsa_crop_type = models.ForeignKey(FsaCropType, on_delete=models.CASCADE)

    def get_projected_mya_price(self):
        """
        Use the fancy new logic for this...
        """
        # TODO: implement this.

    def estimated_county_yield(self):
        """
        Needed for gov_pmt.
        Get premium_to county from the budget crop Farm yield and county yield
        """
        # TODO implement this for the farm crop, then compute a weighted average?

    def gov_payment(self, pf=1, yf=1):
        rp = ReferencePrices.objects.get(
            fsa_crop_type_id=self.fsa_crop_type_id,
            crop_year=self.farm_year.crop_year)
        gp = GovPmt(
            self.fsa_crop_type_id, self.plc_base_acres, self.arcco_base_acres,
            self.plc_yield, self.estimated_county_yield(), rp.effective_ref_price,
            rp.natl_loan_rate, self.harvest_futures_price(),
            self.get_projected_mya_price())
        return gp.compute_gov_pmt(pf, yf)

    def harvest_futures_price(self):
        """
        Since a farmer could have both winter and spring wheat, with different
        prices, we need a weighted average of market prices here.
        """
        # TODO: implement something

    def __str__(self):
        return f'{self.fsa_crop_type} for {self.farm_year}'


# --------------
# MarketCropType
# --------------
class MarketCropType(models.Model):
    """
    A type of crop that can be marketed, i.e. has a price.
    'Corn', 'Beans', 'Spring Wheat', 'Winter Wheat'
    """
    name = models.CharField(max_length=20)
    fsa_crop_type = models.ForeignKey('FsaCropType', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class FuturesPrice(models.Model):
    """
    Futures prices for marketed crop types.  Used for computing MYA prices
    and for estimating insurance indemnity and FSA payments.
    Data: e.g. ('Wheat SRW', 'CBOT', 'Jul 23', 'ZWN23', 6.3325, '2023-03-15', 3)
    """
    croptype = models.CharField(max_length=10)
    exchange = models.CharField(max_length=6)
    futures_month = models.CharField(max_length=8)
    ticker = models.CharField(max_length=8)
    price = models.FloatField()
    priced_on = models.DateField()
    market_crop_type = models.ForeignKey(MarketCropType, on_delete=models.CASCADE)

    def __str__(self):
        return (f'{self.croptype} {self.exchange} {self.futures_month} ' +
                f'{self.priced_on} {self.price}')

    class Meta:
        indexes = [models.Index('croptype', 'futures_month', 'priced_on',
                                name='fut_price_croptype_mth_pron'),
                   models.Index('market_crop_type', 'futures_month', 'priced_on',
                                name='fut_price_mktcroptype_mth_pron')]


class MarketCrop(models.Model):
    """
    """
    contracted_bu = models.FloatField(
        default=0, verbose_name="contracted bushels",
        help_text="Current contracted bushels on futures.")
    avg_contract_price = models.FloatField(
        default=0, verbose_name="avg. contract price",
        help_text="Average price for futures contracts.")
    new_target_frac = models.FloatField(
        default=0, verbose_name="new target as % of production",
        help_text="New target contracted bushels as a percent of total production.")
    basis_bu_locked = models.FloatField(
        default=0, verbose_name="bushels with basis locked",
        help_text="Number of bushels with contracted basis set.")
    avg_locked_basis = models.FloatField(
        default=0, verbose_name="avg. locked basis",
        help_text="Average basis on basis contracts in place.")
    assumed_basis_for_new = models.FloatField(default=0)
    farm_year = models.ForeignKey(FarmYear, on_delete=models.CASCADE)
    market_crop_type = models.ForeignKey(MarketCropType, on_delete=models.CASCADE)
    fsa_crop = models.ForeignKey(FsaCrop, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.market_crop_type} for {self.farm_year}'


# ------------
# FarmCropType
# ------------
class FarmCropType(models.Model):
    """
    Only farm crop types supported by crop insurance are made available to the user.
    Can get ins_crop through fsa_crop_type reference.  Data:
    ('Corn', False, 1, 41, 16), ('FS Beans', False, 2, 81, 997),
    ('Winter Wheat', False, 3, 11, 11), ('Spring Wheat', False, 3, 11, 12),
    ('DC Beans', True, 2, 81, 997)
    """
    name = models.CharField(max_length=20)
    is_fac = models.BooleanField(default=False)
    market_crop_type = models.ForeignKey('MarketCropType', on_delete=models.CASCADE)
    ins_crop = models.ForeignKey(InsCrop, on_delete=models.CASCADE)
    ins_crop_type = models.ForeignKey(InsCropType, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


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
    planted_acres = models.FloatField(default=0)
    nonrotating_acres = models.FloatField(
        default=0, help_text="The number of non-rotating acres, e.g. corn on corn.")
    frac_yield_dep_nonland_cost = models.FloatField(
        null=True, blank=True,
        verbose_name="est. % yield-dependent cost",
        help_text="Estimated % of non-land costs that vary with yield.")
    ta_aph_yield = models.FloatField(
        default=0, verbose_name="TA APH yield",
        help_text="Trend-adjusted average prodution history yield provided by insurer.")
    adj_yield = models.FloatField(
        default=0, verbose_name="Adjusted yield",
        help_text="Adjusted yield provided by insurer.")
    rate_yield = models.FloatField(
        default=0, help_text="Rate yield provided by insurer.")
    ye_use = models.BooleanField(
        default=False, verbose_name='use YE?',
        help_text="Use yield exclusion option? (e.g. exclude 2012 yields)")
    ta_use = models.BooleanField(
        default=False, verbose_name='use TA?',
        help_text="Use trend adjustment option? (apply a trend adjustment to yields).")
    subcounty = models.ForeignKey(
        Subcounty, on_delete=models.CASCADE, null=True, blank=True,
        verbose_name="risk class",
        help_text="Primary risk class (subcounty ID) provided by crop insurer")
    # TODO: we should give the user sensible defaults for these during the period
    # when they are required (prior year value for price volatility and board price
    # for projected price) and hide the form fields once they are known.
    price_vol_factor = models.DecimalField(
        max_digits=2, decimal_places=2, null=True, blank=True,
        verbose_name="price volatility factor",
        help_text="Estimated price volatility factor")
    proj_harv_price = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True,
        verbose_name="projected harvest price",
        help_text="Estimate for projected harvest price")
    cty_expected_yield = models.FloatField(
        null=True, blank=True, verbose_name="county expected yield",
        help_text="The RMA expected yield for the county if available")
    coverage_type = models.SmallIntegerField(
        choices=COVERAGE_TYPES, null=True, blank=True,
        help_text="Crop insurance coverage type.")
    product_type = models.SmallIntegerField(
        choices=PRODUCT_TYPES, null=True, blank=True,
        help_text="Crop insurance product type.")
    # TODO: use Javascript/AJAX to set choices based on coverage type
    base_coverage_level = models.DecimalField(
        max_digits=2, decimal_places=2, null=True, blank=True,
        choices=COVERAGE_LEVELS_F,
        help_text="Coverage level for selected crop insurance product.")
    sco_use = models.BooleanField(
        default=False, verbose_name="add SCO option?",
        help_text="Add Supplemental coverage option to bring coverage level to 86%?")
    eco_level = models.DecimalField(
        max_digits=2, decimal_places=2, null=True, blank=True,
        choices=COVERAGE_LEVELS_ECO,
        verbose_name="ECO level", help_text="Enhanced coverage level")
    prot_factor = models.FloatField(
        default=1, verbose_name="selected payment factor",
        help_text="Selected payment factor for county premiums/indemnities.")
    farm_crop_type = models.ForeignKey(FarmCropType, on_delete=models.CASCADE)
    market_crop = models.ForeignKey(MarketCrop, on_delete=models.CASCADE)
    farm_year = models.ForeignKey(FarmYear, on_delete=models.CASCADE)
    crop_ins_prems = models.JSONField(null=True, blank=True)
    # holds all allowed practices for this FarmCrop
    # these will be added to a drop-down with text 'irrigated', 'nonirrigated'
    # This indirectly specifies whether the farm crop is irrigated or not.
    ins_practices = ArrayField(models.SmallIntegerField(), size=2)
    # holds currently selected practice
    ins_practice = models.SmallIntegerField()
    new_crop_ticker = models.CharField(max_length=8, null=True)
    new_crop_fut_harv_price = models.FloatField(
        default=0, verbose_name="new crop futures price",
        help_text="Current new crop futures harvest price.")

    def __str__(self):
        return f'{self.farm_crop_type} for {self.farm_year}'

    def farm_expected_yield(self):
        """
        Computed from budget crops and rotating acres
        """

    def farm_yield_premium_to_cty(self):
        """
        Computed from budget crops county yield and rotating acres
        """

    def save(self, *args, **kwargs):
        # TODO: only set prems if really necessary (i.e. if an input field changed)
        # TODO: if the model_run_date is before the end of discovery, need to set
        # price_volatility and projected price also.
        if (self.planted_acres > 0 and self.rate_yield > 0 and self.adj_yield > 0
                and self.ta_aph_yield > 0):
            self.set_prems()
        super().save(*args, **kwargs)

    def set_prems(self):
        p = Premium()
        prems = p.compute_prems(
            state=self.farm_year.state_id,
            county=self.farm_year.county_code,
            crop=self.farm_crop_type.ins_crop_id,
            croptype=self.farm_crop_type.ins_crop_type_id,
            practice=self.ins_practice,
            rateyield=self.rate_yield,
            adjyield=self.adj_yield,
            tayield=self.ta_aph_yield,
            acres=self.planted_acres,
            tause=self.ta_use,
            yieldexcl=self.ye_use,
            prot_factor=self.prot_factor,
            price_volatility_factor=self.price_vol_factor,
            projected_price=self.proj_harv_price,
            subcounty=self.subcounty_id)
        if prems is not None:
            names = 'Farm County SCO ECO'.split()
            self.crop_ins_prems = {key: ar.tolist()
                                   for key, ar in zip(names, prems[:4])}
            self.proj_harv_price = prems[4]
            self.cty_expected_yield = prems[5]

    def get_indemnities(self, pf, yf):
        indem = Indemnity(
            self.ta_aph_yield, self.proj_harv_price, self.cur_futures_harv_price.price,
            self.cty_expected_yield, self.farm_expected_yield(), self.prot_factor,
            self.farm_yield_premium_to_cty())
        return indem.compute_indems(pf, yf)

    def allowed_subcounties(self):
        # TODO: may need to double up subcounty id in values_list and/or add None
        return SubcountyAvail.objects.filter(
            state_id=self.farm_year.state_id, county_code=self.farm_year.county_code,
            crop_id=self.farm_crop_type.ins_crop,
            croptype_id=self.farm_crop_type_ins_crop_type,
            practice=self.ins_practice).values_list('subcounty_id')

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(prot_factor__gte=0) & Q(prot_factor__lte=1),
                name="prot_factor_in_range")
        ]


# --------------
# BudgetCropType
# --------------
class BudgetCropType(models.Model):
    """
    Can get is_fac through farm_crop_type reference.
    There are 14 Budget crop types
    """
    name = models.CharField(max_length=20)
    farm_crop_type = models.ForeignKey(FarmCropType, on_delete=models.CASCADE)
    is_rotated = models.BooleanField(null=True)
    is_irr = models.BooleanField(null=True)

    def __str__(self):
        return self.name


class BudgetCrop(models.Model):
    """
    A column in a budget named by its budget_crop_type name.
    Cost items are in dollars per acre.  One or two budget crops are assigned
    To each farm crop based on matching the farm_crop_type and irrigated status
    of the farm crop to the buddget crop type.
    """
    farm_yield = models.FloatField(default=0)
    # the farm yield value is copied to county yield during import.
    county_yield = models.FloatField(default=0)
    assumed_basis = models.FloatField(default=0)
    other_gov_pmts = models.FloatField(default=0)
    other_revenue = models.FloatField(default=0)
    fertilizers = models.FloatField(default=0)
    pesticides = models.FloatField(default=0)
    seed = models.FloatField(default=0)
    drying = models.FloatField(default=0)
    storage = models.FloatField(default=0)
    other_direct_costs = models.FloatField(
        default=0, help_text="Other (hauling, custom operations)")
    machine_hire_lease = models.FloatField(
        default=0, verbose_name="machine hire or lease")
    utilities = models.FloatField(default=0)
    machine_repair = models.FloatField(default=0)
    fuel_and_oil = models.FloatField(default=0)
    light_vehicle = models.FloatField(default=0)
    machine_depr = models.FloatField(default=0, verbose_name="machine depreciation")
    labor_and_mgmt = models.FloatField(default=0, verbose_name="labor and management")
    building_repair_and_rent = models.FloatField(default=0)
    building_depr = models.FloatField(default=0, verbose_name="building depreciation")
    insurance = models.FloatField(default=0)
    misc_overhead_costs = models.FloatField(default=0)
    interest_nonland = models.FloatField(
        default=0, verbose_name="non-land interest cost")
    other_overhead_costs = models.FloatField(default=0)
    rented_land_costs = models.FloatField(default=0)
    budget_crop_type = models.ForeignKey(BudgetCropType, on_delete=models.CASCADE)
    # This is set null after copying and assigning to a farm crop
    budget = models.ForeignKey('Budget', on_delete=models.CASCADE,
                               null=True, blank=True)
    orig_budget = models.ForeignKey('Budget', on_delete=models.CASCADE,
                                    related_name="orig_budget")
    farm_crop = models.ForeignKey(FarmCrop, on_delete=models.CASCADE,
                                  null=True, blank=True)

    def farm_yield_premium_to_cty(self):
        return ((self.farm_yield - self.county_yield) / self.county_yield
                if self.county_yield > 0 else 0)

    def __str__(self):
        return f'{self.budget_crop_type} in {self.budget}'


class Budget(models.Model):
    """
    A built-in budget. It has many BudgetCrops.
    Once farm crops have been added to a farm year and their irrigated status set,
    we use some algorithm to do the selection of budget crops based on the
    user's state/county and insurable crops irr/nonirr. One or two budget crops
    will be copied and associated with each farm crop.  If the user changes the
    irr/non-irr status for a farm crop later, we ask them if they want to
    replace the corresponding budget column or keep the one they have.
    Copies of budget crops assigned to farm crops will have their budget id set to
    NULL, but keep their orig_budget_id for reference.
    """
    name = models.CharField(max_length=60)
    crop_year = models.SmallIntegerField()
    state = models.CharField(max_length=2)
    authors = models.CharField(max_length=150, null=True)
    institution = models.CharField(max_length=150, null=True)
    source_url = models.URLField(null=True)
    created_on = models.DateField()

    @property
    def fullname(self):
        datestr = self.created_on.strftime('%b %d %Y').replace(' 0', ' ')
        return (f"{self.name} - {datestr}")

    def __str__(self):
        return self.fullname

    class Meta:
        constraints = [
            models.UniqueConstraint('name', 'crop_year', 'created_on',
                                    name='name_unique_for_crop_year_created'),
        ]
