from django.contrib.postgres.fields import ArrayField
from django.db import models


class State(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    name = models.CharField(max_length=20)
    abbr = models.CharField(max_length=2)

    def __str__(self):
        return self.name

    class Meta:
        managed = False


class County(models.Model):
    id = models.IntegerField(primary_key=True)
    code = models.SmallIntegerField()
    name = models.CharField(max_length=40)
    state = models.ForeignKey('State', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.name}, {self.state.abbr}'

    class Meta:
        managed = False


class Crop(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'ext_commodity'
        managed = False


class CropType(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    name = models.CharField(max_length=20)
    abbr = models.CharField(max_length=10)
    crop = models.ForeignKey('Crop', on_delete=models.CASCADE, db_column='commodity_id')

    def __str__(self):
        return f'{self.crop}, {self.name}'

    class Meta:
        db_table = 'ext_commoditytype'
        managed = False


class Practice(models.Model):
    id = models.IntegerField(primary_key=True)
    code = models.SmallIntegerField()
    name = models.CharField(max_length=40)
    crop = models.ForeignKey('Crop', on_delete=models.CASCADE, db_column='commodity_id')

    def __str__(self):
        return f'{self.crop}, {self.name}'

    class Meta:
        db_table = 'ext_practice'
        managed = False


class Subcounty(models.Model):
    id = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=20, null=True)

    def __str__(self):
        return self.id

    class Meta:
        db_table = 'ext_subcounty'
        managed = False


class PracticeAvail(models.Model):
    """
    Materialized view for looking up available farm practices
    (not necessarily the farm practice).
    """
    id = models.IntegerField(primary_key=True)
    state = models.ForeignKey('State', on_delete=models.CASCADE)
    county_code = models.SmallIntegerField()
    crop = models.ForeignKey('Crop', on_delete=models.CASCADE, db_column='commodity_id')
    croptype = models.ForeignKey('CropType', on_delete=models.CASCADE,
                                 db_column='commodity_type_id')
    practice = models.SmallIntegerField()

    class Meta:
        db_table = 'ext_practiceavail'
        managed = False


class SubcountyAvail(models.Model):
    """
    Materialized view for looking up available subcounty_ids
    """
    id = models.IntegerField(primary_key=True)
    state = models.ForeignKey('State', on_delete=models.CASCADE)
    county_code = models.SmallIntegerField()
    crop = models.ForeignKey('Crop', on_delete=models.CASCADE, db_column='commodity_id')
    croptype = models.ForeignKey('CropType', on_delete=models.CASCADE,
                                 db_column='commodity_type_id')
    practice = models.SmallIntegerField()
    subcounty = models.ForeignKey('Subcounty', on_delete=models.CASCADE, null=True)

    class Meta:
        db_table = 'ext_subcountyavail'
        managed = False


class InsurableCropsForCty(models.Model):
    """
    Materialized view for looking up available crops/types/practices for a
    state_id and county_code
    """
    id = models.IntegerField(primary_key=True)
    state_id = models.SmallIntegerField()
    county_code = models.SmallIntegerField()
    crop_id = models.SmallIntegerField(db_column='commodity_id')
    crop_type_id = models.SmallIntegerField(db_column='commodity_type_id')
    is_fac = models.BooleanField()
    practices = ArrayField(models.SmallIntegerField(), size=2)

    class Meta:
        db_table = 'ext_insurable_crops_for_cty'
        managed = False
