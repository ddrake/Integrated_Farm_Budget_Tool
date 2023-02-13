from ifbt import Cost

# Note: tests may fail if changes are made to the data textfile


def test_total_cost():
    c = Cost(2023)
    total_cost = c.total_cost()
    assert total_cost == 6660923

    total_cost = c.total_cost(yf=0.6)
    assert total_cost == 6239074

    total_cost = c.total_cost(yf=0.9)
    assert total_cost == 6555460
