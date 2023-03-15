from ifbt import Revenue

# Note: tests may fail if changes are made to the data textfile,
# but changes to pricing for uncontracted grain and revenue_wheat are OK.


def test_total_revenue():
    ovr = {'fall_futures_price_corn': 5.8925,
           'fall_futures_price_soy' : 13.6625,
           'est_basis_corn': 0.35,
           'est_basis_soy': 0.35,
           'revenue_wheat': 300341, }

    rev = Revenue(2023, overrides=ovr)
    total_revenue = rev.total_revenue()
    assert total_revenue == 9905774

    total_revenue = rev.total_revenue(yf=0.4)
    assert total_revenue == 4204997

    total_revenue = rev.total_revenue(pf=0.6)
    assert total_revenue == 9116827

    total_revenue = rev.total_revenue(pf=.9, yf=.9)
    assert total_revenue == 8851353
