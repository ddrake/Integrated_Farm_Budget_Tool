from ifbt import GovPmt, PLC, ARC_CO, CORN, SOY, WHEAT

# Note: tests may fail if changes are made to the data textfile,
# but changes to program selections are OK.


def test_total_gov_pmt_arco():
    ovr = {'program': {CORN: ARC_CO, SOY: ARC_CO, WHEAT: ARC_CO}, }
    g = GovPmt(2023, overrides=ovr)

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=1)
    assert total_gov_pmt == 0

    total_gov_pmt = g.total_gov_pmt(pf=0.6, yf=1)
    assert total_gov_pmt == 196452

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=0.55)
    assert total_gov_pmt == 375000

    total_gov_pmt = g.total_gov_pmt(pf=.75, yf=.8)
    assert total_gov_pmt == 135021


def test_total_gov_pmt_plc():
    ovr = {'program': {CORN: PLC, SOY: PLC, WHEAT: PLC}, }
    g = GovPmt(2023, overrides=ovr)

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=1)
    assert total_gov_pmt == 0

    total_gov_pmt = g.total_gov_pmt(pf=0.6, yf=1)
    assert total_gov_pmt == 375000

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=0.55)
    assert total_gov_pmt == 0

    total_gov_pmt = g.total_gov_pmt(pf=.75, yf=.8)
    assert total_gov_pmt == 894
