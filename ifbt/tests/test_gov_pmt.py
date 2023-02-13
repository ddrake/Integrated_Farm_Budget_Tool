from ifbt import GovPmt, PLC, ARC_CO

# Note: tests may fail if changes are made to the data textfile,
# but changes to program selections are OK.


def test_total_gov_pmt_arco():
    ovr = {'program_corn': ARC_CO, 'program_soy': ARC_CO, 'program_wheat': ARC_CO}
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
    ovr = {'program_corn': PLC, 'program_soy': PLC, 'program_wheat': PLC}
    g = GovPmt(2023, overrides=ovr)

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=1)
    assert total_gov_pmt == 0

    total_gov_pmt = g.total_gov_pmt(pf=0.6, yf=1)
    assert total_gov_pmt == 375000

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=0.55)
    assert total_gov_pmt == 0

    total_gov_pmt = g.total_gov_pmt(pf=.75, yf=.8)
    assert total_gov_pmt == 894
