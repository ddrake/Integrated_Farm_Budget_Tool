from ifbt import CashFlow

# Note: tests may fail if changes are made to the data textfile,
# but changes to pricing for uncontracted grain and cash_flow_wheat are OK.


def test_total_cash_flow():
    cf = CashFlow(2023)
    assert cf.total_cash_flow(pf=1, yf=1) == 2961188
    assert cf.total_cash_flow(pf=1.3, yf=1) == 3552899
    assert cf.total_cash_flow(pf=1, yf=1.3) == 5477269
    assert cf.total_cash_flow(pf=.7, yf=.75) == 3849042
    assert cf.total_cash_flow(pf=.6, yf=.75) == 4931582
