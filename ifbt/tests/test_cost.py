import pytest

from ifbt import Cost, Premium

# Note: tests may fail if changes are made to the data textfile

TOL = 1e-7  # relative tolerance
prem = Premium()


def test_total_cost():
    c = Cost(2023, prem=prem)
    total_cost = c.total_cost()
    assert total_cost == pytest.approx(6840894, TOL)
