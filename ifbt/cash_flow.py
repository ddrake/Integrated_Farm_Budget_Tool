"""
Module cash_flow

Contains a single class, CashFlow, which loads some data for a given crop year
when an instance is created, and uses results from the Cost and Revenue modules
"""
from .analysis import Analysis
from .cost import Cost
from .revenue import Revenue
from .util import SEASON_CROPS


class CashFlow(Analysis):
    """
    Computes net cash flow for the farm crop year
    corresponding to arbitrary sensitivity factors for price and yield.

    Sample usage in a python or ipython console:
      from ifbt import CashFlow, Premium
      c = CashFlow(2023, prem=Premium())
      c.total_cash_flow()                 # pf and yf default to 1
      c.total_cash_flow(pf=.9, yf=1.1)    # specifies both price and yield factors
      c.total_cash_flow(yf=1.2)           # uses default for pf
    """
    DATA_FILES = 'farm_data'

    def __init__(self, *args, crop_ins_overrides=None,
                 gov_pmt_overrides=None, **kwargs):
        """
        Initialize base class, then set attributes to instances of the four models.
        """
        super().__init__(*args, **kwargs)
        if 'prem' not in kwargs:
            raise ValueError('CashFlow constructor needs a Premium instance')
        self.cost = Cost(self.crop_year, prem=kwargs['prem'])
        self.revenue = Revenue(self.crop_year, prem=kwargs['prem'])

    def cash_flow_crop(self, crop, pf=1, yf=1):
        return (self.revenue.gross_revenue_crop(crop, pf, yf) -
                self.cost.total_cost_crop(crop))

    def cash_flow_non_crop(self, pf=1, yf=1):
        return (self.revenue.gross_revenue_non_crop(pf, yf) -
                self.cost.total_nongrain_cost())

    def total_crop_cash_flow(self, pf=1, yf=1):
        return sum((self.cash_flow_crop(crop, pf, yf) for crop in SEASON_CROPS))

    def total_cash_flow(self, pf=1, yf=1):
        return (self.total_crop_cash_flow(pf, yf) +
                self.cash_flow_non_crop(pf, yf))
