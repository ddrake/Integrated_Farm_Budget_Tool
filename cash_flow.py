"""
Module cash_flow

Contains a single class, CashFlow, which loads its data from a text file
for a given crop year when an instance is created.  Its main function
is to return total estimated cost for the farm for the given crop year
corresponding to arbitrary sensitivity factors for price and yield.
"""
from analysis import Analysis


class CashFlow(Analysis):
    """
    Computes net cash flow for the farm crop year
    corresponding to arbitrary sensitivity factors for price and yield.

    Sample usage in a python or ipython console:
      from cash_flow import CashFlow
      c = CashFlow(2023)
      print(c.total_cash_flow()                 # pf and yf default to 1
      print(c.total_cash_flow(.9, 1.1)          # specifies both price and yield factors
      print(c.total_cash_flow(yield_factor=1.2) # uses default for pf
    """
    DATA_FILES = 'farm_data cash_flow_data'

    def __init__(self, *args, **kwargs):
        super(CashFlow, self).__init__(*args, **kwargs)
