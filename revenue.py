"""
Module revenue

Contains a single class, Revenue, which loads its data from a text file
for a given crop year when an instance is created.  Its main function
is to return total estimated revenue for the farm for the given crop year
corresponding to arbitrary sensitivity factors for price and yield.
"""
from analysis import Analysis, crop_in


class Revenue(Analysis):
    """
    Computes total estimated revenue for the farm crop year
    corresponding to arbitrary sensitivity factors for price and yield.

    Sample usage in a python or ipython console:
      from revenue import Revenue
      r = Revenue(2023)
      print(r.total_revenue()        # pf and yf default to 1
      print(r.total_revenue(.9, 1.1) # specifies both price and yield factors
      print(r.total_revenue(yf=1.2)  # uses default for pf
    """
    DATA_FILES = 'farm_data revenue_data'

    def __init__(self, *args, **kwargs):
        super(Revenue, self).__init__(*args, **kwargs)

    @crop_in('corn', 'soy')
    def projected_shrink_bu_crop(self, crop, yf=1):
        """
        E13, F13
        """
        return (self.projected_bu_crop(crop, yf) *
                self.c('est_shrink', crop)/100.)

    @crop_in('corn', 'soy')
    def deliverable_bu_crop(self, crop, yf=1):
        """
        E14, F14
        """
        return (self.projected_bu_crop(crop, yf) -
                self.projected_shrink_bu_crop(crop, yf))

    @crop_in('corn', 'soy')
    def sold_under_contract_crop(self, crop):
        """
        E18, F18:
        Gross revenue from contracted corn or soy assuming contracts can be filled
        rounded to whole dollars
        """
        return round(
            self.c('contract_bu', crop) *
            self.c('avg_contract_price', crop))

    @crop_in('corn', 'soy')
    def unsold_bushels_crop(self, crop, yf=1):
        """
        E19, F19: Unsold (or oversold) bushels
        """
        return (self.deliverable_bu_crop(crop, yf) -
                self.c('contract_bu', crop))

    @crop_in('corn', 'soy')
    def est_price_crop_uncontracted(self, crop, pf=1):
        """
        E20, F20: Harvest price plus basis
        """
        return (self.c('fall_futures_price', crop) * pf +
                self.c('est_basis', crop))

    @crop_in('corn', 'soy')
    def revenue_uncontracted_crop(self, crop, pf=1, yf=1):
        """
        E21, F21:
        Estimated revenue (buyout) of uncontracted (oversold) corn or soy
        for specified pf and yf rounded to whole dollars
        """
        return round(
            self.unsold_bushels_crop(crop, yf) *
            self.est_price_crop_uncontracted(crop, pf))

    @crop_in('corn', 'soy')
    def tot_revenue_before_deducts_crop(self, crop, pf=1, yf=1):
        """
        E22, F22: Total revenue before deducts/penalties
        """
        return (self.sold_under_contract_crop(crop) +
                self.revenue_uncontracted_crop(crop, pf, yf))

    @crop_in('corn', 'soy')
    def est_deducts_crop(self, crop, pf=1, yf=1):
        """
        E23, F23:
        Estimated deducts/penalties in dollars
        """
        return ((self.sold_under_contract_crop(crop) +
                 abs(self.revenue_uncontracted_crop(crop, pf, yf))) *
                self.c('est_deduct', crop)/100)

    @crop_in('corn', 'soy')
    def total_revenue_crop(self, crop, pf=1, yf=1):
        """
        E24, F25, F26
        Total revenue attained by each crop
        Note: wheat is considered a component of soy for revenue and cost
        """
        return ((self.revenue_wheat if crop == 'soy' else 0) +
                self.tot_revenue_before_deducts_crop(crop, pf, yf) -
                self.est_deducts_crop(crop, pf, yf))

    def total_revenue_grain(self, pf=1, yf=1):
        """
        G24 Total revenue over all crops
        """
        return round(sum(
            [self.total_revenue_crop(crop, pf, yf)
             for crop in ['corn', 'soy']]))

    @crop_in('corn', 'soy')
    def avg_realized_price_per_bu(self, crop, pf=1, yf=1):
        """
        E25, F25
        """
        return (self.total_revenue_crop(crop, pf, yf) /
                self.projected_bu_crop(crop, yf))

    @crop_in('corn', 'soy')
    def revenue_other_crop(self, crop):
        """
        E35, F35: Total of other revenue by crop *excluding* govt program
        """
        return (self.c('ppp_loan_forgive', crop) +
                self.c('mfp_cfap', crop) +
                self.c('rental_revenue', crop) +
                self.c('other_revenue', crop))

    def total_revenue_other(self):
        """
        G35: Total of other revenue *excluding* government program payments
        """
        return sum([self.revenue_other_crop(crop)
                    for crop in ['corn', 'soy']])

    def total_revenue(self, pf=1, yf=1):
        """
        Total revenue reflecting current estimates and price/yield factors
        """
        return self.total_revenue_grain(pf, yf) + self.total_revenue_other()
