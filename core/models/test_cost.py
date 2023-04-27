import pytest

from .cost import Cost

# Note: tests may fail if changes are made to the data textfile

TOL = 1e-7  # relative tolerance


def test_total_cost():
    c = Cost(2023)
    total_cost = c.total_cost()
    assert total_cost == pytest.approx(6843967, TOL)
