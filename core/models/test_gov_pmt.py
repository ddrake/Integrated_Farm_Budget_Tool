import pytest

from .gov_pmt import GovPmt
from .util import Crop

# Note: tests may fail if changes are made to the data textfile,
# but changes to program selections are OK.


def test_total_gov_pmt_arco():
    ovr = {'farm_base_acres_arc': {Crop.CORN: 4220, Crop.SOY: 4150,
                                   Crop.WHEAT: 317},
           'farm_base_acres_plc': {Crop.CORN: 0, Crop.SOY: 0,
                                   Crop.WHEAT: 0}, }
    g = GovPmt(2023, overrides=ovr)

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=1)
    assert total_gov_pmt == 0

    total_gov_pmt = g.total_gov_pmt(pf=0.6, yf=1)
    assert total_gov_pmt == pytest.approx(225973)

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=0.55)
    assert total_gov_pmt == pytest.approx(375000)

    total_gov_pmt = g.total_gov_pmt(pf=.75, yf=.8)
    assert total_gov_pmt == pytest.approx(171317)


def test_total_gov_pmt_plc():
    ovr = {'farm_base_acres_arc': {Crop.CORN: 0, Crop.SOY: 0,
                                   Crop.WHEAT: 0},
           'farm_base_acres_plc': {Crop.CORN: 4220, Crop.SOY: 4150,
                                   Crop.WHEAT: 317}, }
    g = GovPmt(2023, overrides=ovr)

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=1)
    assert total_gov_pmt == 0

    total_gov_pmt = g.total_gov_pmt(pf=0.6, yf=1)
    assert total_gov_pmt == pytest.approx(375000)

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=0.55)
    assert total_gov_pmt == 0

    total_gov_pmt = g.total_gov_pmt(pf=.75, yf=.8)
    assert total_gov_pmt == pytest.approx(6865)
