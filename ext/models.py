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
class Practice(models.Model):
    code = models.SmallIntegerField()
    name = models.CharField(max_length=40)
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)


class SubCounty(models.Model):
    id = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=40, null=True)


class RateMethods(models.Model):
    id = models.CharField(max_length=1, primary_key=True)
    name = models.CharField(max_length=40, null=True)


# Deal with this last - I doubt if it affects anything, but need to check
# the worksheet.
class SubCountyRate(models.Model):
    county_code = models.SmallIntegerField()
    subcounty_rate = SmallFloatField(null=True)
    practice = models.SmallIntegerField()
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    rate_method = models.ForeignKey(RateMethods, on_delete=models.CASCADE, null=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    subcounty = models.ForeignKey(SubCounty, on_delete=models.CASCADE)


class InsuranceOfferArea(models.Model):
    # ADM Insurance Offer Code
    id = models.IntegerField(primary_key=True)
    county_code = models.SmallIntegerField()
    practice = models.SmallIntegerField()
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    insurance_plan = models.ForeignKey(InsurancePlan, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)


# TODO: make beta_id and unit_discount_id foreign keys
class InsuranceOfferEnt(models.Model):
    # ADM Insurance Offer Code
    id = models.IntegerField(primary_key=True)
    county_code = models.SmallIntegerField()
    beta_id = models.SmallIntegerField(null=True)
    unit_discount_id = models.IntegerField(null=True)
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    practice = models.SmallIntegerField()
    state = models.ForeignKey(State, on_delete=models.CASCADE)


class Subsidy(models.Model):
    unit_structure_code = models.CharField(max_length=2, null=True)
    coverage_level = SmallFloatField()
    subsidy = SmallFloatField()
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE, null=True)
    coverage_type = models.ForeignKey(CoverageType, on_delete=models.CASCADE)
    insurance_plan = models.ForeignKey(InsurancePlan, on_delete=models.CASCADE)


class Subsidy1(models.Model):
    id = models.IntegerField(primary_key=True)
    subsidy = ArrayField(SmallFloatField(), size=8)


class Beta(models.Model):
    beta_id = models.SmallIntegerField()
    yield_draw = SmallFloatField()
    price_draw = SmallFloatField()


# array(500, 2)
class Beta1(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    draw = ArrayField(SmallFloatField(), size=1000)


class BaseRate(models.Model):
    county_code = models.SmallIntegerField()
    reference_yield = SmallFloatField()
    reference_rate = SmallFloatField()
    exponent = SmallFloatField()
    fixed_rate = SmallFloatField()
    reference_rate_prior = SmallFloatField()
    exponent_prior = SmallFloatField()
    fixed_rate_prior = SmallFloatField()
    practice = models.SmallIntegerField()
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    insurance_plan = models.ForeignKey(InsurancePlan, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    reference_yield_prior = SmallFloatField()


class BaseRate1(models.Model):
    county_code = models.SmallIntegerField()
    practice = models.SmallIntegerField()
    refyield = ArrayField(SmallFloatField(), size=2)
    refrate = ArrayField(SmallFloatField(), size=2)
    exponent = ArrayField(SmallFloatField(), size=2)
    fixedrate = ArrayField(SmallFloatField(), size=2)
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)


class ComboRevenueFactor(models.Model):
    base_rate = SmallFloatField()
    std_deviation_qty = SmallFloatField()
    mean_qty = SmallFloatField()
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)


class ComboRevenueFactor1(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    std_deviation_qty = SmallFloatField()
    mean_qty = SmallFloatField()


# The part of CoverageLevelDifferential that doesn't depend on insurance_plan
class RateDifferential(models.Model):
    county_code = models.SmallIntegerField()
    coverage_level = SmallFloatField()
    rate_differential_factor = SmallFloatField(null=True)
    enterprise_residual_factor = SmallFloatField(null=True)
    rate_differential_factor_prior = SmallFloatField(null=True)
    enterprise_residual_factor_prior = SmallFloatField(null=True)
    practice = models.SmallIntegerField()
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    coverage_type = models.ForeignKey(CoverageType, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    subcounty = models.ForeignKey(SubCounty, on_delete=models.CASCADE, null=True)


# array(8, 2)
class RateDifferential1(models.Model):
    county_code = models.SmallIntegerField()
    rate_differential_factor = ArrayField(SmallFloatField(), size=16)
    practice = models.SmallIntegerField()
    high_risk = models.BooleanField()
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)


# The part of CoverageLevelDifferential that depend on insurance_plan: YP vs RP/RP-HPE
class EnterpriseFactor(models.Model):
    county_code = models.SmallIntegerField()
    coverage_level = SmallFloatField()
    enterprise_residual_factor = SmallFloatField(null=True)
    enterprise_residual_factor_prior = SmallFloatField(null=True)
    practice = models.SmallIntegerField()
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    coverage_type = models.ForeignKey(CoverageType, on_delete=models.CASCADE)
    insurance_plan = models.ForeignKey(InsurancePlan, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    subcounty = models.ForeignKey(SubCounty, on_delete=models.CASCADE, null=True)


# array(8, 2)
class EnterpriseFactor1(models.Model):
    county_code = models.SmallIntegerField()
    enterprise_residual_factor_r = ArrayField(SmallFloatField(), size=16)
    enterprise_residual_factor_y = ArrayField(SmallFloatField(), size=16)
    practice = models.SmallIntegerField()
    high_risk = models.BooleanField()
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)


class OptionRate(models.Model):
    county_code = models.SmallIntegerField()
    option_rate = SmallFloatField()
    practice = models.SmallIntegerField()
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    commodity_type = models.ForeignKey(CommodityType, on_delete=models.CASCADE)
    insurance_option = models.ForeignKey(InsuranceOption, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)


class UnitDiscount(models.Model):
    unit_discount_id = models.IntegerField()
    coverage_level = SmallFloatField(null=True)
    area_low_qty = SmallFloatField(null=True)
    area_high_qty = SmallFloatField(null=True)
    enterprise_discount_factor = SmallFloatField(null=True)


# Reshape to (8,6)
class UnitDiscount1(models.Model):
    id = SmallFloatField(primary_key=True)
    enterprise_discount_factor = ArrayField(SmallFloatField(), size=48)


class AreaCoverageLevel(models.Model):
    insurance_offer_id = models.IntegerField()
    coverage_level = SmallFloatField()
    area_rate_id = models.IntegerField()

    class Meta:
        indexes = [
            models.Index(fields=['area_rate_id'])
        ]


class AreaRate(models.Model):
    area_rate_id = models.IntegerField()
    price_volatility_factor = SmallFloatField(null=True)
    base_rate = SmallFloatField()
