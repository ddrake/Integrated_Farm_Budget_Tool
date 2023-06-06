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

    def __str__(self):
        return f'{self.market_crop_type}'

    def harvest_futures_price_info(self, priced_on=None, price_only=False):
        """
        Get the harvest price for the given date from the correct exchange for the
        crop type and county.  Note: insurancedates gives the exchange and ticker.
        """
        if priced_on is None:
            priced_on = self.farm_year.get_model_run_date()

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
