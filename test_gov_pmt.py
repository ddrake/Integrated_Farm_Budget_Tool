from gov_pmt import GovPmt

# Note: tests may fail if changes are made to the data textfile,
# but changes to program selections are OK.


def test_total_gov_pmt_arco():
    g = GovPmt(2023)

    g.program_corn = GovPmt.ARC_CO
    g.program_soy = GovPmt.ARC_CO
    g.program_wheat = GovPmt.ARC_CO

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=1)
    assert total_gov_pmt == 0

    total_gov_pmt = g.total_gov_pmt(pf=0.6, yf=1)
    assert total_gov_pmt == 196452

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=0.55)
    assert total_gov_pmt == 375000

    total_gov_pmt = g.total_gov_pmt(pf=.75, yf=.8)
    assert total_gov_pmt == 135021


def test_total_gov_pmt_plc():
    g = GovPmt(2023)

    g.program_corn = GovPmt.PLC
    g.program_soy = GovPmt.PLC
    g.program_wheat = GovPmt.PLC

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=1)
    assert total_gov_pmt == 0

    total_gov_pmt = g.total_gov_pmt(pf=0.6, yf=1)
    assert total_gov_pmt == 375000

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=0.55)
    assert total_gov_pmt == 0

    total_gov_pmt = g.total_gov_pmt(pf=.75, yf=.8)
    assert total_gov_pmt == 894
