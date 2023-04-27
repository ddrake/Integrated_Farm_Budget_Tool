import pytest

from cash_flow import CashFlow

# Note: tests may fail if changes are made to the data textfile,
# but changes to pricing for uncontracted grain and cash_flow_wheat are OK.

TOL = 1


def test_total_cash_flow():
    cf = CashFlow(2023)
    assert cf.total_cash_flow(pf=1, yf=1) == pytest.approx(3076177, TOL)
    assert cf.total_cash_flow(pf=1.3, yf=1) == pytest.approx(3671709, TOL)
    assert cf.total_cash_flow(pf=1, yf=1.3) == pytest.approx(5579521, TOL)
    assert cf.total_cash_flow(pf=.7, yf=.75) == pytest.approx(4196027, TOL)
    assert cf.total_cash_flow(pf=.6, yf=.75) == pytest.approx(5271564, TOL)
