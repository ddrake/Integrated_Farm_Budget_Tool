from ifbt import CashFlow, Premiums

# Note: tests may fail if changes are made to the data textfile,
# but changes to pricing for uncontracted grain and cash_flow_wheat are OK.

p = Premiums()


def test_total_cash_flow():
    cf = CashFlow(2023, prem=p)
    assert cf.total_cash_flow(pf=1, yf=1) == 3018006
    assert cf.total_cash_flow(pf=1.3, yf=1) == 3613538
    assert cf.total_cash_flow(pf=1, yf=1.3) == 5521350
    assert cf.total_cash_flow(pf=.7, yf=.75) == 4137857
    assert cf.total_cash_flow(pf=.6, yf=.75) == 5213393
