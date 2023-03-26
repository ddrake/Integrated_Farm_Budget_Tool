from ifbt import CashFlow, Premium

# Note: tests may fail if changes are made to the data textfile,
# but changes to pricing for uncontracted grain and cash_flow_wheat are OK.

p = Premium()


def test_total_cash_flow():
    cf = CashFlow(2023, prem=p)
    assert cf.total_cash_flow(pf=1, yf=1) == 3076177
    assert cf.total_cash_flow(pf=1.3, yf=1) == 3671709
    assert cf.total_cash_flow(pf=1, yf=1.3) == 5579521
    assert cf.total_cash_flow(pf=.7, yf=.75) == 4196027
    assert cf.total_cash_flow(pf=.6, yf=.75) == 5271564
