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
    overrides = {'insure_corn': '1', 'unit_corn': '1', 'protection_corn': '0',
                 'level_corn': '75', 'add_sco_corn': '1', 'eco_level_corn': '0'}

    c = CropIns(2023, overrides)

    crop = 'corn'
    assert c.crop_ins_premium_crop(crop) == pytest.approx(72847.62, tol)

    assert (c.indemnity_corn.harvest_indemnity_pmt(crop, pf=.7, yf=.75)
            == pytest.approx(587057.954, tol))

    # there should be an SCO indemnity
    assert (c.sco_corn.opt_harvest_indemnity_pmt(crop, pf=.7, yf=.75)
            == pytest.approx(1623206.222, tol))

    # there should not be an ECO indemnity
    assert not hasattr(c, 'eco_corn')


def test_premiums_and_revenue_are_zero_for_a_crop_without_insurance():
    # DON'T insure corn, but set an enterprise unit, rp protection at a 75% level
    # with no optional coverage.
    overrides = {'insure_corn': '0', 'unit_corn': '1', 'protection_corn': '0',
                 'level_corn': '75', 'add_sco_corn': '0', 'eco_level_corn': '0'}

    c = CropIns(2023, overrides)
    crop = 'corn'
    assert c.crop_ins_premium_crop(crop) == 0
    assert c.total_indemnity_crop(crop, pf=.7, yf=.75) == 0
    assert not hasattr(c, 'indemnity_corn')


def test_no_indemnity_attribute_is_added_without_base_insurance():
    # DON'T insure corn, but set an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, and no enhanced coverage
    overrides = {'insure_corn': '0', 'unit_corn': '1', 'protection_corn': '0',
                 'level_corn': '75', 'add_sco_corn': '1', 'eco_level_corn': '0'}
    c = CropIns(2023, overrides)
    assert not hasattr(c, 'indemnity_corn')


def test_cannot_add_sco_if_base_insurance_is_area():
    # insure corn with an enterprise unit, rp protection at a 75% level
    # with supplemental coverage option, but no enhanced coverage
    overrides = {'insure_corn': '1', 'unit_corn': '0', 'protection_corn': '0',
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


def test_indemnity_and_its_parts_cannot_be_less_than_zero():
    # insure corn with an enterprise unit, rp protection at a 65% level
    # with supplemental coverage option and enhanced coverage to 90%
    # in a scenario of normal yields and prices (no indemnity)
    overrides = {'insure_corn': '1', 'unit_corn': '1', 'protection_corn': '0',
                 'level_corn': '65', 'add_sco_corn': '1', 'eco_level_corn': '90'}

    c = CropIns(2023, overrides)
    crop = 'corn'
    assert c.indemnity_corn.harvest_indemnity_pmt(crop, pf=1, yf=1) == 0
    assert c.sco_corn.opt_harvest_indemnity_pmt(crop, pf=1, yf=1) == 0
    assert c.eco_corn.opt_harvest_indemnity_pmt(crop, pf=1, yf=1) == 0
    assert c.total_indemnity_crop(crop, pf=1, yf=1) == 0
