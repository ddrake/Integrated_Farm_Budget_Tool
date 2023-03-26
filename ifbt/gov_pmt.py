"""
Module gov_pmt

Contains a single class, GovPmt, which loads its data from text files
for a given crop year when an instance is created.  Its main function
is to return total estimated government payment for the farm for the given
crop year corresponding to arbitrary sensitivity factors for price and yield.
"""
import os

import numpy as np

from .analysis import Analysis
from .util import crop_in, Crop, Prog, Prac


DATADIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


class GovPmt(Analysis):
    """
    Computes total estimated cost for the farm crop year
    corresponding to arbitrary sensitivity factors for price and yield.
    TODO: Do we need to support ARC-IC?
    TODO: If a farmer has e.g. irrigated and non-irrigated full and dc
    soybeans, in two counties, she has to maintain separate base acres and plc yields
    for all 16 combinations -- right? If not, how can she use the spreadsheet tools?
    Gov payment doesn't distinguish full and dc, but crop insurance does.
    Does this give the farmer any flexibility, or must she put all soybean acres in
    the same program, unit, protection, level, option, tause, etc..?

    User inputs are base_acres[crop][prac] and plc_yield[crop][prac]

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

        assert self.crop_year >= 2019, "Crop year must be greater than or equal to 2019"
        self.crop_ids = {Crop.CORN: 1, Crop.SOY: 2, Crop.WHEAT: 3}
        self.fsa_yields = get_fsa_yields()
        self.mya_prices = get_mya_prices()
        self.ref_prices = get_ref_prices()
        self.co_tayields = get_co_tayields()
        # These tables are not used, except to check Table 3.
        # Instead co_tayields is used directly.
        self.tyields = get_tyields()
        self.tayields = get_tayields()
        self.counties = get_counties()
        self.practices = ((Prac.IRR, Prac.NONIRR)
                          if self.counties[str(self.county)] == 1 else
                          (Prac.ALL,))
        self.codes = {crop: {prac: self.county * 1000 + self.crop_ids[crop] * 10 + prac
                             for prac in self.practices}
                      for crop in self.crop_ids.keys()}

    # Government Payment Totals
    # -------------------------
    def total_gov_pmt(self, pf=1, yf=1):
        """
        Government Payments AB60: Sensitized total government payment after
        application of cap.
        TODO: The excel tool doesn't seem to consider payment cap.
        """
        return round(
            min(self.prog_pmt_post_sequest(pf, yf),
                self.fsa_pmt_cap_per_principal * self.number_of_principals))

    def prog_pmt_post_sequest(self, pf=1, yf=1):
        """
        Government Payments AB58: Sensitized, post-sequestration government
        program payment total.
        TODO: The excel tool doesn't seem to consider sequestration fraction
        """
        return self.prog_pmt_pre_sequest(pf, yf) * (1 - self.sequest_frac)

    def prog_pmt_pre_sequest(self, pf=1, yf=1):
        """
        Government Payments AB56: Sensitized, pre-sequestration
        government program payment total
        """
        return sum([self.prog_pmt_pre_sequest_crop(crop, prac, pf, yf)
                    for crop in [Crop.CORN, Crop.SOY, Crop.WHEAT]
                    for prac in self.practices])

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def prog_pmt_pre_sequest_crop(self, crop, prac, pf=1, yf=1):
        """
        Government Payments Y56:AA56: Sensitized pre-sequestration payment
        for the selected program and specified crop.
        """
        return (self.arc_pmt_pre_sequest(crop, prac, pf, yf)
                if self.program[crop] == Prog.ARC_CO else
                self.plc_pmt_pre_sequest(crop, prac, pf))

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def mya_prices_2yr_lag(self, crop):
        """
        Get MYA prices for 5 years up to 2 years before crop_year
        """
        first_year, first_year_idx = 2013, 1
        start = first_year_idx + self.crop_year - first_year - 7
        return np.array(self.mya_prices[self.crop_ids[crop]][start:start+5])

    # PLC
    # ---
    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def plc_pmt_pre_sequest(self, crop, prac, pf=1):
        """
        Price-sensitized pre-sequestration PLC payment for the crop.
        """
        return (self.plc_payment_per_base_acre(crop, prac, pf) *
                self.farm_base_acres[crop][prac])

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def plc_payment_per_base_acre(self, crop, prac, pf=1):
        """
        H76
        Government Payments Y19:AA19: Price-sensitized helper for plc_payment rate
        for the crop
        """
        return (self.plc_payment_rate(crop, pf) *
                self.base_to_net_pmt_frac * self.plc_yield(crop, prac))

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def plc_yield(self, crop, prac):
        """
        (H76): If the farmer has provided this info (plc_yield[crop][prac]), use it;
        otherwise use the default yield.
        TODO: I think there is a bug in Excel; they are multiplying in the
        base_to_net_pmt_frac (0.85) twice!  First, it is multiplied into the plc_yield
        (X2), then again in the plc_payment_per_base_acre (H76)
        TODO: Is the farm's plc yield for a given crop year based on the same two year
        lag calculation?  If so, we should not use a yield factor here.
        """
        idx_2013 = 0
        idx = idx_2013 + self.crop_year - 2013 - 7
        return (self.farm_plc_yield[crop][prac] if hasattr(self, 'farm_plc_yield') else
                round(safe_avg(self.fsa_yields[self.codes[crop][prac]][idx:idx+5]), 0))

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def plc_payment_rate(self, crop, pf=1):
        """
        H74
        Government Payments Y19:AA19: Price-sensitized helper for plc_payment rate
        for the crop
        """
        return max(0, self.effective_reference_price(crop) -
                   max(self.cur_year_mya_price(crop, pf),
                       self.loan_rate(crop)))

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def effective_reference_price(self, crop):
        """
        H70
        """
        statref = self.statutory_reference_price(crop)
        return min(max(statref, self.mya_olympic_avg_price_85(crop)),
                   self.rate_cap_factor_new_escal * statref)

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def loan_rate(self, crop):
        """
        H73
        """
        return self.ref_prices[self.crop_ids[crop]][0]

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def statutory_reference_price(self, crop):
        """
        H69
        """
        idx1year = 2019
        return self.ref_prices[self.crop_ids[crop]][1 + self.crop_year - idx1year]

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def mya_olympic_avg_price_85(self, crop):
        """
        H68
        """
        return round(0.85 * olympic_avg(self.mya_prices_2yr_lag(crop)), 2)

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def cur_year_mya_price(self, crop, pf=1):
        """
        H72: Current year marketing price.
        TODO: It seems to me that the price factor should have a smaller effect on this
        price, the farther we are into the marketing year, e.g. if we are in month 9
        of the marketing year, we could do:
        (9/12*mya_price + 3/12*offset_harvest_futures*pf).
        """
        first_year = 2013
        idx = self.crop_year - first_year
        return self.mya_prices[self.crop_ids[crop]][idx]

    # ARC-CO
    # ------
    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def arc_pmt_pre_sequest(self, crop, prac, pf=1, yf=1):
        """
        Government Payments Y48:AA48: Sensitized ARC payment pre-sequestration
        for the crop.
        """
        return (self.farm_base_acres[crop][prac] *
                self.arc_payment_per_base_acre(crop, prac, pf, yf))

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def arc_payment_per_base_acre(self, crop, prac, pf=1, yf=1):
        """
        H16
        """
        return round(self.base_to_net_pmt_frac *
                     min(max(0, self.guarantee(crop, prac) -
                             self.county_revenue(crop, prac, pf)),
                         self.cap_on_bmk_county_rev * self.benchmark_yield(crop, prac) *
                         self.benchmark_price(crop)), 2)

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def guarantee(self, crop, prac):
        """
        M16
        """
        return round(self.guar_rev_frac * self.benchmark_yield(crop, prac) *
                     self.benchmark_price(crop), 2)

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def county_revenue(self, crop, prac, pf=1):
        """
        N16: County Revenue
        TODO: I don't think we should sensitize county_yield, since county_yield is just
        benchmark yield, which is trend-adjusted, but with a two year lag, and hence
        doesn't include the current crop year's actual or projected yield.
        """
        return round(self.county_yield(crop, prac) *
                     self.mya_price(crop, pf), 2)

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def benchmark_yield(self, crop, prac):
        """
        K16: Olympic average over first five values of set of six, where there is a
        one year gap between the last of the five and the sixth.
        TODO: The spreadsheet column names in Table 3. are misleading.  They do not
        accurately represent the corresponding formulas.  They seem to be artifacts
        from an earlier version, in which the Trend-Adjusted ARC-CO yields were
        calculated in that table, from values in TA and Tyields.  Now, these yields are
        simply read from coTAyields and the preceding columns are values trying to
        indicate how they are computed.  If we think that the coTAyields sheet is
        computed by U of I from the TA and Tyields tables, we could compute coTAyields
        ourselves.  However, TA has missing values for many years/counties and some of
        the yields do not match fsa yields (see alt_co_tayields)
        """
        years_in_group, group1_year = 6, 2019
        group = self.crop_year - group1_year
        start = years_in_group * group
        return round(olympic_avg(
            self.co_tayields[self.codes[crop][prac]][start:start+5]), 2)

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def alt_co_tayields(self, crop, prac):
        """
        Try to compute co_tayields 5-years values based on headings in Table 3.
        TODO: Column D heading 'County Yield' is potentially confusing.  These look like
        FSA yields, except for a couple years that are different.  The footnote
        says they come from RMA, which, if true, may be the key.
        TODO: Column E heading states 0.85 of T-yield, but no factor is applied. Is the
        factor already applied to all values on the Tyields sheet?  Or perhaps omitted
        by accident?  Maybe they intended to multiply in the factor in BT2:BX2, but
        duplicated it in X2 by mistake (see above)
        TODO: Values match for Madison Cty. corn except for 2018 and 2021
              Values match for Madison Cty. soy except for same two years.
              Values match for Madison Cty. wheat except for 2017, 2018, and 2021
        """
        idx2019 = 0
        idx = idx2019 + self.crop_year-2019
        tayield = get_tayields()[self.codes[crop][prac]][idx]
        # Not the same as self.county_yield(crop), comes from RMA e.g. Madison Cty
        idx2013 = 0
        start = idx2013 + 2017-2013
        county_yields = np.array(
            self.fsa_yields[self.codes[crop][prac]][start: start+5])
        idx2013 = 0
        start = idx2013 + 2017-2013
        tyields = np.array(get_tyields()[self.codes[crop][prac]][start:start+5])
        nyears_trend = np.arange(6, 1, -1)
        trend_yield_adj = nyears_trend * tayield
        co_tayield = np.maximum(county_yields, tyields) + trend_yield_adj
        print('county_yields', county_yields)
        print('trend_yield_adj', trend_yield_adj)
        print('co_tayield', co_tayield)

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def benchmark_price(self, crop):
        """
        L16
        """
        return round(olympic_avg(
            np.maximum(self.mya_prices_2yr_lag(crop),
                       self.effective_reference_price(crop))), 2)

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def county_yield(self, crop, prac):
        """
        D16
        TODO: According to footnote 1. in Calculation of PLC and ARC-CO payments, the
        2018 yields enter into 2020 benchmark yield calculations.  The 2018 yield is an
        estimate.  Not sure how to interpret this...
        """
        idx2013 = 0
        idx2018 = idx2013 + 2018-2013

        return (self.fsa_yields[self.codes[crop][prac]][idx2018]
                if self.crop_year == 2019 else
                self.benchmark_yield(crop, prac))

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def mya_price(self, crop, pf=1):
        """
        E16: MYA Price (same value used for all counties for given crop).
        TODO: I think that estimates of the MYA price are available throughout the year,
        and that this value is fixed at harvest.  It seems that the excel tool is just
        using the 2022 value currently for the 2023 price, rather than a more current
        estimate.  We can and probably should update the 2023 price based on current
        estimates and even put in a reasonable estimate for the 2024 price.  It seems
        to me that the price factor should have a smaller effect on this price, the
        farther we are into the marketing year, e.g. if we are in month 9 of the
        marketing year, we could do (9/12*mya_price + 3/12*harvest_futures).
        """
        first_year = 2013
        idx = self.crop_year - first_year
        avail_mya_prices = self.mya_prices[self.crop_ids[crop]]
        return (avail_mya_prices[idx] if idx < len(avail_mya_prices) else
                self.estimated_mya_price[crop]) * pf


# Get lookups
# -----------
def load(filename, processor, **kwargs):
    """
    Try to load a pickle file with the filename.  If it doesn't exist, load the
    textfile, create its dict, and save its dict to a pickle file.
    """
    with open(f'{DATADIR}/{filename}.txt', 'r') as f:
        contents = f.read()
        items = (line.split() for line in contents.strip().split('\n'))
        data = processor(items, **kwargs)
    return data


def special_counties(items):
    return {f'{int(stcode):02}{int(ctycode):03}': irrig
            for stcode, ctycode, _, _, irrig in items}


def int_key_float_tuple(items):
    return {int(item[0]): tuple(float(it) for it in item[1:]) for item in items}


def get_fsa_yields():
    # FSAyields columns: code, fsa2013 : fsa2023
    return load('FSAyields', int_key_float_tuple)


def get_mya_prices():
    # MYAprices columns cropId, 2013 : 2023
    return load('MYAprices', int_key_float_tuple)


def get_ref_prices():
    # Refprices columns: CropId, LoanRate, 2019 : 2023
    return load('Refprices', int_key_float_tuple)


def get_co_tayields():
    # 5 end year blocks, each with 6 years (5 years, skip a year, end year)
    # coTAyields columns: code, ta2013-19, ta2014-19,..., ta2017-19, ta2019-19,
    #                             ...
    #                           ta2017-23, ta2018-23,..., ta2021-23, ta2023-23
    return load('coTAyields', int_key_float_tuple)


def get_tyields():
    # Tyields columns: code, ty2013,ty2014,...,ty2023
    return load('Tyields', int_key_float_tuple)


def get_tayields():
    # Note: many missing and #N/A values are present
    # TA columns: code, 2019 taYield, 2020 taYield, ..., 2023 taYield
    return load('TA', int_key_float_tuple)


def get_counties():
    return load('counties', special_counties)


# Averaging helpers
# -----------------
def safe_avg(nums):
    """
    Given some numbers, which may contain N/A or missing values represented by -1,
    return the average of the postive values or raise an error if they are all missing.
    TODO:  For our purposes, I think an approximate average or olympic average
    is better than refusing to compute anything.
    """
    if -1 in nums:
        clean = [n for n in nums if n != -1]
        if len(clean) == 0:
            raise ValueError("Can't compute average, all values missing.")
        return sum(clean)/len(clean)
    return sum(nums)/len(nums)


def olympic_avg(nums):
    """
    Given some numbers, which may contain N/A or missing values represented by -1,
    Return the olympic average if no -1 values are present, raise an error
    if all values are missing, and return a simple average if at least one
    non-negative value is present.
    """
    cnums = list(nums)
    if -1 in nums:
        clean = [n for n in cnums if n != -1]
        if len(clean) == 0:
            raise ValueError("Can't compute olympic average, all values missing.")
        return sum(clean)/len(clean)
    nmin, nmax = min(cnums), max(cnums)
    cnums.remove(nmin)
    cnums.remove(nmax)
    return sum(cnums)/len(cnums)

    # @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    # def assumed_mya_price(self, crop, pf=1):
    #     """
    #     Government Payments Y38:AA38 -> AR16:AT16:
    #     Price-sensitized marketing Year Avg Price for the crop.
    #     """

    #     return (self.fall_futures_price[crop] * pf -
    #             self.decrement_from_futures_to_mya[crop])

    # @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    # def arc_pmt_rate(self, crop, pf=1, yf=1):
    #     """
    #     Government Payments Y44:AA44: Sensitized ARC Payment rate
    #     for the crop.
    #     """
    #     return min(self.arc_capped_bmk_revenue(crop),
    #                self.revenue_shortfall(crop, pf, yf))

    # @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    # def arc_capped_bmk_revenue(self, crop):
    #     """
    #     Government Payments Y43:AA43: ARC 10 percent cap
    #     on Benchmark County Revenue for the crop.
    #     """
    #     return (self.arc_bmk_county_revenue(crop) *
    #             self.cap_on_bmk_county_rev)

    # @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    # def revenue_shortfall(self, crop, pf=1, yf=1):
    #     """
    #     Government Payments Y42:AA42: Sensitized revenue shortfall
    #     for the crop.
    #     """
    #     return max(0, (self.arc_guar_revenue(crop) -
    #                    self.actual_crop_revenue(crop, pf, yf)))

    # @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    # def actual_crop_revenue(self, crop, pf=1, yf=1):
    #     """
    #     Government Payments Y41:AA41: price/yield-sensitized actual
    #     revenue for the crop.
    #     """
    #     return (max(self.assumed_mya_price(crop, pf),
    #                 self.natl_loan_rate[crop]) *
    #             self.arc_county_rma_yield(crop, yf))

    # @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    # def arc_county_rma_yield(self, crop, yf=1):
    #     """
    #     Government Payments Y40:AA40 -> AR25:AT25: Yield-sensitized County
    #     actual/est yield (RMA) for the crop.
    #     Note: this is NOT the same as the county_rma_yield in the base class
    #     """
    #     return self.est_county_yield[crop] * yf

    # @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    # def effective_price(self, crop, pf=1):
    #     """
    #     Government Payments Y18:AA18: The price-sensitized effective price
    #     for the crop.
    #     """
    #     return max(self.natl_loan_rate[crop],
    #                self.assumed_mya_price(crop, pf))

    # @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    # def net_payment_acres(self, crop):
    #     """
    #     Government Payments Y10:AA10: Net Payment Acres (85 percent of base)
    #     for the crop.
    #     """
    #     return (self.base_to_net_pmt_frac * self.farm_base_acres[crop])

    # @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    # def plc_pmt_pre_sequest(self, crop, pf=1):
    #     """
    #     Government Payments Y23:AA23: Price-sensitized pre-sequestration PLC payment
    #     for the crop.
    #     """
    #     return (self.plc_payment_rate(crop, pf) * self.net_payment_acres(crop) *
    #             self.farm_plc_yield[crop])

    # @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    # def plc_payment_rate(self, crop, pf=1):
    #     """
    #     Government Payments Y21:AA21: The price-sensitized PLC payment rate
    #     for the crop
    #     """
    #     return min(self.plc_payment_rate1(crop, pf),
    #                self.max_plc_payment_rate(crop))

    # @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    # def max_plc_payment_rate(self, crop):
    #     """
    #     Government Payments Y20:AA20: The maximum PLC payment rate for the crop
    #     """
    #     return (self.stat_ref_rate_farm_bill[crop] -
    #             self.natl_loan_rate[crop])

    # @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    # def effective_ref_rate(self, crop):
    #     """
    #     Government Payments Y15:AA15: The effective reference rate for the crop.
    #     """
    #     return max(self.stat_ref_rate_farm_bill[crop],
    #                min(self.stat_ref_rate_new_escal[crop],
    #                    self.rate_cap_factor_new_escal *
    #                    self.stat_ref_rate_farm_bill[crop]))
