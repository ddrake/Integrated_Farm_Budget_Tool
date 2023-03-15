"""
Module revenue

Contains a single class, Revenue, which loads its data from text files
for a given crop year when an instance is created.  Its main function
is to return total estimated revenue for the farm for the given crop year
corresponding to arbitrary sensitivity factors for price and yield.
"""
from .analysis import Analysis
from .util import crop_in, Crop


class Revenue(Analysis):
    """
    Computes total estimated revenue for the farm crop year
    corresponding to arbitrary sensitivity factors for price and yield.

    Sample usage in a python or ipython console:
      from ifbt import Revenue
      r = Revenue(2023)
      r.total_revenue()                # pf and yf default to 1
      r.total_revenue(pf=.9, yf=1.1)   # specifies both price and yield factors
      r.total_revenue(yf=1.2)          # uses default for pf
    """
    DATA_FILES = 'farm_data revenue_data'

    def __init__(self, *args, **kwargs):
        super(Revenue, self).__init__(*args, **kwargs)

    @crop_in(Crop.CORN, Crop.SOY)
    def projected_shrink_bu_crop(self, crop, yf=1):
        """
        GVBudget E13, F13: Yield-sensitized projected shrink for the crop.
        """
        return (self.projected_bu_crop(crop, yf) *
                self.est_shrink[crop]/100.)

    @crop_in(Crop.CORN, Crop.SOY)
    def deliverable_bu_crop(self, crop, yf=1):
        """
        GVBudget E14, F14: Yield-sensitized deliverable bushels for the crop.
        """
        return (self.projected_bu_crop(crop, yf) -
                self.projected_shrink_bu_crop(crop, yf))

    @crop_in(Crop.CORN, Crop.SOY)
    def sold_under_contract_crop(self, crop):
        """
        GVBudget E18, F18: Gross revenue from contracted crop assuming contracts
        can be filled.  Rounded to whole dollars.
        """
        return round(
            self.contract_bu[crop] *
            self.avg_contract_price[crop])

    @crop_in(Crop.CORN, Crop.SOY)
    def unsold_bushels_crop(self, crop, yf=1):
        """
        GVBudget E19, F19: Yield-sensitized unsold (or oversold) bushels
        for the crop
        """
        return (self.deliverable_bu_crop(crop, yf) -
                self.contract_bu[crop])

    @crop_in(Crop.CORN, Crop.SOY)
    def est_price_crop_uncontracted(self, crop, pf=1):
        """
        GVBudget E20, F20: Price-sensitized harvest price plus basis
        """
        return (self.fall_futures_price[crop] * pf +
                self.est_basis[crop])

    @crop_in(Crop.CORN, Crop.SOY)
    def revenue_uncontracted_crop(self, crop, pf=1, yf=1):
        """
        GVBudget E21, F21: Sensitized estimated revenue (buyout) of uncontracted
        (or oversold) corn or soy rounded to whole dollars
        """
        return round(
            self.unsold_bushels_crop(crop, yf) *
            self.est_price_crop_uncontracted(crop, pf))

    @crop_in(Crop.CORN, Crop.SOY)
    def total_revenue_before_deducts_crop(self, crop, pf=1, yf=1):
        """
        GVBudget E22, F22: Sensitized total revenue before deducts/penalties.
        """
        return (self.sold_under_contract_crop(crop) +
                self.revenue_uncontracted_crop(crop, pf, yf))

    @crop_in(Crop.CORN, Crop.SOY)
    def est_deducts_crop(self, crop, pf=1, yf=1):
        """
        GVBudget E23, F23: Sensitized estimated deducts/penalties in dollars.
        """
        return ((self.sold_under_contract_crop(crop) +
                 abs(self.revenue_uncontracted_crop(crop, pf, yf))) *
                self.est_deduct[crop]/100)

    @crop_in(Crop.CORN, Crop.SOY)
    def total_revenue_crop(self, crop, pf=1, yf=1):
        """
        GVBudget E24, F25, F26: Sensitized total revenue attained by each crop.
        Note: wheat is considered a component of soy for revenue and cost
        """
        return ((self.wheat_revenue if crop == Crop.SOY else 0) +
                self.total_revenue_before_deducts_crop(crop, pf, yf) -
                self.est_deducts_crop(crop, pf, yf))

    def total_revenue_grain(self, pf=1, yf=1):
        """
        GVBudget G24: Sensitized total revenue over all crops.
        """
        return round(sum(
            [self.total_revenue_crop(crop, pf, yf)
             for crop in [Crop.CORN, Crop.SOY]]))

    @crop_in(Crop.CORN, Crop.SOY)
    def avg_realized_price_per_bu(self, crop, pf=1, yf=1):
        """
        GVBudget E25, F25: Sensitized average realized price per bushel for
        the crop.
        """
        return (self.total_revenue_crop(crop, pf, yf) /
                self.projected_bu_crop(crop, yf))

    @crop_in(Crop.CORN, Crop.SOY)
    def revenue_other_crop(self, crop):
        """
        GVBudget E35, F35: Total of other revenue by crop *excluding* government
        program payments for the crop.
        """
        return (self.ppp_loan_forgive[crop] +
                self.mfp_cfap[crop] +
                self.rental_revenue[crop] +
                self.other_revenue[crop])

    def total_revenue_other(self):
        """
        GVBudget G35: Total of other revenue *excluding* government program payments
        """
        return sum([self.revenue_other_crop(crop)
                    for crop in [Crop.CORN, Crop.SOY]])

    def total_revenue(self, pf=1, yf=1):
        """
        GVBudget G37: Sensitized total revenue *excluding* government program
        payments.
        """
        return self.total_revenue_grain(pf, yf) + self.total_revenue_other()
