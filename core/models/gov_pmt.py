"""
Module gov_pmt

Contains a single class, GovPmt, which loads its data from text files
for a given crop year when an instance is created.  Its main function
is to return total estimated government payment for the farm for the given
crop year corresponding to arbitrary sensitivity factors for price and yield.

The source data (effective reference price and benchmark county revenue) is
downloaded for a crop year here:
https://www.fsa.usda.gov/programs-and-services/arcplc_program/arcplc-program-data/index
in the form of two spreadsheets, e.g. 2023_erp.xls and arcco_2023_data_2023-02-16.xlsx
"""
import os
import pickle

# import numpy as np

from analysis import Analysis
from util import crop_in, Crop, BASE_CROPS

DATADIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


class GovPmt(Analysis):
    """
    Computes total estimated cost for the farm crop year
    corresponding to arbitrary sensitivity factors for price and yield.

    Sample usage in a python or ipython console:
      from ifbt import GovPmt
      p = GovPmt(2023)
      p.total_pmt()               # pf and yf default to 1
      p.total_pmt(pf=.9, yf=1.1)  # specifies both price and yield factors
      p.total_pmt(yf=1.2)         # uses default for pf
    """

    DATA_FILES = 'farm_data gov_pmt_data'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.benchmark_revenue = self.load_benchmark_revenue()
        # Lookup keys for benchmark county revenue
        self.codes = [f'{self.county:05d}{crop:d}{self.arc_practice[crop]}'
                      for crop in (Crop.CORN, Crop.SOY, Crop.WHEAT)]

    # Government Payment Totals
    # -------------------------
    @crop_in(*BASE_CROPS)
    def total_gov_pmt_crop(self, crop, pf=1, yf=1):
        tot = self.total_gov_pmt(pf, yf)
        return (0 if tot == 0 else
                tot * self.prog_pmt_pre_sequest_crop(crop, pf, yf) /
                self.prog_pmt_pre_sequest(pf, yf))

    def total_gov_pmt(self, pf=1, yf=1):
        """
        Government Payments AB60: Sensitized total government payment after
        application of cap
        """
        return round(
            min(self.prog_pmt_post_sequest(pf, yf),
                self.fsa_pmt_cap_per_principal * self.number_of_principals))

    def prog_pmt_post_sequest(self, pf=1, yf=1):
        """
        Government Payments AB58: Sensitized, post-sequestration government
        program payment total.
        """
        return self.prog_pmt_pre_sequest(pf, yf) * (1 - self.sequest_frac)

    def prog_pmt_pre_sequest(self, pf=1, yf=1):
        """
        Government Payments AB56: Sensitized, pre-sequestration
        government program payment total
        """
        return sum([self.prog_pmt_pre_sequest_crop(crop, pf, yf)
                    for crop in BASE_CROPS])

    @crop_in(*BASE_CROPS)
    def prog_pmt_pre_sequest_crop(self, crop, pf=1, yf=1):
        """
        Government Payments Y56:AA56: Sensitized pre-sequestration payment
        for the selected program and specified crop.
        """
        return (self.arc_pmt_pre_sequest(crop, pf, yf) +
                self.plc_pmt_pre_sequest(crop, pf))

    # PLC
    # ---
    @crop_in(*BASE_CROPS)
    def plc_pmt_pre_sequest(self, crop, pf=1):
        """
        Government Payments Y23:AA23: Price-sensitized pre-sequestration PLC payment
        for the crop.
        """
        return (self.plc_payment_rate(crop, pf) * self.net_payment_acres_plc(crop) *
                self.farm_plc_yield[crop])

    @crop_in(*BASE_CROPS)
    def plc_payment_rate(self, crop, pf=1):
        """
        Government Payments Y21:AA21: The price-sensitized PLC payment rate
        for the crop
        """
        return min(self.plc_payment_rate1(crop, pf),
                   self.max_plc_payment_rate(crop))

    @crop_in(*BASE_CROPS)
    def net_payment_acres_plc(self, crop):
        """
        Government Payments Y10:AA10: Net Payment Acres (85 percent of base)
        for the crop.
        """
        return (self.base_to_net_pmt_frac *
                self.farm_base_acres_plc[crop])

    @crop_in(*BASE_CROPS)
    def plc_payment_rate1(self, crop, pf=1):
        """
        Government Payments Y19:AA19: Price-sensitized helper for plc_payment rate
        for the crop
        """
        return max(self.effective_ref_price[crop] - self.effective_price(crop, pf), 0)

    @crop_in(*BASE_CROPS)
    def max_plc_payment_rate(self, crop):
        """
        Government Payments Y20:AA20: The maximum PLC payment rate for the crop
        """
        return self.stat_ref_rate_farm_bill[crop] - self.natl_loan_rate[crop]

    @crop_in(*BASE_CROPS)
    def effective_price(self, crop, pf=1):
        """
        Government Payments Y18:AA18: The price-sensitized effective price
        for the crop.
        """
        return max(self.natl_loan_rate[crop],
                   self.assumed_mya_price(crop, pf))

    # ARC-CO
    # ------
    @crop_in(*BASE_CROPS)
    def arc_pmt_pre_sequest(self, crop, pf=1, yf=1):
        """
        Government Payments Y48:AA48: Sensitized ARC payment pre-sequestration
        for the crop.
        """
        return self.net_payment_acres_arc(crop) * self.arc_pmt_rate(crop, pf, yf)

    @crop_in(*BASE_CROPS)
    def net_payment_acres_arc(self, crop):
        """
        Government Payments Y10:AA10: Net Payment Acres (85 percent of base)
        for the crop.
        """
        return (self.base_to_net_pmt_frac *
                self.farm_base_acres_arc[crop])

    @crop_in(*BASE_CROPS)
    def arc_pmt_rate(self, crop, pf=1, yf=1):
        """
        Government Payments Y44:AA44: Sensitized ARC Payment rate
        for the crop.
        """
        return min(self.arc_capped_bmk_revenue(crop),
                   self.revenue_shortfall(crop, pf, yf))

    @crop_in(*BASE_CROPS)
    def arc_capped_bmk_revenue(self, crop):
        """
        Government Payments Y43:AA43: ARC 10 percent cap
        on Benchmark County Revenue for the crop.
        """
        return (self.arc_bmk_county_revenue(crop) *
                self.cap_on_bmk_county_rev)

    @crop_in(*BASE_CROPS)
    def revenue_shortfall(self, crop, pf=1, yf=1):
        """
        Government Payments Y42:AA42: Sensitized revenue shortfall
        for the crop.
        """
        return max(0, (self.arc_guar_revenue(crop) -
                       self.actual_crop_revenue(crop, pf, yf)))

    @crop_in(*BASE_CROPS)
    def arc_bmk_county_revenue(self, crop):
        """
        Government Payments Y35:AA35: ARC Benchmark County Revenue for the crop.
        """
        return self.benchmark_revenue[self.codes[crop]]

    @crop_in(*BASE_CROPS)
    def arc_guar_revenue(self, crop):
        """
        Government Payments Y36:AA36: ARC Guarantee Revenue
        (86 percent of Benchmark County revenue)
        """
        return (self.arc_bmk_county_revenue(crop) * self.guar_rev_frac)

    @crop_in(*BASE_CROPS)
    def actual_crop_revenue(self, crop, pf=1, yf=1):
        """
        Government Payments Y41:AA41: price/yield-sensitized actual
        revenue for the crop.
        """
        return (max(self.assumed_mya_price(crop, pf),
                    self.natl_loan_rate[crop]) *
                self.arc_county_rma_yield(crop, yf))

    @crop_in(*BASE_CROPS)
    def arc_county_rma_yield(self, crop, yf=1):
        """
        Government Payments Y40:AA40 -> AR25:AT25: Yield-sensitized County
        actual/est yield (RMA) for the crop.
        Note: this is NOT the same as the county_rma_yield in the base class
        """
        return self.est_county_yield[crop] * yf

    # Used by both programs
    # ---------------------
    @crop_in(*BASE_CROPS)
    def assumed_mya_price(self, crop, pf=1):
        """
        Government Payments Y38:AA38 -> AR16:AT16:
        Price-sensitized marketing Year Avg Price for the crop.
        """

        return (self.fall_futures_price[crop] * pf -
                self.decrement_from_futures_to_mya[crop])

    # Data loaded in constructor
    # --------------------------
    def load_benchmark_revenue(self):
        """
        Load textfile, create and return a dict with key county-crop and value
        benchmark revenue.
        """
        picklename = f'{DATADIR}/benchmark_revenue_{self.crop_year}.pkl'
        with open(picklename, 'rb') as f:
            data = pickle.load(f)
        return data
