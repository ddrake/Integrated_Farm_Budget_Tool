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


class GovPmt():
    """
    Computes the total pre-sequestration payment (ARC-CO + PLC) for a crop
    corresponding to arbitrary sensitivity factors for price and yield.
    """

    BASE_TO_NET_PMT_FRAC = 0.85
    SEQUEST_FRAC = 0.062
    CAP_ON_BMK_COUNTY_REV = 0.1
    GUAR_REV_FRAC = 0.86

    def __init__(self, plc_base_acres=4220, arcco_base_acres=0, plc_yield=160,
                 estimated_county_yield=190, effective_ref_price=3.70,
                 natl_loan_rate=2.20, sens_mya_price=4.80, benchmark_revenue=801.09):

        self.plc_base_acres = plc_base_acres
        self.arcco_base_acres = arcco_base_acres
        self.plc_yield = plc_yield
        self.estimated_county_yield = estimated_county_yield
        self.effective_ref_price = effective_ref_price
        self.natl_loan_rate = natl_loan_rate
        self.sens_mya_price = sens_mya_price
        self.benchmark_revenue = benchmark_revenue

    # Government Payment Totals
    # -------------------------

    def prog_pmt_pre_sequest(self, yf=1):
        """
        Government Payments Y56:AA56: Sensitized total pre-sequestration payment
        over both programs.
        """
        result = round(self.arc_pmt_pre_sequest(yf) +
                       self.plc_pmt_pre_sequest(), 2)
        return result

    # PLC
    # ---
    def plc_pmt_pre_sequest(self):
        """
        Government Payments Y23:AA23: Price-sensitized pre-sequestration PLC payment
        """
        return (self.plc_payment_rate() * self.net_payment_acres_plc() *
                self.plc_yield)

    def plc_payment_rate(self):
        """
        Government Payments Y21:AA21: The price-sensitized PLC payment rate
        """
        return min(self.plc_payment_rate1(),
                   self.max_plc_payment_rate())

    def net_payment_acres_plc(self):
        """
        Government Payments Y10:AA10: Net Payment Acres (85 percent of base)
        """
        return GovPmt.BASE_TO_NET_PMT_FRAC * self.plc_base_acres

    def plc_payment_rate1(self):
        """
        Government Payments Y19:AA19: Price-sensitized helper for plc_payment rate
        """
        return max(self.effective_ref_price - self.effective_price(), 0)

    def max_plc_payment_rate(self):
        """
        Government Payments Y20:AA20: The maximum PLC payment rate
        """
        return self.effective_ref_price - self.natl_loan_rate

    def effective_price(self):
        """
        Government Payments Y18:AA18: The price-sensitized effective price
        (because it uses a pre-sensitized mya price).
        """
        return max(self.natl_loan_rate,
                   self.sens_mya_price)

    # ARC-CO
    # ------
    def arc_pmt_pre_sequest(self, yf=1):
        """
        Government Payments Y48:AA48: Sensitized ARC payment pre-sequestration.
        """
        return self.net_payment_acres_arc() * self.arc_pmt_rate(yf)

    def net_payment_acres_arc(self):
        """
        Government Payments Y10:AA10: Net Payment Acres (85 percent of base)
        """
        return GovPmt.BASE_TO_NET_PMT_FRAC * self.arcco_base_acres

    def arc_pmt_rate(self, yf=1):
        """
        Government Payments Y44:AA44: Sensitized ARC Payment rate.
        """
        return min(self.arc_capped_bmk_revenue(),
                   self.revenue_shortfall(yf))

    def arc_capped_bmk_revenue(self):
        """
        Government Payments Y43:AA43: ARC 10 percent cap on Benchmark County Revenue.
        """
        return (self.arc_bmk_county_revenue() *
                GovPmt.CAP_ON_BMK_COUNTY_REV)

    def revenue_shortfall(self, yf=1):
        """
        Government Payments Y42:AA42: Sensitized revenue shortfall.
        """
        return max(0, (self.arc_guar_revenue() -
                       self.actual_crop_revenue(yf)))

    def arc_bmk_county_revenue(self):
        """
        Government Payments Y35:AA35: ARC Benchmark County Revenue for the crop.
        """
        return self.benchmark_revenue

    def arc_guar_revenue(self):
        """
        Government Payments Y36:AA36: ARC Guarantee Revenue
        (86 percent of Benchmark County revenue)
        """
        return (self.arc_bmk_county_revenue() * GovPmt.GUAR_REV_FRAC)

    def actual_crop_revenue(self, yf=1):
        """
        Government Payments Y41:AA41: price/yield-sensitized actual
        revenue for the crop.
        """
        return (max(self.sens_mya_price,
                    self.natl_loan_rate) *
                self.arc_county_rma_yield(yf))

    def arc_county_rma_yield(self, yf=1):
        """
        Government Payments Y40:AA40 -> AR25:AT25: Yield-sensitized County
        actual/est yield (RMA) for the crop.
        Note: this is NOT the same as the county_rma_yield in the base class
        """
        return self.estimated_county_yield * yf
