import pytest

from crop_ins import CropIns

# Note: tests may fail if changes are made to the data files
# 2023_crop_ins_indemnity.txt or 2023_crop_ins_premiums.txt
# However, changes to the settings in 2023_crop_ins_data.txt should
# not cause any tests to fail because tests will provide overrides

tol = .01


def test_total_crop_ins():
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    overrides = {'insure_corn': '1', 'unit_corn': '1', 'protection_corn': '1',
                 'level_corn': '75', 'add_sco_corn': '1', 'eco_level_corn': '0'}

    c = CropIns(2023, overrides)
    c.insure_corn = 1
    c.unit_corn = 1
    c.protection_corn = 1
    c.level_corn = 75
    c.add_sco_corn = 1

    crop = 'corn'
    assert c.crop_ins_premium_crop(crop) == pytest.approx(42424.02, tol)

    assert (c.indemnity_corn.harvest_indemnity_pmt(crop, pf=.7, yf=.75)
            == pytest.approx(587057.954, tol))

    # there should be an SCO indemnity
    assert (c.sco_corn.opt_harvest_indemnity_pmt(crop, pf=.7, yf=.75)
            == pytest.approx(1623206.222, tol))

    # there should not be an ECO indemnity
    assert not hasattr(c, 'eco_corn')


def test_cannot_add_sco_if_base_insurance_is_area():
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    overrides = {'insure_corn': '1', 'unit_corn': '0', 'protection_corn': '1',
                 'level_corn': '75', 'add_sco_corn': '1', 'eco_level_corn': '0'}

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
    overrides = {'insure_corn': '1', 'unit_corn': '0', 'protection_corn': '1',
                 'level_corn': '75', 'add_sco_corn': '0', 'eco_level_corn': '90'}

    with pytest.raises(ValueError):
        CropIns(2023, overrides)
