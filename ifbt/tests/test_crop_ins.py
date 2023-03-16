import pytest

from ifbt import CropIns, Premiums, Crop, Ins, Unit, Prot, Lvl

# Note: tests may fail if changes are made to the data files
# 2023_crop_ins_indemnity.txt or 2023_crop_ins_premiums.txt
# However, changes to the settings in 2023_crop_ins_data.txt should
# not cause any tests to fail because tests will provide overrides

TOL = .01

p = Premiums()


def test_total_crop_ins():
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    ovr = {'insure': {Crop.CORN: Ins.YES}, 'unit': {Crop.CORN: Unit.ENT},
           'protection': {Crop.CORN: Prot.RP},
           'level': {Crop.CORN: 75}, 'sco_level': {Crop.CORN: Lvl.DFLT},
           'eco_level': {Crop.CORN: Lvl.NONE},
           'selected_pmt_factor': {Crop.CORN: 1}}

    c = CropIns(2023, overrides=ovr, prem=p)

    crop = Crop.CORN
    assert c.crop_ins_premium_crop(crop) == pytest.approx(72847.62, TOL)

    assert (c.indemnity[Crop.CORN].harvest_indemnity_pmt(pf=.7, yf=.75)
            == pytest.approx(1126643.935, TOL))

    # there should be an SCO indemnity
    assert (c.sco[Crop.CORN].harvest_indemnity_pmt(pf=.7, yf=.75)
            == pytest.approx(593544.579, TOL))

    # there should not be an ECO indemnity for CORN
    assert not hasattr(c, 'eco') or Crop.CORN not in c.eco


def test_premiums_and_revenue_are_zero_for_a_crop_without_insurance():
    # DON'T insure corn, but set an enterprise unit, rp protection at a 75% level
    # with no optional coverage.
    ovr = {'insure': {Crop.CORN: Ins.NO}, 'unit': {Crop.CORN: Unit.ENT},
           'protection': {Crop.CORN: Prot.RP}, 'level': {Crop.CORN: 75},
           'sco_level': {Crop.CORN: Lvl.NONE}, 'eco_level': {Crop.CORN: Lvl.NONE},
           'selected_pmt_factor': {Crop.CORN: 1}, }

    c = CropIns(2023, overrides=ovr, prem=p)
    crop = Crop.CORN
    assert c.crop_ins_premium_crop(crop) == 0
    assert c.total_indemnity_crop(crop, pf=.7, yf=.75) == 0
    assert not hasattr(c, 'indemnity') or Crop.CORN not in c.indemnity


def test_no_indemnity_attribute_is_added_without_base_insurance():
    # DON'T insure corn, but set an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, and no enhanced coverage
    ovr = {'insure': {Crop.CORN: Ins.NO}, 'unit': {Crop.CORN: Unit.ENT},
           'protection': {Crop.CORN: Prot.RP}, 'level': {Crop.CORN: 75},
           'sco_level': {Crop.CORN: Lvl.DFLT}, 'eco_level': {Crop.CORN: Lvl.NONE},
           'selected_pmt_factor': {Crop.CORN: 1}, }
    c = CropIns(2023, overrides=ovr, prem=p)
    assert not hasattr(c, 'indemnity') or Crop.CORN not in c.indemnity


def test_cannot_add_sco_if_base_insurance_is_area():
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    ovr = {'insure': {Crop.CORN: Ins.YES}, 'unit': {Crop.CORN: Unit.AREA},
           'protection': {Crop.CORN: Prot.RP}, 'level': {Crop.CORN: 75},
           'sco_level': {Crop.CORN: Lvl.DFLT}, 'eco_level': {Crop.CORN: Lvl.NONE},
           'selected_pmt_factor': {Crop.CORN: 1}, }

    with pytest.raises(ValueError):
        CropIns(2023, overrides=ovr, prem=p)


def test_can_add_eco_without_sco():
    """
    Legally it is possible for a farmer to purchase eco without sco.  The scenario
    manager shows that this choice sometimes maximizes net crop insurance revenue.
    """
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    ovr = {'insure': {Crop.CORN: Ins.YES}, 'unit': {Crop.CORN: Unit.ENT},
           'protection': {Crop.CORN: Prot.RP}, 'level': {Crop.CORN: 75},
           'sco_level': {Crop.CORN: Lvl.NONE}, 'eco_level': {Crop.CORN: 90},
           'selected_pmt_factor': {Crop.CORN: 1}, }

    ci = CropIns(2023, overrides=ovr, prem=p)
    assert (ci.total_indemnity_crop(Crop.CORN, pf=.8, yf=.8) ==
            pytest.approx(704796.216, TOL))
    assert (ci.total_premium_crop(Crop.CORN) == pytest.approx(140666.895, TOL))


