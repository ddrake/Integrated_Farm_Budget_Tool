import pytest

from ifbt import CropIns, Premiums, Crop, Ins, Unit, Prot, Lvl

# Note: tests may fail if changes are made to the data files
# 2023_crop_ins_indemnity.txt or 2023_crop_ins_premiums.txt
# However, changes to the settings in 2023_crop_ins_data.txt should
# not cause any tests to fail because tests will provide overrides

TOL = .01

prem = Premiums()


def test_total_crop_ins():
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    ovr = {'insure': {Crop.CORN: Ins.YES}, 'unit': {Crop.CORN: Unit.ENT},
           'protection': {Crop.CORN: Prot.RP},
           'level': {Crop.CORN: 75}, 'sco_level': {Crop.CORN: Lvl.DFLT},
           'eco_level': {Crop.CORN: Lvl.NONE},
           'prot_factor': {Crop.CORN: 1}}

    c = CropIns(2023, overrides=ovr, prem=prem)

    crop = Crop.CORN
    assert c.premium_base_crop(crop) == pytest.approx(39085.875, TOL)

    assert c.indemnity_base_crop(crop, pf=.7, yf=.75) == pytest.approx(1126643.935, TOL)

    # there should be an SCO indemnity
    assert c.indemnity_sco_crop(crop, pf=.7, yf=.75) == pytest.approx(593544.579, TOL)

    # there should not be an ECO indemnity for CORN
    assert c.indemnity_eco_crop(crop, pf=.7, yf=.75) == 0


def test_premiums_and_revenue_are_zero_for_a_crop_without_insurance():
    # DON'T insure corn, but set an enterprise unit, rp protection at a 75% level
    # with no optional coverage.
    ovr = {'insure': {Crop.CORN: Ins.NO}, 'unit': {Crop.CORN: Unit.ENT},
           'protection': {Crop.CORN: Prot.RP}, 'level': {Crop.CORN: 75},
           'sco_level': {Crop.CORN: Lvl.NONE}, 'eco_level': {Crop.CORN: Lvl.NONE},
           'prot_factor': {Crop.CORN: 1}, }

    c = CropIns(2023, overrides=ovr, prem=prem)
    crop = Crop.CORN
    assert c.premium_base_crop(crop) == 0
    assert c.indemnity_base_crop(crop, pf=.7, yf=.75) == 0


def test_indemnity_is_zero_without_base_insurance():
    # DON'T insure corn, but set an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, and no enhanced coverage
    ovr = {'insure': {Crop.CORN: Ins.NO}, 'unit': {Crop.CORN: Unit.ENT},
           'protection': {Crop.CORN: Prot.RP}, 'level': {Crop.CORN: 75},
           'sco_level': {Crop.CORN: Lvl.DFLT}, 'eco_level': {Crop.CORN: Lvl.NONE},
           'prot_factor': {Crop.CORN: 1}, }
    c = CropIns(2023, overrides=ovr, prem=prem)
    assert c.indemnity_base_crop(Crop.CORN) == 0


def test_cannot_add_sco_if_base_insurance_is_area():
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    ovr = {'insure': {Crop.CORN: Ins.YES}, 'unit': {Crop.CORN: Unit.AREA},
           'protection': {Crop.CORN: Prot.RP}, 'level': {Crop.CORN: 75},
           'sco_level': {Crop.CORN: Lvl.DFLT}, 'eco_level': {Crop.CORN: Lvl.NONE},
           'prot_factor': {Crop.CORN: 1}, }

    with pytest.raises(ValueError):
        CropIns(2023, overrides=ovr, prem=prem)


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
           'prot_factor': {Crop.CORN: 1}, }

    ci = CropIns(2023, overrides=ovr, prem=prem)
    assert (ci.total_indemnity_crop(Crop.CORN, pf=.8, yf=.8) ==
            pytest.approx(704796.216, TOL))
    assert (ci.total_premium_crop(Crop.CORN) == pytest.approx(83622.644, TOL))


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
           'prot_factor': {Crop.CORN: 1}, }

    with pytest.raises(ValueError):
        CropIns(2023, overrides=ovr, prem=prem)


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
           'prot_factor': {Crop.CORN: 1}, }

    ci = CropIns(2023, overrides=ovr, prem=prem)
    assert (ci.total_indemnity_crop(Crop.CORN, pf=.8, yf=.8) ==
            pytest.approx(1028547.804, TOL))
    assert (ci.total_premium_crop(Crop.CORN) == pytest.approx(113708.204, TOL))


def test_sco_level_equal_to_base_level_is_ok():
    """
    This case should give the same results as if the sco_level is set to 1.
    """
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    ovr = {'insure': {Crop.CORN: Ins.YES}, 'unit': {Crop.CORN: Unit.ENT},
           'protection': {Crop.CORN: Prot.RP}, 'level': {Crop.CORN: 75},
           'sco_level': {Crop.CORN: 75}, 'eco_level': {Crop.CORN: 90},
           'prot_factor': {Crop.CORN: 1}, }

    ci = CropIns(2023, overrides=ovr, prem=prem)
    assert (ci.total_net_indemnity(pf=.8, yf=.8) ==
            pytest.approx(2001774.451, TOL))


def test_sco_level_less_than__base_level_throws():
    """
    Setting the SCO level below the base level should not be allowed.
    """
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    ovr = {'insure': {Crop.CORN: Ins.YES}, 'unit': {Crop.CORN: Unit.ENT},
           'protection': {Crop.CORN: Prot.RP}, 'level': {Crop.CORN: 75},
           'sco_level': {Crop.CORN: 65}, 'eco_level': {Crop.CORN: 90},
           'prot_factor': {Crop.CORN: 1}, }

    with pytest.raises(ValueError):
        CropIns(2023, overrides=ovr, prem=prem)


