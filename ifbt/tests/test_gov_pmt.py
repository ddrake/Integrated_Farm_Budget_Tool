from ifbt import GovPmt, Prog, Crop

# Note: tests may fail if changes are made to the data textfile,
# but changes to program selections are OK.


def test_total_gov_pmt_arco():
    ovr = {'program': {Crop.CORN: Prog.ARC_CO, Crop.SOY: Prog.ARC_CO,
                       Crop.WHEAT: Prog.ARC_CO}, }
    g = GovPmt(2023, overrides=ovr)

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=1)
    assert total_gov_pmt == 0

    total_gov_pmt = g.total_gov_pmt(pf=0.6, yf=1)
    assert total_gov_pmt == 198995

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=0.55)
    assert total_gov_pmt == 375000

    total_gov_pmt = g.total_gov_pmt(pf=.75, yf=.8)
    assert total_gov_pmt == 137564


def test_total_gov_pmt_plc():
    ovr = {'program': {Crop.CORN: Prog.PLC, Crop.SOY: Prog.PLC,
                       Crop.WHEAT: Prog.PLC}, }
    g = GovPmt(2023, overrides=ovr)

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=1)
    assert total_gov_pmt == 0

    total_gov_pmt = g.total_gov_pmt(pf=0.6, yf=1)
    assert total_gov_pmt == 375000

    total_gov_pmt = g.total_gov_pmt(pf=1, yf=0.55)
    assert total_gov_pmt == 0

    total_gov_pmt = g.total_gov_pmt(pf=.75, yf=.8)
    assert total_gov_pmt == 894
