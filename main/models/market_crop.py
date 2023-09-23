from datetime import datetime
from django.core.validators import (
    MinValueValidator as MinVal, MaxValueValidator as MaxVal)
from django.db import models
from ext.models import FuturesPrice, MarketCropType
from .farm_year import FarmYear
from .fsa_crop import FsaCrop


class MarketCrop(models.Model):
    """
    A crop which can be marketed and which has a unique set of futures prices
    for a given county.
    """
    assumed_basis_for_new = models.FloatField(
        default=0, validators=[MinVal(-2), MaxVal(2)],
        help_text="Assumed basis for non-contracted bushels.")
    farm_year = models.ForeignKey(FarmYear, on_delete=models.CASCADE,
                                  related_name='market_crops')
    market_crop_type = models.ForeignKey(MarketCropType, on_delete=models.CASCADE)
    fsa_crop = models.ForeignKey(FsaCrop, on_delete=models.CASCADE,
                                 related_name='market_crops')
    price_factor = models.FloatField(
        default=1, validators=[
            MinVal(0),
            MaxVal(10, message="Ensure this value is less than or equal to 1000")],
        verbose_name='price sensititivity factor',
        help_text=('Percent of current futures price, reflected in detailed budget'))

    def __str__(self):
        return f'{self.market_crop_type}'

    def contracted_bu(self):
        return sum(c.bushels for c in self.get_futures_contracts())

    def basis_bu_locked(self):
        return sum(c.bushels for c in self.get_basis_contracts())

    def avg_contract_price(self):
        pairs = [(c.price*c.bushels, c.bushels) for c in self.get_futures_contracts()]
        if len(pairs) == 0:
            return 0
        else:
            amounts, bushels = zip(*pairs)
            tot_bu = sum(bushels)
            return sum(amounts) / tot_bu if tot_bu > 0 else 0

    def avg_locked_basis(self):
        pairs = [(c.price*c.bushels, c.bushels) for c in self.get_basis_contracts()]
        if len(pairs) == 0:
            return 0
        else:
            amounts, bushels = zip(*pairs)
            tot_bu = sum(bushels)
            return sum(amounts) / tot_bu if tot_bu > 0 else 0

    def get_basis_contracts(self):
        model_run_date = self.farm_year.get_model_run_date()
        return self.contracts.filter(
            is_basis=True, contract_date__lte=model_run_date)

    def get_futures_contracts(self):
        model_run_date = self.farm_year.get_model_run_date()
        return self.contracts.filter(
            is_basis=False, contract_date__lte=model_run_date)

    def harvest_price(self):
        return self.harvest_futures_price_info(price_only=True)

    def sens_harvest_price(self, pf=None):
        if pf is None:
            pf = self.price_factor
        return self.harvest_futures_price_info(price_only=True) * pf

    def harvest_futures_price_info(self, priced_on=None, price_only=False):
        """
        Get the harvest price for the given date from the correct exchange for the
        crop type and county.  Note: insurancedates gives the exchange and ticker.
        """
        # TODO: consider returning a boolean "price locked" if the model run date
        # is after the expiration date of the post_ticker contract
        if priced_on is None:
            priced_on = self.farm_year.get_model_run_date()

        sql = """
            SELECT fp.id, fp.exchange, fp.futures_month, fp.ticker,
            fp.priced_on, fp.price
            FROM ext_futuresprice fp
            WHERE ticker=
                (select ticker from ext_tickers_for_crop_location
                 where crop_year=%s and state_id=%s and county_code=%s
                 and market_crop_type_id=%s
                 and (%s <= contract_end_date
                     or contract_end_date = last_contract_end_date)
                 order by contract_end_date limit 1)
            AND fp.priced_on <= %s
            ORDER BY priced_on desc limit 1
            """

        rec = FuturesPrice.objects.raw(
            sql, params=[self.farm_year.crop_year, self.farm_year.state_id,
                         self.farm_year.county_code, self.market_crop_type_id,
                         priced_on, priced_on])[0]
        return rec.price if price_only else rec

    def planted_acres(self):
        return sum((fc.planted_acres for fc in self.farm_crops.all()))

    def sens_farm_expected_yield(self):
        """ used in revenue buildup """
        return sum((fc.sens_farm_expected_yield() for fc in self.farm_crops.all()
                    if fc.has_budget()))

    def yield_factor(self):
        return sum((fc.yield_factor * fc.planted_acres
                    for fc in self.farm_crops.all())) / self.planted_acres()

    def county_bean_yield(self, yf=1):
        """ for indemnity calculations """
        ac = self.planted_acres()
        return (0 if self.market_crop_type_id != 2 or ac == 0 else
                sum((fc.sens_cty_expected_yield(yf) * fc.planted_acres
                     for fc in self.farm_crops.all())) / ac)

    def expected_total_bushels(self, yf=None):
        return sum((fc.sens_farm_expected_yield(yf=yf) * fc.planted_acres
                    for fc in self.farm_crops.all() if fc.has_budget()))

    def futures_pct_of_expected(self, yf=None):
        tot = self.expected_total_bushels(yf=yf)
        return (0 if tot == 0 else self.contracted_bu() / tot)

    def basis_pct_of_expected(self, yf=None):
        tot = self.expected_total_bushels(yf=yf)
        return (0 if tot == 0 else self.basis_bu_locked() / tot)

    def production_frac_for_farm_crop(self, farmcrop, yf=None):
        expbu = self.expected_total_bushels(yf)
        return (0 if expbu == 0 else
                (farmcrop.sens_farm_expected_yield(yf) * farmcrop.planted_acres /
                 expbu))

    class Meta:
        ordering = ['market_crop_type_id']


class Contract(models.Model):
    """
    Represents a futures or basis contract
    If a manual model_run_date is set, we should warn the user that contracts with
    contract date in the future are not displayed or included in budget or sensitivity.
    Otherwise, they might think they missed one and add a duplicate contract.
    """
    is_basis = models.BooleanField(
        default=False,
        help_text='Specifies a basis contract instead of a futures contract.')

    contract_date = models.DateField(default=datetime.today)

    bushels = models.FloatField(default=0, validators=[MinVal(0), MaxVal(999999)])

    price = models.FloatField(
        default=0, validators=[MinVal(-2), MaxVal(30)], verbose_name="price per bushel")

    terminal = models.CharField(max_length=60, blank=True)

    contract_number = models.CharField(max_length=25, blank=True)

    delivery_start_date = models.DateField(null=True, blank=True)

    delivery_end_date = models.DateField(null=True, blank=True)

    market_crop = models.ForeignKey(
        MarketCrop, on_delete=models.CASCADE, related_name='contracts')

    class Meta:
        ordering = ['contract_date']
