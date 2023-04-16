import pytest

from .crop_ins import CropIns
from .premium import Premium
from .util import Crop, Ins, Unit, Prot, Lvl

# Note: tests may fail if changes are made to the data files
# 2023_crop_ins_indemnity.txt or 2023_crop_ins_premiums.txt
# However, changes to the settings in 2023_crop_ins_data.txt should
# not cause any tests to fail because tests will provide overrides

TOL = .01

prem = Premium()


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

    assert c.indemnity_base_crop(crop, pf=.7, yf=.75) == pytest.approx(1225310.792, TOL)

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
            pytest.approx(821049.889, TOL))
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
            pytest.approx(1145783.420, TOL))
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
            pytest.approx(1751889.003, TOL))


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

    values = [2407471.968, 2430786.518, -19368.658,
              1673260.289, 1696993.759, 107695.511,
              2574958.878, 2617839.538, 811322.296,
              2858712.536, 2920548.096, 1124828.574,

              -106902.829, -83588.279, -72403.560,
              -54424.279, -30690.809, -45779.920,
              374062.117, 416942.777, -79142.220,
              594344.398, 656179.958, -117428.250,

              152462.612, 175777.162, -19368.658,
              215466.993, 239200.463, 107695.511,
              890525.672, 933406.332, 811322.296,
              1174279.331, 1236114.891, 1124828.574,

              -107698.830, -84384.280, -72403.560,
              -65224.350, -41490.880, -45779.920,
              -130954.610, -88073.950, -79142.220,
              -198993.260, -137157.700, -117428.250,

              -1629.027, -84384.280, -19368.658,
              241726.511, -41490.880, 107695.511,
              1649974.421, -88073.950, 811322.296,
              2285520.388, -137157.700, 1124828.574, ]

    print()
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

    indemnities = [2263653.718, 2263653.718, 47731.411,
                   1738484.639, 1738484.639, 153475.431,
                   2705913.488, 2705913.488, 890464.516,
                   3057705.796, 3057705.796, 1242256.824,]

    print()
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
