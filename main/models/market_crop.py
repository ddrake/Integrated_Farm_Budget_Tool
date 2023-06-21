from django.core.validators import (
    MinValueValidator as MinVal, MaxValueValidator as MaxVal)
from django.db import models
from ext.models import FuturesPrice, MarketCropType
from .farm_year import FarmYear, BaselineFarmYear
from .fsa_crop import FsaCrop, BaselineFsaCrop


class MarketCrop(models.Model):
    """
    A crop which can be marketed and which has a unique set of futures prices
    for a given county.
    """
    contracted_bu = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="contracted bushels",
        help_text="Current contracted bushels on futures.")
    avg_contract_price = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(30)],
        verbose_name="avg. contract price",
        help_text="Average price for futures contracts.")
    basis_bu_locked = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="bushels with basis locked",
        help_text="Number of bushels with contracted basis set.")
    avg_locked_basis = models.FloatField(
        default=0, validators=[MinVal(-2), MaxVal(2)],
        verbose_name="avg. locked basis",
        help_text="Average basis on basis contracts in place.")
    assumed_basis_for_new = models.FloatField(
        default=0, validators=[MinVal(-2), MaxVal(2)],
        help_text="Assumed basis for non-contracted bushels.")
    farm_year = models.ForeignKey(FarmYear, on_delete=models.CASCADE,
                                  related_name='market_crops')
    market_crop_type = models.ForeignKey(MarketCropType, on_delete=models.CASCADE)
    fsa_crop = models.ForeignKey(FsaCrop, on_delete=models.CASCADE,
                                 related_name='market_crops')
    price_factor = models.FloatField(default=1, validators=[MinVal(0), MaxVal(10)],
                                     verbose_name='price sensititivity factor')

    def __str__(self):
        return f'{self.market_crop_type}'

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
        if priced_on is None:
            priced_on = self.farm_year.get_model_run_date()

        rec = FuturesPrice.objects.raw("""
        SELECT fp.id, fp.exchange, fp.futures_month, fp.ticker, fp.priced_on, fp.price
            FROM ext_futuresprice fp
            INNER JOIN (
            SELECT crop_year, state_id, county_code, market_crop_type_id, ticker
            FROM ext_insurancedates idt
            WHERE crop_year=%s and state_id=%s and county_code=%s
              and market_crop_type_id=%s) idt
            ON fp.ticker = idt.ticker
            WHERE fp.priced_on <= %s
            order by priced_on desc limit 1;
        """, params=[self.farm_year.crop_year, self.farm_year.state_id,
                     self.farm_year.county_code, self.market_crop_type_id,
                     priced_on])[0]
        return rec.price if price_only else rec

    def planted_acres(self):
        return sum((fc.planted_acres for fc in self.farm_crops.all()))

    def yield_factor(self):
        return sum((fc.yield_factor * fc.planted_acres
                    for fc in self.farm_crops.all())) / self.planted_acres()

    class Meta:
        ordering = ['market_crop_type_id']


class BaselineMarketCrop(models.Model):
    market_crop_type = models.ForeignKey(MarketCropType, on_delete=models.CASCADE)
    farm_year = models.ForeignKey(BaselineFarmYear, on_delete=models.CASCADE,
                                  related_name='market_crops')
    fsa_crop = models.ForeignKey(BaselineFsaCrop, on_delete=models.CASCADE,
                                 related_name='market_crops')
