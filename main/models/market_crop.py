from datetime import datetime
import numpy as np
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator as MinVal, MaxValueValidator as MaxVal)
from django.db import models
from ext.models import FuturesPrice, MarketCropType
from .farm_year import FarmYear
from .fsa_crop import FsaCrop
from .util import scal


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

    def __init__(self, *args, **kwargs):
        self.futures_contracted_bu_mem = None
        self.basis_contracted_bu_mem = None
        self.avg_futures_contract_price_mem = None
        self.avg_basis_contract_price_mem = None
        self.planted_acres_mem = None
        self.harvest_futures_price_info_mem = None
        self.planted_acres_mem = None
        self.sens_farm_expected_yield_mem = None
        self.expected_total_bushels_mem = None

        super().__init__(*args, **kwargs)

    def __str__(self):
        return f'{self.market_crop_type}'

    def futures_contracted_bu(self):
        if self.futures_contracted_bu_mem is None:
            self.futures_contracted_bu_mem = sum(
                c.bushels for c in self.get_contracts()
                if c.futures_price is not None)
        return self.futures_contracted_bu_mem

    def basis_contracted_bu(self):
        if self.basis_contracted_bu_mem is None:
            self.basis_contracted_bu_mem = sum(
                c.bushels for c in self.get_contracts()
                if c.basis_price is not None)
        return self.basis_contracted_bu_mem

    def avg_futures_contract_price(self):
        if self.avg_futures_contract_price_mem is None:
            amounts = [c.futures_price*c.bushels for c in self.get_contracts()
                       if c.futures_price is not None]
            tot_bu = self.futures_contracted_bu()
            self.avg_futures_contract_price_mem = (sum(amounts) / tot_bu
                                                   if tot_bu > 0 else 0)
        return self.avg_futures_contract_price_mem

    def avg_basis_contract_price(self):
        if self.avg_basis_contract_price_mem is None:
            amounts = [c.basis_price*c.bushels for c in self.get_contracts()
                       if c.basis_price is not None]
            tot_bu = self.basis_contracted_bu()
            self.avg_basis_contract_price_mem = (sum(amounts) / tot_bu
                                                 if tot_bu > 0 else 0)
        return self.avg_basis_contract_price_mem

    def get_contracts(self):
        model_run_date = self.farm_year.get_model_run_date()
        return self.contracts.filter(contract_date__lte=model_run_date)

    def get_planned_contracts(self):
        model_run_date = self.farm_year.get_model_run_date()
        return self.contracts.filter(contract_date__gt=model_run_date)

    def harvest_price(self):
        return self.harvest_futures_price_info(price_only=True)

    def sens_harvest_price(self, pf=None):
        """ array 1d or scalar """
        if pf is None:
            pf = self.price_factor
        return self.harvest_futures_price_info(price_only=True) * pf

    def harvest_futures_price_info(self, priced_on=None, price_only=False):
        """
        Get the harvest price for the given date from the correct exchange for the
        crop type and county.  Note: insurancedates gives the exchange and ticker.
        """
        if not price_only or self.harvest_futures_price_info_mem is None:
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

            self.harvest_futures_price_info_mem = None if rec is None else rec.price
        return self.harvest_futures_price_info_mem if price_only else rec

    def planted_acres(self):
        if self.planted_acres_mem is None:
            self.planted_acres_mem = sum((fc.planted_acres
                                          for fc in self.farm_crops.all()))
        return self.planted_acres_mem

    def county_bean_yield(self, yf=None):
        """
        for indemnity calculations (only called when final RMA yield is not known)
        1d array or scalar
        """
        ac = self.planted_acres()
        return (0 if scal(yf) and (self.market_crop_type_id != 2 or ac == 0) else
                np.zeros_like(yf) if self.market_crop_type_id != 2 or ac == 0 else
                sum((fc.sens_cty_expected_yield(yf)[0] * fc.planted_acres
                     for fc in self.farm_crops.all())) / ac)

    def expected_total_bushels(self, yf=None):
        if self.expected_total_bushels_mem is None:
            self.expected_total_bushels_mem = sum(
                (fc.sens_farm_expected_yield(yf=yf) * fc.planted_acres
                 for fc in self.farm_crops.all()))
        return self.expected_total_bushels_mem

    def futures_pct_of_expected(self, yf=None):
        tot = self.expected_total_bushels(yf=yf)
        return (0 if tot == 0 else self.futures_contracted_bu() / tot)

    def basis_pct_of_expected(self, yf=None):
        tot = self.expected_total_bushels(yf=yf)
        return (0 if tot == 0 else self.basis_contracted_bu() / tot)

    def production_frac_for_farm_crop(self, farmcrop, yf=None):
        """ scalar or array(ny)  """
        if scal(yf):
            expbu = self.expected_total_bushels(yf)
            return (0 if expbu == 0 else
                    (farmcrop.sens_farm_expected_yield(yf) * farmcrop.planted_acres /
                     expbu))
        else:
            expbu = self.expected_total_bushels(yf)
            return (np.zeros_like(yf) if expbu.all() == 0 else
                    (farmcrop.sens_farm_expected_yield(yf) * farmcrop.planted_acres /
                     expbu))

    class Meta:
        ordering = ['market_crop_type_id']


class Contract(models.Model):
    """
    Represents a futures / basis contract
    If a manual model_run_date is set, we should warn the user that contracts with
    contract date in the future are not displayed or included in budget or sensitivity.
    Otherwise, they might think they missed one and add a duplicate contract.
    """
    contract_date = models.DateField(default=datetime.today)

    bushels = models.FloatField(default=0, validators=[MinVal(1), MaxVal(999999)])

    futures_price = models.FloatField(
        null=True, blank=True, verbose_name="futures price per bushel")

    basis_price = models.FloatField(
        null=True, blank=True,
        verbose_name="basis price per bushel")

    terminal = models.CharField(max_length=60, blank=True)

    contract_number = models.CharField(max_length=25, blank=True)

    delivery_start_date = models.DateField(null=True, blank=True)

    delivery_end_date = models.DateField(null=True, blank=True)

    market_crop = models.ForeignKey(
        MarketCrop, on_delete=models.CASCADE, related_name='contracts')

    class Meta:
        ordering = ['contract_date']

    def clean(self):
        if self.futures_price is not None and self.futures_price < 1:
            raise ValidationError(
                {'futures_price': 'Futures price must be at least $1.00'})
        if self.futures_price is not None and self.futures_price > 25:
            raise ValidationError(
                {'futures_price': 'Futures price must be less than $25.00'})
        if self.basis_price is not None and self.basis_price < -2:
            raise ValidationError(
                {'basis_price': 'Basis price must be at least -$2.00'})
        if self.basis_price is not None and self.basis_price > 2:
            raise ValidationError(
                {'basis_price': 'Basis price must be less than $2.00'})