def test_indemnity_and_its_parts_cannot_be_less_than_zero():
    # insure corn with an enterprise unit, rp protection at a 65% level
    # with supplemental coverage option and enhanced coverage to 90%
    # in a scenario of normal yields and prices (no indemnity)
    ovr = {'insure': {Crop.CORN: Ins.YES}, 'unit': {Crop.CORN: Unit.ENT},
           'protection': {Crop.CORN: Prot.RP}, 'level': {Crop.CORN: 65},
           'sco_level': {Crop.CORN: Lvl.DFLT}, 'eco_level': {Crop.CORN: 90},
           'prot_factor': {Crop.CORN: 1}, }

    c = CropIns(2023, overrides=ovr, prem=prem)
    crop = Crop.CORN
    assert c.indemnity_base_crop(crop, pf=1, yf=1) == 0
    assert c.indemnity_sco_crop(crop, pf=1, yf=1) == 0
    assert c.indemnity_eco_crop(crop, pf=1, yf=1) == 0
    assert c.total_indemnity_crop(crop, pf=1, yf=1) == 0


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

    values = [2911813.731, 2900808.448, 422779.864,
              1713861.057, 1737592.052, 134047.695,
              2628448.099, 2633551.801, 1091737.875,
              2943715.023, 2957304.175, 1413836.992,

              52322.103, 75633.544, -72393.002,
              -53938.197, -30207.202, -45773.352,
              581527.718, 624403.846, -77977.773,
              864260.816, 926090.001, -104676.781,

              407594.038, 385149.846, 422779.864,
              114605.960, 138336.955, 134047.695,
              1060654.827, 1056362.923, 1091737.875,
              1360539.937, 1358049.077, 1413836.992,

              -107681.166, -84369.725, -72393.002,
              -65215.088, -41484.093, -45773.352,
              -129783.684, -86907.556, -77977.773,
              -186232.286, -124403.101, -104676.781,

              882664.567, -84369.725, 422779.864,
              294427.008, -41484.093, 134047.695,
              2191131.776, -88061.536, 1091737.875,
              2863532.418, -137140.258, 1413836.992,
              ]

    idx = 0
    for pf, yf in factors:
        for u, p, s, e in configs:
            ovr = {'insure': {Crop.CORN: Ins.YES, Crop.FULL_SOY: Ins.YES,
                              Crop.DC_SOY: Ins.YES, Crop.WHEAT: Ins.YES},
                   'unit': {Crop.CORN: u, Crop.FULL_SOY: u, Crop.DC_SOY: u,
                            Crop.WHEAT: u},
                   'protection': {Crop.CORN: p, Crop.FULL_SOY: p, Crop.DC_SOY: p,
                                  Crop.WHEAT: p},
                   'level': {Crop.CORN: 75, Crop.FULL_SOY: 75, Crop.DC_SOY: 75,
                             Crop.WHEAT: 75},
                   'sco_level': {Crop.CORN: s, Crop.FULL_SOY: s, Crop.DC_SOY: s,
                                 Crop.WHEAT: s},
                   'eco_level': {Crop.CORN: e, Crop.FULL_SOY: e, Crop.DC_SOY: e,
                                 Crop.WHEAT: e},
                   'prot_factor': {Crop.CORN: 1, Crop.FULL_SOY: 1,
                                   Crop.DC_SOY: 1, Crop.WHEAT: 1}, }
            ci = CropIns(2023, overrides=ovr, prem=prem)
            assert (ci.total_net_indemnity(pf, yf)
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

    premiums = [96896.783, 75918.264, 65169.606,
                65215.088, 41484.093, 45773.352,
                130937.663, 88061.536, 79131.753,
                198969.443, 137140.258, 117413.938,]

    indemnities = [2717545.407, 2686660.355, 445655.580,
                   1779076.145, 1779076.145, 179821.048,
                   2779055.580, 2743679.556, 1170869.628,
                   3142684.466, 3094444.433, 1531250.930,]

    idx = 0
    for u, p, s, e in configs:
        ovr = {'insure': {Crop.CORN: Ins.YES, Crop.FULL_SOY: Ins.YES,
                          Crop.DC_SOY: Ins.YES, Crop.WHEAT: Ins.YES},
               'unit': {Crop.CORN: u, Crop.FULL_SOY: u, Crop.DC_SOY: u,
                        Crop.WHEAT: u},
               'protection': {Crop.CORN: p, Crop.FULL_SOY: p, Crop.DC_SOY: p,
                              Crop.WHEAT: p},
               'level': {Crop.CORN: 75, Crop.FULL_SOY: 75, Crop.DC_SOY: 75,
                         Crop.WHEAT: 75},
               'sco_level': {Crop.CORN: s, Crop.FULL_SOY: s, Crop.DC_SOY: s,
                             Crop.WHEAT: s},
               'eco_level': {Crop.CORN: e, Crop.FULL_SOY: e, Crop.DC_SOY: e,
                             Crop.WHEAT: e},
               'prot_factor': {Crop.CORN: .9, Crop.FULL_SOY: .9,
                               Crop.DC_SOY: .9, Crop.WHEAT: .9}, }
        ci = CropIns(2023, overrides=ovr, prem=prem)
        assert (ci.total_premium() == pytest.approx(premiums[idx], TOL))
        assert (ci.total_indemnity(pf=.75, yf=.7) ==
                pytest.approx(indemnities[idx], TOL))
        idx += 1
