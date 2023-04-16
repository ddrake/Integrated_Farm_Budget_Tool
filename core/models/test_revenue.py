import pytest

from .revenue import Revenue
from .premium import Premium

# Note: tests may fail if changes are made to the data textfile,
# but changes to pricing for uncontracted grain and revenue_wheat are OK.

prem = Premium()


def test_total_revenue():
    ovr = {'fall_futures_price_corn': 5.8925,
           'fall_futures_price_soy' : 13.6625,
           'est_basis_corn': 0.35,
           'est_basis_soy': 0.35,
           'revenue_wheat': 300341, }

    rev = Revenue(2023, overrides=ovr, prem=prem)
    gross_revenue = rev.gross_revenue()
    assert gross_revenue == pytest.approx(9977249)

    gross_revenue = rev.gross_revenue(yf=0.4)
    assert gross_revenue == pytest.approx(8379167)

    gross_revenue = rev.gross_revenue(pf=0.6)
    assert gross_revenue == pytest.approx(11844769)

    gross_revenue = rev.gross_revenue(pf=.9, yf=.9)
    assert gross_revenue == pytest.approx(9270065)
