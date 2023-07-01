from datetime import datetime
from django.core.exceptions import ValidationError
from django.core.validators import (MinValueValidator as MinVal,
                                    MaxValueValidator as MaxVal)
from django.db import models
from django.utils.translation import gettext_lazy as _
from ext.models import ReferencePrices, FsaCropType, PriceYield
from core.models.gov_pmt import GovPmt
from .farm_year import FarmYear, BaselineFarmYear


def get_current_year():
    return datetime.today().year


def any_changed(instance, *fields):
    """
    Check an instance to see if the values of any of the listed fields changed.
    """
    if not instance.pk:
        return False
    dbinst = instance.__class__._default_manager.get(pk=instance.pk)
    return any((getattr(dbinst, field) != getattr(instance, field)
                for field in fields))


class FsaCrop(models.Model):
    """
    Priced crop-specific operator input data.  A FsaCrop has many FarmCrops so we
    should be able to get totals pretty easily.
    """
    plc_base_acres = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(99999)],
        verbose_name="Base acres in PLC")
    arcco_base_acres = models.FloatField(
        default=0,  validators=[MinVal(0), MaxVal(99999)],
        verbose_name="Base acres in ARC-CO")
    plc_yield = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(400)],
        verbose_name="farm avg. PLC yield",
        help_text="Weighted average PLC yield for farm in bushels per acre.")
    farm_year = models.ForeignKey(FarmYear, on_delete=models.CASCADE,
                                  related_name='fsa_crops')
    fsa_crop_type = models.ForeignKey(FsaCropType, on_delete=models.CASCADE)

    def planted_acres(self):
        return sum((mc.planted_acres() for mc in self.market_crops.all()))

    def farm_crops(self):
        return [fc for mc in self.market_crops.all() for fc in mc.farm_crops.all()]

    def price_factor(self):
        pa = self.planted_acres()
        return (1 if pa == 0 else
                sum((mc.price_factor * mc.planted_acres()
                    for mc in self.market_crops.all())) / pa)

    def yield_factor(self):
        pa = self.planted_acres()
        return (1 if pa == 0 else
                sum((fc.yield_factor * fc.planted_acres
                    for fc in self.farm_crops())) / pa)

    def cty_expected_yield(self, yf=None):
        """
        Get weighted average of farm crop county yields
        TODO: This needs to check model run date and use RMA final yields
        once they are available (and ignore any yield factor).
        """
        if yf is None:
            yf = self.yield_factor()
        farm_crop = self.farm_crops()[0]
        if self.farm_year.get_model_run_date() > farm_crop.cty_yield_final:
            py = PriceYield.objects.get(
                crop_year=self.farm_year.crop_year, state_id=self.farm_year.state_id,
                county_code=self.farm_year.county_code,
                crop_id=farm_crop.farm_crop_type.ins_crop_id,
                crop_type_id=farm_crop.ins_crop_type_id,
                practice=farm_crop.ins_practice)
            if py.final_yield is not None:
                return py.final_yield
        pairs = ((fc.planted_acres, fc.sens_cty_expected_yield(yf) *
                  fc.planted_acres) for fc in self.farm_crops())
        acres, weighted = zip(*pairs)
        totacres = sum(acres)
        return 0 if totacres == 0 else sum(weighted) / totacres

    def benchmark_revenue(self):
        pairs = ((fc.planted_acres, fc.benchmark_revenue * fc.planted_acres)
                 for fc in self.farm_crops())
        acres, weighted = zip(*pairs)
        totacres = sum(acres)
        return 0 if totacres == 0 else sum(weighted) / totacres

    def gov_payment(self, sens_mya_price, yf=None):
        if yf is None:
            yf = self.yield_factor()
        rp = ReferencePrices.objects.get(
            fsa_crop_type_id=self.fsa_crop_type_id,
            crop_year=self.farm_year.crop_year)
        gp = GovPmt(plc_base_acres=self.plc_base_acres,
                    arcco_base_acres=self.arcco_base_acres, plc_yield=self.plc_yield,
                    estimated_county_yield=self.cty_expected_yield(yf=yf),
                    effective_ref_price=rp.effective_ref_price,
                    natl_loan_rate=rp.natl_loan_rate, sens_mya_price=sens_mya_price,
                    benchmark_revenue=self.benchmark_revenue())
        return gp.prog_pmt_pre_sequest(yf)

    def clean(self):
        field_crop_sco_use = any((fc.sco_use for mc in self.market_crops.all()
                                  for fc in mc.farm_crops.all()))
        if self.arcco_base_acres > 0 and field_crop_sco_use:
            raise ValidationError({'arcco_base_acres': _(
                "ARC-CO base acres must be zero if SCO is set for related farm crop")})

    def __str__(self):
        return f'{self.fsa_crop_type}'

    class Meta:
        ordering = ['fsa_crop_type_id']


class BaselineFsaCrop(models.Model):
    farm_year = models.ForeignKey(BaselineFarmYear, on_delete=models.CASCADE)
    fsa_crop_type = models.ForeignKey(FsaCropType, on_delete=models.CASCADE)
