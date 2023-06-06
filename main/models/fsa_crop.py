from datetime import datetime
from django.core.exceptions import ValidationError
from django.core.validators import (MinValueValidator as MinVal,
                                    MaxValueValidator as MaxVal)
from django.db import models
from django.utils.translation import gettext_lazy as _
from ext.models import ReferencePrices, FsaCropType
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

    def estimated_county_yield(self):
        """
        Needed for gov_pmt.
        Get weighted average of market crop county yields
        """
        mcdata = [(mc.planted_acres(), mc.estimated_county_yield())
                  for mc in self.market_crops.all()]
        acres, _ = zip(*mcdata)
        if sum(acres) == 0:
            return 0
        return sum((ac*yld for ac, yld in mcdata)) / sum(acres)

    def planted_acres(self):
        return sum((mc.planted_acres() for mc in self.market_crops.all()))

    def is_irrigated(self):
        irr_acres = sum((mc.planted_acres() * (1 if mc.is_irrigated() else 0)
                         for mc in self.market_crops.all()))
        return irr_acres > self.planted_acres() / 2

    def gov_payment(self, sens_mya_price, priced_on, pf=1, yf=1):
        rp = ReferencePrices.objects.get(
            fsa_crop_type_id=self.fsa_crop_type_id,
            crop_year=self.farm_year.crop_year)
        gp = GovPmt(
            self.farm_year.crop_year, self.farm_year.state.id,
            self.farm_year.county_code, self.fsa_crop_type_id,
            self.is_irrigated(), self.plc_base_acres,
            self.arcco_base_acres, self.plc_yield, self.estimated_county_yield(),
            rp.effective_ref_price, rp.natl_loan_rate, sens_mya_price)
        return gp.prog_pmt_pre_sequest(pf, yf)

    def harvest_futures_price(self, priced_on, pf=1):
        """
        Since a farmer could have both winter and spring wheat, with different
        prices, we need some kind of average of market prices here.  A simple
        average should do for now.
        """
        prices = [p.harvest_futures_price_info(priced_on, price_only=True)
                  for p in self.market_crops.all()]
        return sum(prices)/len(prices) * pf

    def clean(self):
        field_crop_sco_use = any((fc.sco_use for mc in self.market_crops.all()
                                  for fc in mc.farm_crops.all()))
        if self.arcco_base_acres > 0 and field_crop_sco_use:
            raise ValidationError({'arcco_base_acres': _(
                "ARC-CO base acres must be zero if SCO is set for related farm crop")})

    def __str__(self):
        return f'{self.fsa_crop_type}'


class BaselineFsaCrop(models.Model):
    farm_year = models.ForeignKey(BaselineFarmYear, on_delete=models.CASCADE)
    fsa_crop_type = models.ForeignKey(FsaCropType, on_delete=models.CASCADE)
