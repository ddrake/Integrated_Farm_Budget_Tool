import pytest

from crop_ins import CropIns

# Note: tests may fail if changes are made to the data files
# 2023_crop_ins_indemnity.txt or 2023_crop_ins_premiums.txt
# However, changes to the settings in 2023_crop_ins_data.txt should
# not cause any tests to fail because tests will provide overrides

# For reference, here are the crop insurance settings definitions:

# insure_[crop]:     (0) Don't insure OR (1) Insure
# unit_[crop]:       (0) County area OR (1) Enterprise
# protection_[crop]: (0) rp OR (1) rphpe OR (2) yo
# level_[crop]:      50, 55, 60, 65, 70, 75, 80, or 85 for ent unit or
#                    70, 75, 80, 85, or 90             for area unit
# add_sco_[crop]:    (0) Don't add sco or (1) add sco
# eco_level_[crop]   (0) Don't add eco or 90 or 95

tol = .01


def test_total_crop_ins():
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    overrides = {'insure_corn': 1, 'unit_corn': 1, 'protection_corn': 0,
                 'level_corn': 75, 'add_sco_corn': 1, 'eco_level_corn': 0,
                 'selected_payment_factor_corn': 1}

    c = CropIns(2023, overrides)

    crop = 'corn'
    assert c.crop_ins_premium_crop(crop) == pytest.approx(72847.62, tol)

    assert (c.indemnity_corn.harvest_indemnity_pmt(pf=.7, yf=.75)
            == pytest.approx(1126643.935, tol))

    # there should be an SCO indemnity
    assert (c.sco_corn.opt_harvest_indemnity_pmt(pf=.7, yf=.75)
            == pytest.approx(593544.579, tol))

    # there should not be an ECO indemnity
    assert not hasattr(c, 'eco_corn')


def test_premiums_and_revenue_are_zero_for_a_crop_without_insurance():
    # DON'T insure corn, but set an enterprise unit, rp protection at a 75% level
    # with no optional coverage.
    overrides = {'insure_corn': 0, 'unit_corn': 1, 'protection_corn': 0,
                 'level_corn': 75, 'add_sco_corn': 0, 'eco_level_corn': 0,
                 'selected_payment_factor_corn': 1}

    c = CropIns(2023, overrides)
    crop = 'corn'
    assert c.crop_ins_premium_crop(crop) == 0
    assert c.total_indemnity_crop(crop, pf=.7, yf=.75) == 0
    assert not hasattr(c, 'indemnity_corn')


def test_no_indemnity_attribute_is_added_without_base_insurance():
    # DON'T insure corn, but set an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, and no enhanced coverage
    overrides = {'insure_corn': 0, 'unit_corn': 1, 'protection_corn': 0,
                 'level_corn': 75, 'add_sco_corn': 1, 'eco_level_corn': 0,
                 'selected_payment_factor_corn': 1}
    c = CropIns(2023, overrides)
    assert not hasattr(c, 'indemnity_corn')


def test_cannot_add_sco_if_base_insurance_is_area():
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    overrides = {'insure_corn': 1, 'unit_corn': 0, 'protection_corn': 0,
                 'level_corn': 75, 'add_sco_corn': 1, 'eco_level_corn': 0,
                 'selected_payment_factor_corn': 1}

    with pytest.raises(ValueError):
        CropIns(2023, overrides)


def test_cannot_add_eco_unless_sco_is_added():
    """
    Legally it is possible for a farmer to purchase eco without sco, but it is
    not clear why this would be considered a good idea, and allowing it would
    complicate the logic somewhat
    """
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    overrides = {'insure_corn': 1, 'unit_corn': 0, 'protection_corn': 1,
                 'level_corn': 75, 'add_sco_corn': 0, 'eco_level_corn': 90,
                 'selected_payment_factor_corn': 1}

    with pytest.raises(ValueError):
        CropIns(2023, overrides)


