"""
Module cash_flow

Contains a single class, CashFlow, which loads some data from a text file
for a given crop year when an instance is created, and uses results from other modules
Its main function is to return total estimated cost for the farm for the given crop year
corresponding to arbitrary sensitivity factors for price and yield.
"""
from .analysis import Analysis
from .cost import Cost
from .crop_ins import CropIns
from .gov_pmt import GovPmt
from .revenue import Revenue


class CashFlow(Analysis):
    """
    Computes net cash flow for the farm crop year
    corresponding to arbitrary sensitivity factors for price and yield.

    Sample usage in a python or ipython console:
      from ifbt import CashFlow
      c = CashFlow(2023)
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
            raise ValueError('CashFlow constructor needs a Premiums instance')
        self.cost = Cost(self.crop_year)
        self.crop_ins = CropIns(self.crop_year, overrides=crop_ins_overrides,
                                prem=kwargs['prem'])
        self.gov_pmt = GovPmt(self.crop_year, overrides=gov_pmt_overrides)
        self.revenue = Revenue(self.crop_year)

    def total_revenue(self, pf=1, yf=1):
        """
        GVBudget G37: Total revenue including government payments.
        """
        return round(self.revenue.total_revenue_grain(pf, yf) +
                     self.revenue.total_revenue_other() +
                     self.gov_pmt.total_gov_pmt(pf, yf))

    def total_non_land_operating_costs(self, pf=1, yf=1):
        """
        GVBudget G41: Total non-land operating costs.  Net crop insurance
        indemnity is subtracted to give net crop insurance cost.
        """
        return round(self.cost.total_variable_cost(yf) -
                     self.crop_ins.total_net_crop_ins_indemnity(pf, yf) +
                     self.cost.total_overhead(yf))

    def cash_flow_before_land_costs(self, pf=1, yf=1):
        """
        GVBudget G43: Cash flow before land costs.
        """
        return (self.total_revenue(pf, yf) -
                self.total_non_land_operating_costs(pf, yf))

    def total_cash_flow(self, pf=1, yf=1):
        """
        GVBudget G52: Total net cash flow, including land expenses.
        """
        return round(self.cash_flow_before_land_costs(pf, yf) -
                     self.cost.total_land_expenses_over_crops(yf))
