"""
Module revenue

Contains a single class, Revenue, which loads its data for a given crop year
when an instance is created.
"""
from analysis import Analysis
from crop_ins import CropIns
from gov_pmt import GovPmt
from util import Crop, crop_in, BASE_CROPS, SEASON_CROPS


class Revenue(Analysis):
    """
    Computes total estimated revenue for the farm crop year
    corresponding to arbitrary sensitivity factors for price and yield.

    Sample usage in a python or ipython console:
      from ifbt import Revenue, Premium
      r = Revenue(2023, prem=Premium())
      r.total_revenue()                # pf and yf default to 1
      r.total_revenue(pf=.9, yf=1.1)   # specifies both price and yield factors
      r.total_revenue(yf=1.2)          # uses default for pf
    """
    DATA_FILES = 'farm_data revenue_data'

    def __init__(self, *args, **kwargs):
        super(Revenue, self).__init__(*args, **kwargs)
        if 'prem' not in kwargs:
            raise ValueError('Revenue constructor needs a Premium instance')
        self.gov_pmt = GovPmt(self.crop_year)
        self.crop_ins = CropIns(self.crop_year, prem=kwargs['prem'])

    @crop_in(*BASE_CROPS)
    def price_crop_contracted(self, crop):
        return self.avg_contract_price[crop] + self.avg_contract_basis[crop]

    @crop_in(*BASE_CROPS)
    def est_price_crop_uncontracted(self, crop, pf=1):
        """
        Price-sensitized harvest price plus basis
        """
        return (self.fall_futures_price[self.base_crop(crop)] * pf +
                self.est_basis[crop])

    @crop_in(*SEASON_CROPS)
    def deliverable_bu_crop(self, crop, yf=1):
        """
        Yield-sensitized deliverable bushels for the season crop.
        """
        return self.projected_bu_scrop(crop, yf)

    @crop_in(*SEASON_CROPS)
    def apportion_contract_bushels(self, crop, yf=1):
        return (self.contract_bu[crop] if crop in (Crop.CORN, Crop.WHEAT) else
                self.contract_bu[Crop.SOY] *
                self.projected_bu_scrop(crop, yf) / self.projected_bu_soy(yf))

    @crop_in(*SEASON_CROPS)
    def sold_under_contract_crop(self, crop):
        """
        Gross revenue from contracted crop.
        """
        return (self.apportion_contract_bushels(crop) *
                self.price_crop_contracted(self.base_crop(crop)))

    def total_contracted_bushels(self):
        return sum((self.contract_bu[crop] for crop in BASE_CROPS))

    @crop_in(*SEASON_CROPS)
    def unsold_bushels_crop(self, crop, yf=1):
        """
        Yield-sensitized unsold (or oversold) bushels for the crop
        """
        return (self.deliverable_bu_crop(crop, yf) -
                self.apportion_contract_bushels(crop, yf))

    def total_uncontracted_bushels(self, yf=1):
        return sum((self.unsold_bushels_crop(yf)))

    @crop_in(*SEASON_CROPS)
    def revenue_uncontracted_crop(self, crop, pf=1, yf=1):
        """
        Sensitized estimated revenue (buyout) of uncontracted
        (or oversold) corn or soy rounded to whole dollars
        """
        return (
            self.unsold_bushels_crop(crop, yf) *
            self.est_price_crop_uncontracted(self.base_crop(crop), pf))

    @crop_in(*SEASON_CROPS)
    def total_revenue_crop(self, crop, pf=1, yf=1):
        return (self.sold_under_contract_crop(crop) +
                self.revenue_uncontracted_crop(crop, pf, yf))

    def total_crop_revenue(self, pf=1, yf=1):
        return sum(
            [self.total_revenue_crop(crop, pf, yf)
             for crop in SEASON_CROPS])

    @crop_in(*SEASON_CROPS)
    def avg_realized_price_per_bu(self, crop, pf=1, yf=1):
        return (self.total_revenue_crop(crop, pf, yf) /
                self.projected_bu_scrop(crop, yf))

    @crop_in(*SEASON_CROPS)
    def apportion_gov_pmt(self, crop, pf=1, yf=1):
        return (self.gov_pmt.total_gov_pmt_crop(crop, pf, yf)
                if crop in (Crop.CORN, Crop.WHEAT) else
                self.gov_pmt.total_gov_pmt_crop(Crop.SOY, pf, yf) *
                self.acres_crop(crop)/self.acres_crop(Crop.SOY))

    @crop_in(*SEASON_CROPS)
    def revenue_other_crop(self, crop, pf=1, yf=1):
        return (self.apportion_gov_pmt(crop, pf, yf) +
                self.other_gov_pmts[crop] +
                self.crop_ins.total_indemnity_crop(crop, pf, yf) +
                self.other_revenue[crop])

    @crop_in(*SEASON_CROPS)
    def gross_revenue_crop(self, crop, pf=1, yf=1):
        return (self.total_revenue_crop(crop, pf, yf) +
                self.revenue_other_crop(crop, pf, yf))

    def gross_crop_revenue(self, pf=1, yf=1):
        return sum((self.gross_revenue_crop(crop, pf, yf) for crop in SEASON_CROPS))

    def gross_revenue_non_crop(self, pf=1, yf=1):
        return self.other_noncrop_revenue

    def total_revenue_other(self, pf=1, yf=1):
        return sum([self.revenue_other_crop(crop, pf, yf)
                    for crop in SEASON_CROPS])

    def gross_revenue(self, pf=1, yf=1):
        return self.gross_crop_revenue(pf, yf) + self.gross_revenue_non_crop()
