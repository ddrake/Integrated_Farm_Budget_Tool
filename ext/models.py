from django.contrib.postgres.fields import ArrayField
from django.db import models

from core.models.util import call_postgres_func


class SmallFloatField(models.FloatField):
    def db_type(self, connection):
        return 'real'


class State(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    name = models.CharField(max_length=20)
    abbr = models.CharField(max_length=2)

    def __str__(self):
        return self.name

    class Meta:
        managed = False


class County(models.Model):
    id = models.IntegerField(primary_key=True)
    code = models.SmallIntegerField()
    name = models.CharField(max_length=40)
    state = models.ForeignKey('State', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.name}, {self.state.abbr}'

    class Meta:
        managed = False
        verbose_name_plural = 'counties'

    @classmethod
    def code_and_name_for_state_id(cls, state_id):
        return list(cls.objects.filter(state_id=state_id)
                    .order_by('name').values_list('code', 'name'))


class InsCrop(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'ext_commodity'
        managed = False


class InsCropType(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    name = models.CharField(max_length=20)
    abbr = models.CharField(max_length=10)
    crop = models.ForeignKey('InsCrop', on_delete=models.CASCADE,
                             db_column='commodity_id')

    def __str__(self):
        return f'{self.crop}, {self.name}'

    class Meta:
        db_table = 'ext_commoditytype'
        managed = False


class InsPractice(models.Model):
    id = models.IntegerField(primary_key=True)
    code = models.SmallIntegerField()
    name = models.CharField(max_length=40)
    crop = models.ForeignKey('InsCrop', on_delete=models.CASCADE,
                             db_column='commodity_id')

    def __str__(self):
        return f'{self.crop}, {self.name}'

    class Meta:
        db_table = 'ext_practice'
        managed = False


class Subcounty(models.Model):
    id = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=20, null=True)

    def __str__(self):
        return self.id

    class Meta:
        db_table = 'ext_subcounty'
        managed = False
        verbose_name_plural = 'subcounties'


class PracticeAvail(models.Model):
    """
    Materialized view for looking up available farm practices
    (not necessarily the farm practice).
    """
    id = models.IntegerField(primary_key=True)
    state = models.ForeignKey('State', on_delete=models.CASCADE)
    county_code = models.SmallIntegerField()
    crop = models.ForeignKey('InsCrop', on_delete=models.CASCADE,
                             db_column='commodity_id')
    croptype = models.ForeignKey('InsCropType', on_delete=models.CASCADE,
                                 db_column='commodity_type_id')
    practice = models.SmallIntegerField()

    class Meta:
        managed = False
        db_table = 'ext_practiceavail'


class SubcountyAvail(models.Model):
    """
    Materialized view for looking up available subcounty_ids
    """
    id = models.IntegerField(primary_key=True)
    state = models.ForeignKey('State', on_delete=models.CASCADE)
    county_code = models.SmallIntegerField()
    crop = models.ForeignKey('InsCrop', on_delete=models.CASCADE,
                             db_column='commodity_id')
    croptype = models.ForeignKey('InsCropType', on_delete=models.CASCADE,
                                 db_column='commodity_type_id')
    practice = models.SmallIntegerField()
    subcounty = models.ForeignKey('Subcounty', on_delete=models.CASCADE, null=True)

    class Meta:
        managed = False
        db_table = 'ext_subcountyavail'


class InsurableCropsForCty(models.Model):
    """
    Materialized view for looking up available crops/types/practices for a
    state_id and county_code
    """
    id = models.IntegerField(primary_key=True)
    state_id = models.SmallIntegerField()
    county_code = models.SmallIntegerField()
    crop_id = models.SmallIntegerField(db_column='commodity_id')
    crop_type_id = models.SmallIntegerField(db_column='commodity_type_id')
    is_fac = models.BooleanField()
    practices = ArrayField(models.SmallIntegerField(), size=2)

    class Meta:
        managed = False
        db_table = 'ext_insurable_crops_for_cty'


class FsaCropType(models.Model):
    """
    Aggregates for government payment, marketing assumptions, basis
    'Corn', 'Beans', 'Wheat'
    """
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name

    class Meta:
        managed = False


class ReferencePrices(models.Model):
    """
    Reference prices needed to compute government payments
    """
    crop_year = models.SmallIntegerField()
    fsa_crop_type = models.ForeignKey(FsaCropType, on_delete=models.CASCADE,
                                      related_name='reference_prices')
    natl_loan_rate = models.FloatField()
    effective_ref_price = models.FloatField()

    class Meta:
        managed = False
        indexes = [models.Index('crop_year', name='ref_prices_crop_year'), ]


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

    @classmethod
    def get_mya_pre_estimates(cls, crop_year, for_date, pf=None):
        """
        Get the sensitized MYA prices for each FSA crop type for the crop year
        and the given date.
        """
        if pf is None:
            pf = [1, 1, 1]
        names = ('''corn_mya_price beans_mya_price wheat_mya_price''').split()
        cmd = 'SELECT ' + ', '.join(names) + """
                  FROM
                  public.ext_mya_pre_estimate(%s, %s)
                  AS (corn_mya_price double precision, beans_mya_price double precision,
                      wheat_mya_price double precision);
              """
        record = call_postgres_func(cmd, crop_year, for_date)
        return tuple(None if it is None else float(it) * ppf
                     for ppf, it in zip(pf, record))

    @classmethod
    def get_mya_pre_estimate(cls, crop_year, for_date, fsa_crop_type_id, pf=1):
        """
        Get the sensitized MYA price for the specified FSA crop type for the crop year
        and the given date.
        """
        names = ('''corn_mya_price beans_mya_price wheat_mya_price''').split()
        name = names[fsa_crop_type_id-1]
        cmd = f'SELECT {name}' + """
                  FROM
                  public.ext_mya_pre_estimate(%s, %s)
                  AS (corn_mya_price double precision, beans_mya_price double precision,
                      wheat_mya_price double precision);
              """
        record = call_postgres_func(cmd, crop_year, for_date)
        return list(record)[0] * pf

    class Meta:
        managed = False
        indexes = [models.Index('crop_year', name='mya_pre_crop_year'), ]


class MyaPost(models.Model):
    """
    View to get sensitized MYA prices when the model_run_date is after the
    May WASDE report
    """
    id = models.IntegerField(primary_key=True)
    crop_year = models.SmallIntegerField()
    forecast_month = models.CharField(max_length=8)
    wasde_release_date = models.DateField(verbose_name='WASDE release date')
    corn_price = models.FloatField(null=True)
    beans_price = models.FloatField(null=True)
    wheat_price = models.FloatField(null=True)
    corn_pct_locked = models.FloatField(null=True)
    beans_pct_locked = models.FloatField(null=True)
    wheat_pct_locked = models.FloatField(null=True)

    @classmethod
    def get_mya_post_estimates(cls, crop_year, for_date, pf=None):
        """
        Get the sensitized MYA prices for each FSA crop type for the crop year
        and the given date.
        """
        if pf is None:
            pf = [1, 1, 1]
        row = (MyaPost.objects
               .filter(wasde_release_date__lte=for_date, crop_year=crop_year)
               .order_by("-wasde_release_date")[0])
        prices = [row.corn_price, row.beans_price, row.wheat_price]
        pct_locked = [row.corn_pct_locked, row.beans_pct_locked, row.wheat_pct_locked]
        mya_prices = [pr * (plk + pff * (1 - plk))
                      for pff, pr, plk in zip(pf, prices, pct_locked)]
        return mya_prices

    @classmethod
    def get_mya_post_estimate(cls, crop_year, for_date, fsa_crop_type_id, pf=1):
        """
        Get the sensitized MYA prices for each FSA crop type for the crop year
        and the given date.
        """
        row = (MyaPost.objects
               .filter(wasde_release_date__lte=for_date, crop_year=crop_year)
               .order_by("-wasde_release_date")[0])
        price = (row.corn_price if fsa_crop_type_id == 1 else
                 row.beans_price if fsa_crop_type_id == 2 else
                 row.wheat_price)
        pct_locked = (row.corn_pct_locked if fsa_crop_type_id == 1 else
                      row.beans_pct_locked if fsa_crop_type_id == 2 else
                      row.wheat_pct_locked)
        return price * (pct_locked + pf * (1 - pct_locked))

    class Meta:
        managed = False


class MarketCropType(models.Model):
    """
    A type of crop that can be marketed, i.e. has a price.
    'Corn', 'Beans', 'Spring Wheat', 'Winter Wheat'
    """
    name = models.CharField(max_length=20)
    fsa_crop_type = models.ForeignKey('FsaCropType', on_delete=models.CASCADE,
                                      related_name='market_crop_types')

    def __str__(self):
        return self.name

    class Meta:
        managed = False


class FuturesContract(models.Model):
    id = models.IntegerField(primary_key=True)
    ticker = models.CharField(max_length=8)
    croptype = models.CharField(max_length=10)
    exchange = models.CharField(max_length=6)
    futures_month = models.CharField(max_length=8)
    contract_end_date = models.DateField()
    market_crop_type_id = models.IntegerField()

    class Meta:
        managed = False


class FuturesPrice(models.Model):
    """
    Futures prices for marketed crop types.  Used for computing MYA prices
    and for estimating insurance indemnity and FSA payments.
    Data: e.g. ('Wheat SRW', 'CBOT', 'Jul 23', 'ZWN23', 6.3325, '2023-03-15', 3)
    """
    id = models.IntegerField(primary_key=True)
    croptype = models.CharField(max_length=10)
    exchange = models.CharField(max_length=6)
    futures_month = models.CharField(max_length=8)
    ticker = models.CharField(max_length=8)
    price = models.FloatField()
    priced_on = models.DateField()
    market_crop_type_id = models.IntegerField()

    def __str__(self):
        return (f'{self.croptype} {self.exchange} {self.futures_month} ' +
                f'{self.priced_on} {self.price}')

    class Meta:
        managed = False


class InsuranceDates(models.Model):
    """
    Information from RMA aquired via the following urls:
    https://prodwebnlb.rma.usda.gov/apps/PriceDiscovery/GetPrices/YourPrice
    https://www.rma.usda.gov/Policy-and-Procedure/Insurance-Plans/
       Commodity-Exchange-Price-Provisions-CEPP
    """
    crop_year = models.SmallIntegerField()
    proj_price_disc_start = models.DateField()
    proj_price_disc_end = models.DateField()
    harv_price_disc_mth_start = models.DateField()
    harv_price_disc_mth_end = models.DateField()
    exchange = models.CharField(max_length=6)
    futures_month = models.CharField(max_length=8)
    ticker = models.CharField(max_length=8)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    county_code = models.SmallIntegerField()
    market_crop_type = models.ForeignKey('MarketCropType', on_delete=models.CASCADE)
    post_futures_month = models.CharField(max_length=8)
    post_ticker = models.CharField(max_length=8)

    class Meta:
        managed = False
        indexes = [models.Index('crop_year', name='insurance_dates_crop_year'),
                   models.Index('ticker', name='insurance_dates_ticker'),
                   models.Index('county_code', name='insurance_dates_county'), ]


class FarmCropType(models.Model):
    """
    Only farm crop types supported by crop insurance are made available to the user.
    Can get ins_crop through fsa_crop_type reference.  Data:
    ('Corn', False, 1, 41, False), ('FS Beans', False, 2, 81, False),
    ('Winter Wheat', False, 3, 11, True), ('Spring Wheat', False, 3, 11, False),
    ('DC Beans', True, 2, 81, False)
    """
    name = models.CharField(max_length=20)
    is_fac = models.BooleanField(default=False)
    market_crop_type = models.ForeignKey('MarketCropType', on_delete=models.CASCADE,
                                         related_name='farm_crop_types')
    ins_crop = models.ForeignKey(InsCrop, on_delete=models.CASCADE,
                                 related_name='farm_crop_types')
    is_winter = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        managed = False


class BudgetCrop(models.Model):
    """
    A column in a budget named by its budget_crop_type name.
    Cost items are in dollars per acre.  One or two budget crops are assigned
    To each farm crop based on matching the farm_crop_type and irrigated status
    of the farm crop to the buddget crop type.
    """
    farm_yield = models.FloatField(default=0)
    description = models.CharField(max_length=50)
    yield_variability = models.FloatField(default=0)
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
    farm_crop_type = models.ForeignKey(FarmCropType, on_delete=models.CASCADE,
                                       null=True)
    budget = models.ForeignKey('Budget', on_delete=models.CASCADE,
                               null=True, blank=True, related_name='budget_crops')
    state = models.ForeignKey(State, on_delete=models.CASCADE, null=True)
    is_rot = models.BooleanField(null=True)
    is_irr = models.BooleanField(default=False)

    def __str__(self):
        rotstr = (' Rot,' if self.is_rot
                  else '' if self.is_rot is None else ' Cont,')
        descr = '' if self.description == '' else f' {self.description},'
        yldstr = f' {int(self.farm_yield)} bpa,'
        rentstr = f' Rent: ${int(self.rented_land_costs)}/ac'
        return (f'{self.state.abbr},{descr}{rotstr}{yldstr}{rentstr}')

    class Meta:
        managed = False
        ordering = ['state__abbr', 'description', 'is_rot',
                    'farm_yield', 'rented_land_costs']


class Budget(models.Model):
    """
    A built-in budget. It has many BudgetCrops.  It's essentially a bucket with
    some source information for reference only.
    """
    crop_year = models.SmallIntegerField()
    authors = models.CharField(max_length=150, null=True)
    institution = models.CharField(max_length=150, null=True)
    source_url = models.URLField(null=True)
    created_on = models.DateField()

    @property
    def fullname(self):
        return (f"{self.institution} - {self.created_on}")

    def __str__(self):
        return self.fullname

    class Meta:
        managed = False
        ordering = ['institution']


class Price(models.Model):
    id = models.IntegerField(primary_key=True)
    county_code = models.SmallIntegerField()
    crop_id = models.SmallIntegerField(db_column='commodity_id')
    crop_type_id = models.SmallIntegerField(db_column='commodity_type_id')
    state_id = models.SmallIntegerField()
    practice = models.SmallIntegerField()
    projected_price = SmallFloatField()
    price_volatility_factor = SmallFloatField()
    expected_yield = SmallFloatField()
    final_yield = SmallFloatField()
    harvest_price = SmallFloatField()
    crop_year = models.SmallIntegerField()

    class Meta:
        db_table = 'ext_price'
        managed = False


class PriceYield(models.Model):
    id = models.IntegerField(primary_key=True)
    state_id = models.SmallIntegerField()
    county_code = models.SmallIntegerField()
    crop_id = models.SmallIntegerField(db_column='commodity_id')
    crop_type_id = models.SmallIntegerField(db_column='commodity_type_id')
    practice = models.SmallIntegerField()
    expected_yield = SmallFloatField()
    projected_price = SmallFloatField()
    price_volatility_factor = models.SmallIntegerField()
    final_yield = SmallFloatField()
    harvest_price = SmallFloatField()
    crop_year = models.SmallIntegerField()
    price_volatility_factor_prevyr = SmallFloatField()

    class Meta:
        db_table = 'ext_priceyield'
        managed = False


class AreaRate(models.Model):
    id = models.IntegerField(primary_key=True)
    state_id = models.SmallIntegerField()
    county_code = models.SmallIntegerField()
    crop_id = models.SmallIntegerField(db_column='commodity_id')
    crop_type_id = models.SmallIntegerField(db_column='commodity_type_id')
    practice = models.SmallIntegerField()
    insurance_plan_id = models.SmallIntegerField()

    class Meta:
        db_table = 'ext_arearate'
        managed = False


class BenchmarkRevenue(models.Model):
    id = models.IntegerField(primary_key=True)
    state_id = models.SmallIntegerField()
    county_code = models.SmallIntegerField()
    crop = models.SmallIntegerField()
    practice = models.SmallIntegerField()
    crop_year = models.SmallIntegerField()
    benchmark_revenue = SmallFloatField()
    benchmark_yield = SmallFloatField()
    benchmark_price = SmallFloatField()

    class Meta:
        db_table = 'ext_govpmt_benchmark_revenue'
        managed = False
