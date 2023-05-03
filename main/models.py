from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q
from django.utils import timezone
from ext.models import (State, Subcounty, Crop, CropType,
                        InsurableCropsForCty, SubcountyAvail)
from core.models.premium import Premium


def get_current_year():
    return timezone.now().year


class Budget(models.Model):
    """
    A built-in (imported) or user-customized budget. It has many BudgetCrops.
    A user budget is created with columns from one or more built-in budgets
    once the farm crops have been added and their irrigated status set.
    We use some algorithm to do the selection of budget columns based on the
    user's state/county and insurable crops irr/nonirr.  If they change the
    irr/non-irr status for a farm crop later, we ask them if they want to
    replace the corresponding budget column or keep the one they have.
    """
    name = models.CharField(max_length=60)
    crop_year = models.SmallIntegerField()
    state = models.CharField(max_length=2)
    authors = models.CharField(max_length=150, null=True)
    institution = models.CharField(max_length=150, null=True)
    source_url = models.URLField(null=True)
    created_on = models.DateField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

    @property
    def fullname(self):
        datestr = self.created_on.strftime('%b %d %Y').replace(' 0', ' ')
        return (f"{self.name} - {datestr}")

    def __str__(self):
        return self.fullname

    class Meta:
        constraints = [
            models.UniqueConstraint('name', 'user', 'crop_year', 'created_on',
                                    name='name_unique_for_user_crop_year_created'),
        ]


class FarmYear(models.Model):
    """
    Holds non-crop-specific values for a crop year for a farm
    A user can have multiple FarmYears, including multiple farms for the
    same crop year, but we don't currently try to do any aggregation over
    a user's farms for a given crop year.
    A FarmYear has many FarmCrops and many PricedCrops so we should be able
    to add any needed totalizer methods.
    I think the farm year should include FarmCrops and PricedCrops if and
    only if they can be insured.  E.g. a Champaign County user would not
    see FAC beans.  A Madison County user would see that crop but could
    set the acres to zero if so desired.
    We may want to break out a form that lets the user first input a minimal
    set of data (farm_name, crop_year, state and county) sufficient for
    determining the set of insurable crops.
    We probably need a method that creates those insurable farm_crops
    with default values and associates them with the current instance.
    """
    PRETAX_INCOME = 0
    PRETAX_CASH_FLOW = 1
    REPORT_TYPES = [(PRETAX_INCOME, 'Pre-tax income'),
                    (PRETAX_CASH_FLOW, 'Pre-tax cash flow')]
    farm_name = models.CharField(max_length=60)
    # TODO: We'll want to populate a counties drop-down via AJAX when the
    # user selects or changes the state.
    county_code = models.SmallIntegerField(verbose_name="county")
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
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, null=True, blank=True)
    # When a user sets the baseline for a crop year, copies are made of the farmyear and
    # all related model records and is_baseline is set True.  These records are never
    # updated, but remain a static snapshot.  If the user later chooses to set a new
    # baseline for the year, these records are deleted and replaced by the new baseline
    # records.  At any time, the user can view a report on variance with respect to
    # the baseline for the crop year.  Once a baseline has been set, some fields
    # e.g. planted acres, is_irr, should no longer be allowed to change.  I guess we
    # could say, if you change that value, your baseline budget will be deleted.
    # TODO: Add method create_baseline()
    is_baseline = models.BooleanField(default=False)

    @property
    def full_name(self):
        return f'{self.farm_name} ({self.crop_year} Crop Year)'

    def __str__(self):
        return self.full_name

    def add_insured_farm_crops(self):
        for row in (InsurableCropsForCty.objects
                    .filter(state_id=self.state_id, county_code=self.county_code)
                    .order_by('id')):
            fct = FarmCropType.objects.get(
                ins_crop_id=row.crop_id, ins_crop_type_id=row.crop_type_id,
                is_fac=row.is_fac)
            pct = PricedCropType.objects.get(pk=fct.priced_crop_type_id)
            pc = PricedCrop.objects.create(farm_year=self, priced_crop_type=pct)
            FarmCrop.objects.create(
                farm_year=self, farm_crop_type=fct, priced_crop=pc,
                ins_practices=row.practices, ins_practice=row.practices[0])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.farmcrop_set.count() == 0:
            self.add_insured_farm_crops()
            self.save()

    class Meta:
        constraints = [
            models.UniqueConstraint('farm_name', 'user', 'crop_year',
                                    name='farm_name_unique_for_user_crop_year'),
        ]