def test_indemnity_and_its_parts_cannot_be_less_than_zero():
    # insure corn with an enterprise unit, rp protection at a 65% level
    # with supplemental coverage option and enhanced coverage to 90%
    # in a scenario of normal yields and prices (no indemnity)
    overrides = {'insure_corn': 1, 'unit_corn': 1, 'protection_corn': 0,
                 'level_corn': 65, 'add_sco_corn': 1, 'eco_level_corn': 90,
                 'selected_payment_factor_corn': 1}

    c = CropIns(2023, overrides)
    crop = 'corn'
    assert c.indemnity_corn.harvest_indemnity_pmt(pf=1, yf=1) == 0
    assert (c.indemnity_corn.tot_indemnity_pmt_received(pf=1, yf=1) ==
            pytest.approx(1991.901))
    assert c.sco_corn.opt_harvest_indemnity_pmt(pf=1, yf=1) == 0
    assert c.eco_corn.opt_harvest_indemnity_pmt(pf=1, yf=1) == 0
    assert c.total_indemnity_crop(crop, pf=1, yf=1) == pytest.approx(1991.901, .01)


def test_multiple_configurations():
    """
    Loop through a list of crop insurance configurations checking the values
    returned by total_net_crop_ins_indemnity for a few different pf/yf
    combinations (48 different checks total) all verified against Excel
    """

    factors = [(.75, .7), (.75, 1), (1, .7), (1, 1)]

    configs = [(0, 0, 0, 0), (0, 1, 0, 0), (0, 2, 0, 0),
               (1, 0, 0, 0), (1, 1, 0, 0), (1, 2, 0, 0),
               (1, 0, 1, 0), (1, 1, 1, 0), (1, 2, 1, 0),
               (1, 0, 1, 90), (1, 1, 1, 90), (1, 2, 1, 90), ]

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
              -304529.613, -206755.715, -143172.607]

    idx = 0
    for pf, yf in factors:
        for u, p, s, e in configs:
            ovr = {'insure_corn': 1, 'unit_corn': u, 'protection_corn': p,
                   'level_corn': 75, 'add_sco_corn': s, 'eco_level_corn': e,
                   'insure_soy': 1, 'unit_soy': u, 'protection_soy': p,
                   'level_soy': 75, 'add_sco_soy': s, 'eco_level_soy': e,
                   'selected_payment_factor_corn': 1, 'selected_payment_factor_soy': 1}
            ci = CropIns(2023, overrides=ovr)
            assert (ci.total_net_crop_ins_indemnity(pf, yf)
                    == pytest.approx(values[idx], .01))
            idx += 1


def test_payment_factor_scales_premiums_and_indemnities():
    """
    Check that the premiums and indemnities match Excel when a payment factor
    other than 1 is used
    """
    configs = [(0, 0, 0, 0), (0, 1, 0, 0), (0, 2, 0, 0),
               (1, 0, 0, 0), (1, 1, 0, 0), (1, 2, 0, 0),
               (1, 0, 1, 0), (1, 1, 1, 0), (1, 2, 1, 0),
               (1, 0, 1, 90), (1, 1, 1, 90), (1, 2, 1, 90), ]

    premiums = [119263.793, 97625.988, 62704.394,
                91089.765, 53645.355, 50555.995,
                196639.440, 131065.566, 92598.615,
                297928.073, 204314.665, 141074.820,]

    indemnities = [2242836.588, 2242836.588, 33440.343,
                   1619506.064, 1619506.064, 156746.507,
                   2560189.662, 2560189.662, 1059087.023,
                   2902256.425, 2902256.425, 1401153.786,]

    idx = 0
    for u, p, s, e in configs:
        ovr = {'insure_corn': 1, 'unit_corn': u, 'protection_corn': p,
               'level_corn': 75, 'add_sco_corn': s, 'eco_level_corn': e,
               'insure_soy': 1, 'unit_soy': u, 'protection_soy': p,
               'level_soy': 75, 'add_sco_soy': s, 'eco_level_soy': e,
               'selected_payment_factor_corn': .9, 'selected_payment_factor_soy': .9}
        ci = CropIns(2023, overrides=ovr)
        assert (ci.total_premium() == pytest.approx(premiums[idx]))
        assert (ci.total_indemnity(pf=.75, yf=.7) ==
                pytest.approx(indemnities[idx]))
        idx += 1
