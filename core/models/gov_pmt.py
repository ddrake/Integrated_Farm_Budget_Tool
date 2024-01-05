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
import numbers
import numpy as np


class GovPmt():
    """
    Computes the total pre-sequestration payment (ARC-CO + PLC) for a crop
    corresponding to arbitrary sensitivity factors for price and yield.
    """

    BASE_TO_NET_PMT_FRAC = 0.85
    SEQUEST_FRAC = 0.062
    CAP_ON_BMK_COUNTY_REV = 0.1
    GUAR_REV_FRAC = 0.86

    def __init__(self, plc_base_acres, arcco_base_acres, plc_yield,
                 estimated_county_yield, effective_ref_price,
                 natl_loan_rate, sens_mya_price, benchmark_revenue=None):
        """
        All inputs are scalars, with the exceptions of estimated_county_yield
        and sens_mya_price, which may be either scalars or numpy arrays.
        If benchmark_revenue is not available, a zero value forces
        any ARC-CO payment to zero, though ARC-CO should not be permitted in this case.
        """
        if benchmark_revenue is None:
            benchmark_revenue = 0
        self.plc_base_acres = plc_base_acres
        self.arcco_base_acres = arcco_base_acres
        self.plc_yield = (plc_yield if isinstance(estimated_county_yield, float) else
                          plc_yield * np.ones_like(estimated_county_yield))
        # pre-sensitized county yield
        self.estimated_county_yield = estimated_county_yield
        self.effective_ref_price = effective_ref_price
        self.natl_loan_rate = natl_loan_rate
        # pre-sensitized mya price
        self.sens_mya_price = sens_mya_price
        self.benchmark_revenue = benchmark_revenue

    # Government Payment Totals
    # -------------------------

    def prog_pmt_pre_sequest(self):
        """
        Government Payments Y56:AA56: Sensitized total pre-sequestration payment
        over both programs.
        scalar or 2d array
        """
        result = (round(self.arc_pmt_pre_sequest() + self.plc_pmt_pre_sequest(), 2)
                  if isinstance(self.plc_yield, float) else
                  (self.arc_pmt_pre_sequest() + self.plc_pmt_pre_sequest()).round(2))

        return result

    # PLC
    # ---
    def plc_pmt_pre_sequest(self):
        """
        Government Payments Y23:AA23: Price-sensitized pre-sequestration PLC payment
        scalar or array(np, ny)
        """
        return (self.plc_payment_rate() * self.net_payment_acres_plc() *
                self.plc_yield if isinstance(self.plc_yield, float) else
                np.outer(self.plc_payment_rate() * self.net_payment_acres_plc(),
                         self.plc_yield))

    def plc_payment_rate(self):
        """
        Government Payments Y21:AA21: The price-sensitized PLC payment rate
        scalar or array(np)
        """
        return np.minimum(self.plc_payment_rate1(), self.max_plc_payment_rate())

    def net_payment_acres_plc(self):
        """
        Government Payments Y10:AA10: Net Payment Acres (85 percent of base)
        scalar
        """
        return GovPmt.BASE_TO_NET_PMT_FRAC * self.plc_base_acres

    def plc_payment_rate1(self):
        """
        Government Payments Y19:AA19: Price-sensitized helper for plc_payment rate
        scalar or array(np)
        """
        return np.maximum(self.effective_ref_price - self.effective_price(), 0)

    def max_plc_payment_rate(self):
        """
        Government Payments Y20:AA20: The maximum PLC payment rate
        scalar
        """
        return self.effective_ref_price - self.natl_loan_rate

    def effective_price(self):
        """
        Government Payments Y18:AA18: The price-sensitized effective price
        (because it uses a pre-sensitized mya price).
        scalar or array(np)
        """
        return np.maximum(self.natl_loan_rate, self.sens_mya_price)

    # ARC-CO
    # ------
    def arc_pmt_pre_sequest(self):
        """
        Government Payments Y48:AA48: Sensitized ARC payment pre-sequestration.
        scalar or array(np, ny)
        """
        return self.net_payment_acres_arc() * self.arc_pmt_rate()

    def net_payment_acres_arc(self):
        """
        Government Payments Y10:AA10: Net Payment Acres (85 percent of base)
        scalar
        """
        return GovPmt.BASE_TO_NET_PMT_FRAC * self.arcco_base_acres

    def arc_pmt_rate(self):
        """
        Government Payments Y44:AA44: Sensitized ARC Payment rate.
        scalar or array(np, ny)
        """
        return np.minimum(self.arc_capped_bmk_revenue(), self.revenue_shortfall())

    def arc_capped_bmk_revenue(self):
        """
        Government Payments Y43:AA43: ARC 10 percent cap on Benchmark County Revenue.
        scalar
        """
        return self.benchmark_revenue * GovPmt.CAP_ON_BMK_COUNTY_REV

    def revenue_shortfall(self):
        """
        Government Payments Y42:AA42: Sensitized revenue shortfall.
        scalar or array(np, ny)
        """
        return np.maximum(0, (self.arc_guar_revenue() - self.actual_crop_revenue()))

    def arc_guar_revenue(self):
        """
        Government Payments Y36:AA36: ARC Guarantee Revenue
        (86 percent of Benchmark County revenue)
        scalar
        """
        return (self.benchmark_revenue * GovPmt.GUAR_REV_FRAC)

    def actual_crop_revenue(self):
        """
        Government Payments Y41:AA41: price/yield-sensitized actual
        revenue for the crop.
        scalar or array(np, ny)
        """
        if isinstance(self.sens_mya_price, numbers.Number):
            return (max(self.sens_mya_price, self.natl_loan_rate) *
                    self.estimated_county_yield)
        else:
            return np.outer(np.maximum(self.sens_mya_price, self.natl_loan_rate),
                            self.estimated_county_yield)