def test_cannot_add_eco_with_area_unit():
    """
    The restriction that the base policy be enterprise only prevents an ECO
    policy from being used.  SCO should be OK.
    """
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    ovr = {'insure': {Crop.CORN: Ins.YES}, 'unit': {Crop.CORN: Unit.AREA},
           'protection': {Crop.CORN: Prot.RP}, 'level': {Crop.CORN: 75},
           'sco_level': {Crop.CORN: Lvl.NONE}, 'eco_level': {Crop.CORN: 90},
           'selected_pmt_factor': {Crop.CORN: 1}, }

    with pytest.raises(ValueError):
        CropIns(2023, overrides=ovr, prem=p)


def test_sco_level_greater_than_base_level_is_ok():
    """
    Legally it is possible for the bottom sco level to be greater than the
    base level, leaving a gap.  It is not clear when this would be a good idea,
    but it is now supported.
    """
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    ovr = {'insure': {Crop.CORN: Ins.YES}, 'unit': {Crop.CORN: Unit.ENT},
           'protection': {Crop.CORN: Prot.RP}, 'level': {Crop.CORN: 75},
           'sco_level': {Crop.CORN: 80}, 'eco_level': {Crop.CORN: 90},
           'selected_pmt_factor': {Crop.CORN: 1}, }

    ci = CropIns(2023, overrides=ovr, prem=p)
    assert (ci.total_indemnity_crop(Crop.CORN, pf=.8, yf=.8) ==
            pytest.approx(1028547.804, TOL))
    assert (ci.total_premium_crop(Crop.CORN) == pytest.approx(188584.065, TOL))


def test_sco_level_equal_to_base_level_is_ok():
    """
    This case should give the same results as if the sco_level is set to 1.
    """
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    ovr = {'insure': {Crop.CORN: Ins.YES}, 'unit': {Crop.CORN: Unit.ENT},
           'protection': {Crop.CORN: Prot.RP}, 'level': {Crop.CORN: 75},
           'sco_level': {Crop.CORN: 75}, 'eco_level': {Crop.CORN: 90},
           'selected_pmt_factor': {Crop.CORN: 1}, }

    ci = CropIns(2023, overrides=ovr, prem=p)
    assert (ci.total_net_crop_ins_indemnity(pf=.8, yf=.8) ==
            pytest.approx(1640664.574, TOL))


def test_sco_level_less_than__base_level_throws():
    """
    Setting the SCO level below the base level should not be allowed.
    """
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    ovr = {'insure': {Crop.CORN: Ins.YES}, 'unit': {Crop.CORN: Unit.ENT},
           'protection': {Crop.CORN: Prot.RP}, 'level': {Crop.CORN: 75},
           'sco_level': {Crop.CORN: 65}, 'eco_level': {Crop.CORN: 90},
           'selected_pmt_factor': {Crop.CORN: 1}, }

    with pytest.raises(ValueError):
        CropIns(2023, overrides=ovr, prem=p)


def test_indemnity_and_its_parts_cannot_be_less_than_zero():
    # insure corn with an enterprise unit, rp protection at a 65% level
    # with supplemental coverage option and enhanced coverage to 90%
    # in a scenario of normal yields and prices (no indemnity)
    ovr = {'insure': {Crop.CORN: Ins.YES}, 'unit': {Crop.CORN: Unit.ENT},
           'protection': {Crop.CORN: Prot.RP}, 'level': {Crop.CORN: 65},
           'sco_level': {Crop.CORN: Lvl.DFLT}, 'eco_level': {Crop.CORN: 90},
           'selected_pmt_factor': {Crop.CORN: 1}, }

    c = CropIns(2023, overrides=ovr, prem=p)
    crop = Crop.CORN
    assert c.indemnity[Crop.CORN].harvest_indemnity_pmt(pf=1, yf=1) == 0
    assert (c.indemnity[Crop.CORN].total_indemnity_pmt_received(pf=1, yf=1) ==
            pytest.approx(1991.901, TOL))
    assert c.sco[Crop.CORN].harvest_indemnity_pmt(pf=1, yf=1) == 0
    assert c.eco[Crop.CORN].harvest_indemnity_pmt(pf=1, yf=1) == 0
    assert c.total_indemnity_crop(crop, pf=1, yf=1) == pytest.approx(1991.901, TOL)


