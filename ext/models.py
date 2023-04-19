from django.db import models
from django.contrib.postgres.fields import ArrayField


class SmallFloatField(models.FloatField):
    def db_type(self, connection):
        return 'real'


class Commodity(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    name = models.CharField(max_length=20)


class State(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    name = models.CharField(max_length=20)
    abbr = models.CharField(max_length=2)


class County(models.Model):
    code = models.SmallIntegerField()
    name = models.CharField(max_length=40)
    state = models.ForeignKey(State, on_delete=models.CASCADE)

    class Meta:
        indexes = [models.Index(fields=['state_id', 'code'])]


class InsurancePlan(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    abbr = models.CharField(max_length=20)


class InsuranceOption(models.Model):
    id = models.CharField(max_length=2, primary_key=True)
    name = models.CharField(max_length=40)


class CoverageType(models.Model):
    id = models.CharField(max_length=1, primary_key=True)
    name = models.CharField(max_length=20)


class OptionLevel(models.Model):
    id = models.CharField(max_length=1, primary_key=True)
    name = models.CharField(max_length=20)


class CommodityType(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    name = models.CharField(max_length=20)
    abbr = models.CharField(max_length=10)
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)


# The code for practice is not unique, so it can't be a PK
# There are only two county practices: 3 Non-irrigated and 53 NFac non-irrigated.
# Wheat and corn are always 3, but soybeans can be either, depending on county.
class Practice(models.Model):
    code = models.SmallIntegerField()
    name = models.CharField(max_length=40)
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)

    class Meta:
        indexes = [models.Index(fields=['commodity_id', 'code'])]


class SubCounty(models.Model):
    id = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=40, null=True)


class RateMethods(models.Model):
    id = models.CharField(max_length=1, primary_key=True)
    name = models.CharField(max_length=40, null=True)


# I dropped the practice column.  It's always 3 for corn and wheat.
# For soybeans it's either 3 Non-irrigated or 53 Nfac Nonirrigated, based on which
# county codes it.
class SubCountyRate(models.Model):
    county_code = models.SmallIntegerField()
    subcounty_rate = SmallFloatField(null=True)
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    rate_method = models.ForeignKey(RateMethods, on_delete=models.CASCADE, null=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    subcounty = models.ForeignKey(SubCounty, on_delete=models.CASCADE)
    high_risk = models.BooleanField()

    class Meta:
        indexes = [
            models.Index(fields=[
                'state_id', 'county_code', 'subcounty_id',
                'commodity_id', 'commodity_type_id'])
        ]


# TODO: this could be deleted, should we? Yes, but not yet...
class InsuranceOfferArea(models.Model):
    # ADM Insurance Offer Code
    id = models.IntegerField(primary_key=True)
    county_code = models.SmallIntegerField()
    practice = models.SmallIntegerField()
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    insurance_plan = models.ForeignKey(InsurancePlan, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)


# array(500, 2)
class Beta(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    draw = ArrayField(SmallFloatField(), size=1000)


# Reshape to (8,6)
class UnitDiscount(models.Model):
    id = models.IntegerField(primary_key=True)
    enterprise_discount_factor = ArrayField(SmallFloatField(), size=48)


class InsuranceOfferEnt(models.Model):
    # ADM Insurance Offer Code
    id = models.IntegerField(primary_key=True)
    county_code = models.SmallIntegerField()
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    practice = models.SmallIntegerField()
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    beta = models.ForeignKey(Beta, on_delete=models.CASCADE, null=True)
    unit_discount = models.ForeignKey(UnitDiscount, on_delete=models.CASCADE, null=True)

    class Meta:
        indexes = [
            models.Index(fields=[
                'state_id', 'county_code', 'commodity_id',
                'commodity_type_id', 'practice'
            ])]


class Subsidy(models.Model):
    id = models.IntegerField(primary_key=True)
    subsidy = ArrayField(SmallFloatField(), size=8)


class BaseRate(models.Model):
    county_code = models.SmallIntegerField()
    practice = models.SmallIntegerField()
    refyield = ArrayField(SmallFloatField(), size=2)
    refrate = ArrayField(SmallFloatField(), size=2)
    exponent = ArrayField(SmallFloatField(), size=2)
    fixedrate = ArrayField(SmallFloatField(), size=2)
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            models.Index(fields=[
                'state_id', 'county_code', 'commodity_id',
                'commodity_type_id', 'practice'
            ])]


class ComboRevenueFactor(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    std_deviation_qty = SmallFloatField()
    mean_qty = SmallFloatField()


# The part of CoverageLevelDifferential that doesn't depend on insurance_plan
# array(8, 2).  The high_risk column is not necessary for any computations, but
# one can see that high_risk implies lower rate differential_factor values.
class RateDifferential(models.Model):
    county_code = models.SmallIntegerField()
    rate_differential_factor = ArrayField(SmallFloatField(), size=16)
    practice = models.SmallIntegerField()
    high_risk = models.BooleanField()
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            models.Index(fields=[
                'state_id', 'county_code', 'commodity_id',
                'commodity_type_id', 'practice'
            ])]


# The part of CoverageLevelDifferential that depend on insurance_plan: YP vs RP/RP-HPE
# array(8, 2).  The high_risk column is not necessary for any computations, but
# one can see that high_risk implies higher enterprise_residual_factor values.
class EnterpriseFactor(models.Model):
    county_code = models.SmallIntegerField()
    enterprise_residual_factor_r = ArrayField(SmallFloatField(), size=16)
    enterprise_residual_factor_y = ArrayField(SmallFloatField(), size=16)
    practice = models.SmallIntegerField()
    high_risk = models.BooleanField()
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            models.Index(fields=[
                'state_id', 'county_code', 'commodity_id',
                'commodity_type_id', 'practice'
            ])]


# array(2) ordered (HF, PF)
class OptionRate(models.Model):
    county_code = models.SmallIntegerField()
    option_rate = ArrayField(SmallFloatField(), size=2)
    practice = models.SmallIntegerField()
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            models.Index(fields=[
                'state_id', 'county_code', 'commodity_id',
                'commodity_type_id', 'practice'
            ])]


# Gives all county rates for a given
# (insurance_plan_id, price_volatility_factor (which is NULL for Yield plans))
# The array indexes over coverage levels.
class AreaRate(models.Model):
    price_volatility_factor = models.IntegerField(null=True)
    county_code = models.SmallIntegerField()
    base_rate = ArrayField(ArrayField(SmallFloatField()))
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    insurance_plan = models.ForeignKey(InsurancePlan, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            models.Index(fields=[
                'insurance_plan_id', 'state_id', 'county_code', 'commodity_id',
                'commodity_type_id', 'price_volatility_factor'])
        ]


# Needed for computation of ARP, ARP-HPE, AYP
class ExpectedYield(models.Model):
    county_code = models.SmallIntegerField()
    expected_yield = SmallFloatField(null=True)
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            models.Index(fields=[
                'state_id', 'county_code', 'commodity_id',
                'commodity_type_id'
            ])]