class PricedCropType(models.Model):
    """
    Aggregates for government payment, marketing assumptions, basis
    'Corn', 'Beans', 'Wheat'
    """
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class FarmCropType(models.Model):
    """
    Only farm crop types supported by crop insurance are made available to the user.
    Can get ins_crop through priced_crop_type reference.  Data:
    ('Corn', False, 1, 41, 16), ('FS Beans', False, 2, 81, 997),
    ('Winter Wheat', False, 3, 11, 11), ('Spring Wheat', False, 3, 11, 12),
    ('DC Beans', True, 2, 81, 997)
    """
    name = models.CharField(max_length=20)
    is_fac = models.BooleanField(default=False)
    priced_crop_type = models.ForeignKey(PricedCropType, on_delete=models.CASCADE)
    ins_crop = models.ForeignKey(Crop, on_delete=models.CASCADE)
    ins_crop_type = models.ForeignKey(CropType, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class BudgetCropType(models.Model):
    """
    Can get is_fac through farm_crop_type reference.  Data:
    ('Corn on Beans', 1, True), ('Corn on Corn', 1, False),
    ('Beans on Corn' 2, True), ('Beans on Beans', 2, False),
    ('Winter Wheat', 3, Null), ('Spring Wheat', 4, Null),
    ('DC Beans', 5, Null)
    """
    name = models.CharField(max_length=20)
    farm_crop_type = models.ForeignKey(FarmCropType, on_delete=models.CASCADE)
    is_rotated = models.BooleanField(null=True)

    def __str__(self):
        return self.name


class HarvestFuturesPrice(models.Model):
    """
    Harvest futures prices, inserted daily until they go off the board.
    I think we store prices going back to the beginning of the crop year, but
    prompt the user that they may wish to update the prices if more recent
    prices are available for the crop year.  Maybe they could click
    a button 'set current prices'?  Sample data:
    ('C', 'CHI', 'Dec 23', 5.20, 16, 2023-04-01),
    ('S', 'CHI', 'Nov 23', 9.40, 997, 2023-04-01),
    ('SRW', 'CHI', 'Jul 23', 6.10, 11, 2023-04-01),
    ('HRW', 'KC', 'Jul 23', 6.10, 11, 2023-04-01),
    ('HRS', 'MPLS', 'Jul 23', 6.10, 12, 2023-04-01),
    """
    CORN = 'C'
    SOY = 'S'
    SRW = 'SRW'
    HRW = 'HRW'
    HRS = 'HRS'
    CROPTYPES = [(CORN, 'CORN'), (SOY, 'SOY'), (SRW, 'SRW'), (HRW, 'HRW'), (HRS, 'HRS')]
    CHI = 'CHI'
    KC = 'KC'
    MPLS = 'MPLS'
    EXCHANGES = [(CHI, CHI), (KC, KC), (MPLS, MPLS)]

    croptype = models.CharField(max_length=6, choices=CROPTYPES)
    exchange = models.CharField(max_length=6, choices=EXCHANGES)
    futures_month = models.CharField(max_length=8)
    price = models.FloatField(default=0)
    priced_on = models.DateField(default=timezone.now)
    ins_crop_type = models.ForeignKey(CropType, on_delete=models.CASCADE)

    def __str__(self):
        return (f'{self.croptype} {self.exchange} {self.futures_month} ' +
                f'{self.priced_on} {self.price}')


class PricedCrop(models.Model):
    """
    Priced crop-specific operator input data.  A PricedCrop has many FarmCrops so we
    should be able to get totals pretty easily.
    """
    plc_base_acres = models.FloatField(default=0, verbose_name="Base acres in PLC")
    arcco_base_acres = models.FloatField(default=0, verbose_name="Base acres in ARC-CO")
    plc_yield = models.FloatField(
        default=0, verbose_name="farm avg. PLC yield",
        help_text="Weighted average PLC yield for farm in bushels per acre.")
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
    priced_crop_type = models.ForeignKey(PricedCropType, on_delete=models.CASCADE)
    new_crop_fut_harv_price = models.ForeignKey(
        HarvestFuturesPrice, on_delete=models.CASCADE, null=True, blank=True,
        verbose_name="new crop futures price",
        help_text="Current new crop futures harvest price.")

    def __str__(self):
        return str(self.priced_crop_type)


class FarmCrop(models.Model):
    """
    Farm crop-specific data.  A column in the operator input sheet.
    It holds references to the associated priced_crop and farm_year models
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
    is_irr = models.BooleanField(default=False, verbose_name='irrigated?')
    planted_acres = models.FloatField(default=0)
    rotating_acres = models.FloatField(
        null=True, help_text="The number of rotating acres, e.g. corn on beans.")
    frac_yield_dep_nonland_cost = models.FloatField(
        null=True, verbose_name="est. % yield-dependent cost",
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
    coverage_type = models.SmallIntegerField(
        choices=COVERAGE_TYPES, null=True, blank=True,
        help_text="Crop insurance coverage type.")
    product_type = models.SmallIntegerField(
        choices=PRODUCT_TYPES, null=True, blank=True,
        help_text="Crop insurance product type.")
    # TODO: use Javascript/AJAX to set choices based on coverage type or include from
    # 50% to 90% and filter?
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
    # since all priced_crop fields have default values, we don't need to allow
    # priced_crop to be NULL.
    priced_crop = models.ForeignKey(PricedCrop, on_delete=models.CASCADE)
    farm_year = models.ForeignKey(FarmYear, on_delete=models.CASCADE)
    crop_ins_prems = models.JSONField(null=True, blank=True)
    # holds all allowed practices for this FarmCrop
    ins_practices = ArrayField(models.SmallIntegerField(), size=2)
    # holds currently selected practice
    ins_practice = models.SmallIntegerField()

    def __str__(self):
        return str(self.farm_crop_type)

    def save(self, *args, **kwargs):
        # TODO: only set prems if really necessary (i.e. if an input field changed)
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
                                   for key, ar in zip(names, prems)}

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


class BudgetCrop(models.Model):
    """
    A column in a budget named by its budget_crop_type name.
    Cost items are in dollars per acre.
    I think budget crops should be included in the budget if and only if they can
    be insured, and a budget with no insurable crops should be removed from the
    select list.
    """
    farm_yield = models.FloatField(default=0)
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
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.budget_crop_type} in {self.budget}'