def test_multiple_configurations():
    """
    Loop through a list of crop insurance configurations checking the values
    returned by total_net_crop_ins_indemnity for a few different pf/yf
    combinations (48 different checks total) all verified against Excel
    """

    factors = [(.75, .7), (.75, 1), (1, .7), (1, 1), (2.5, .7)]

    configs = [
        (Unit.AREA, Prot.RP, Lvl.NONE, Lvl.NONE),
        (Unit.AREA, Prot.RPHPE, Lvl.NONE, Lvl.NONE),
        (Unit.AREA, Prot.YO, Lvl.NONE, Lvl.NONE),
        (Unit.ENT, Prot.RP, Lvl.NONE, Lvl.NONE),
        (Unit.ENT, Prot.RPHPE, Lvl.NONE, Lvl.NONE),
        (Unit.ENT, Prot.YO, Lvl.NONE, Lvl.NONE),
        (Unit.ENT, Prot.RP, Lvl.DFLT, Lvl.NONE),
        (Unit.ENT, Prot.RPHPE, Lvl.DFLT, Lvl.NONE),
        (Unit.ENT, Prot.YO, Lvl.DFLT, Lvl.NONE),
        (Unit.ENT, Prot.RP, Lvl.DFLT, 90),
        (Unit.ENT, Prot.RPHPE, Lvl.DFLT, 90),
        (Unit.ENT, Prot.YO, Lvl.DFLT, 90), ]

    values = [2359525.327, 2383567.332, -32515.612,
              1518295.213, 1559900.113, 100573.179,
              2353429.137, 2423163.501, 960871.075,
              2594207.266, 2691981.164, 1254461.633,

              -132515.326, -108473.321, -69671.549,
              -97691.305, -56086.405, -52653.782,
              263861.229, 333595.593, -94696.402,
              504639.359, 602413.257, -143172.607,

              -95359.388, -71317.383, -32515.611,
              55535.656, 97140.556, 100573.179,
              852326.497, 922060.861, 960871.075,
              1093104.627, 1190878.525, 1254461.633,

              -132515.326, -108473.321, -69671.549,
              -97691.305, -56086.405, -52653.782,
              -203240.980, -133506.616, -94696.402,
              -304529.613, -206755.715, -143172.607,

              -58203.451, -108473.321, -32515.611,
              208762.617, -56086.405, 100573.179,
              1907893.974, -133506.616, 960871.075,
              2490738.868, -206755.715, 1254461.633,
              ]

    idx = 0
    for pf, yf in factors:
        for u, p, s, e in configs:
            ovr = {'insure': {Crop.CORN: Ins.YES, Crop.SOY: Ins.YES},
                   'unit': {Crop.CORN: u, Crop.SOY: u},
                   'protection': {Crop.CORN: p, Crop.SOY: p},
                   'level': {Crop.CORN: 75, Crop.SOY: 75},
                   'sco_level': {Crop.CORN: s, Crop.SOY: s},
                   'eco_level': {Crop.CORN: e, Crop.SOY: e},
                   'selected_pmt_factor': {Crop.CORN: 1, Crop.SOY: 1}, }
            ci = CropIns(2023, overrides=ovr, prem=p)
            assert (ci.total_net_crop_ins_indemnity(pf, yf)
                    == pytest.approx(values[idx], TOL))
            idx += 1


def test_pmt_factor_scales_premiums_and_indemnities_for_area_unit():
    """
    Check that the premiums and indemnities match Excel when a payment factor
    other than 1 is used.  Payment factor is only used for area unit we think.
    """
    configs = [
        (Unit.AREA, Prot.RP, Lvl.NONE, Lvl.NONE),
        (Unit.AREA, Prot.RPHPE, Lvl.NONE, Lvl.NONE),
        (Unit.AREA, Prot.YO, Lvl.NONE, Lvl.NONE),
        (Unit.ENT, Prot.RP, Lvl.NONE, Lvl.NONE),
        (Unit.ENT, Prot.RPHPE, Lvl.NONE, Lvl.NONE),
        (Unit.ENT, Prot.YO, Lvl.NONE, Lvl.NONE),
        (Unit.ENT, Prot.RP, Lvl.DFLT, Lvl.NONE),
        (Unit.ENT, Prot.RPHPE, Lvl.DFLT, Lvl.NONE),
        (Unit.ENT, Prot.YO, Lvl.DFLT, Lvl.NONE),
        (Unit.ENT, Prot.RP, Lvl.DFLT, 90),
        (Unit.ENT, Prot.RPHPE, Lvl.DFLT, 90),
        (Unit.ENT, Prot.YO, Lvl.DFLT, 90), ]

    premiums = [119263.793, 97625.988, 62704.394,
                101210.851, 59605.951, 56173.328,
                206760.526, 137026.162, 98215.948,
                308049.159, 210275.261, 146692.153,]

    indemnities = [2242864.424, 2242864.424, 33451.824,
                   1619506.064, 1619506.064, 156746.507,
                   2560189.662, 2560189.662, 1059104.989,
                   2902256.425, 2902256.425, 1401171.753,]

    idx = 0
    for u, p, s, e in configs:
        ovr = {'insure': {Crop.CORN: Ins.YES, Crop.SOY: Ins.YES},
               'unit': {Crop.CORN: u, Crop.SOY: u},
               'protection': {Crop.CORN: p, Crop.SOY: p},
               'level': {Crop.CORN: 75, Crop.SOY: 75},
               'sco_level': {Crop.CORN: s, Crop.SOY: s},
               'eco_level': {Crop.CORN: e, Crop.SOY: e},
               'selected_pmt_factor': {Crop.CORN: .9, Crop.SOY: .9}, }
        ci = CropIns(2023, overrides=ovr, prem=p)
        assert (ci.total_premium() == pytest.approx(premiums[idx], TOL))
        assert (ci.total_indemnity(pf=.75, yf=.7) ==
                pytest.approx(indemnities[idx], TOL))
        idx += 1
