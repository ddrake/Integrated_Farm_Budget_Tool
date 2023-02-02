from crop_ins import CropIns

# Note: tests may fail if changes are made to the data textfile


def test_total_crop_ins():
    c = CropIns(2023)
    c.unit_corn = 0
    c.protection_corn = 1
    c.level_corn = 75

    assert c.crop_ins_premium_crop('corn') == 22.09
