import numpy as np
from datetime import datetime
from django.core.exceptions import ValidationError
from django.core.validators import (MinValueValidator as MinVal,
                                    MaxValueValidator as MaxVal)
from django.db import models
from django.utils.translation import gettext_lazy as _
from ext.models import (FsaCropType, MyaPreEstimate, MyaPost,
                        BenchmarkRevenue)
from core.models.gov_pmt import GovPmt
from .farm_year import FarmYear
from .util import scal


def get_current_year():
    return datetime.today().year


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
    effective_ref_price = models.FloatField(null=True)
    natl_loan_rate = models.FloatField(null=True)

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
        """ a default yield_factor """
        pa = self.planted_acres()
        return (1 if pa == 0 else
                sum(((fc.farmbudgetcrop.yield_factor if fc.has_budget() else 1) *
                     fc.planted_acres
                    for fc in self.farm_crops())) / pa)

    def cty_expected_yield(self, yf=None):
        """
        Get weighted average of farm crop county yields, along with final status
        Note: fc.sens_cty_expected_yield(yf) considers RMA final yields
        """
        if yf is None:
            yf = self.yield_factor()
        if len(self.farm_crops()) == 0:
            return (0 if scal(yf) else np.zeros_like(yf))
        yield_info = [fc.sens_cty_expected_yield(yf) for fc in self.farm_crops()]
        is_rma_final = len(yield_info) > 0 and all((yi[1] for yi in yield_info))
        if is_rma_final:
            return yield_info[0][0], is_rma_final

        acres = [fc.planted_acres for fc in self.farm_crops()]
        pairs = list(zip(acres, [yi[0] for yi in yield_info]))
        if scal(yf):
            pairs = [p for p in pairs if p != (0, 0)]
        else:
            pairs = [p for p in pairs if p[0] != 0 or not np.all(p[1]) == 0]
        if len(pairs) == 0:
            return (0 if scal(yf) else np.zeros_like(yf)), is_rma_final
        if len(pairs) == 1:
            return pairs[0][1], is_rma_final
        acres, weight = zip(*((ac, ac*yld) for ac, yld in pairs))
        totacres = sum(acres)
        if scal(yf):
            return (0 if totacres == 0 else sum(weight) / totacres), is_rma_final
        else:
            return (np.zeros_like(yf) if totacres == 0 else
                    sum(weight) / totacres), is_rma_final

    def is_irrigated(self):
        pairs = [(fc.is_irrigated(), fc.planted_acres) for fc in self.farm_crops()]
        return (False if max((pr[1] for pr in pairs)) == 0 else
                sorted(pairs, key=lambda p: p[1]*10+(0 if p[0] else 1),
                       reverse=True)[0][0])

    def benchmark_revenue(self, revenue_only=False):
        result = BenchmarkRevenue.objects.filter(
            state_id=self.farm_year.state_id, county_code=self.farm_year.county_code,
            crop=self.fsa_crop_type_id,
            crop_year=self.farm_year.crop_year,
            practice__in=([0, 1] if self.is_irrigated() else [0, 2]))[0]
        return result.benchmark_revenue if revenue_only else result

    def sens_mya_price(self, pf=None):
        mrd = self.farm_year.get_model_run_date()
        if pf is None:
            pf = self.price_factor()
        return (MyaPreEstimate.get_mya_pre_estimate(
            self.farm_year.crop_year, mrd, self.fsa_crop_type_id, pf=pf)
            if mrd < self.farm_year.wasde_first_mya_release_on()
            else MyaPost.get_mya_post_estimate(
                self.farm_year.crop_year, mrd, self.fsa_crop_type_id, pf=pf))

    def gov_payment(self, sens_mya_price=None, cty_yield=None):
        """
        sens_mya_price is array(np), cty_yield is array(ny)
        """
        if sens_mya_price is None:
            sens_mya_price = self.sens_mya_price()
        if cty_yield is None:
            cty_yield = self.cty_expected_yield()[0]
        gp = GovPmt(plc_base_acres=self.plc_base_acres,
                    arcco_base_acres=self.arcco_base_acres, plc_yield=self.plc_yield,
                    estimated_county_yield=cty_yield,
                    effective_ref_price=self.effective_ref_price,
                    natl_loan_rate=self.natl_loan_rate, sens_mya_price=sens_mya_price,
                    benchmark_revenue=self.benchmark_revenue(revenue_only=True))
        return gp.prog_pmt_pre_sequest()

    def clean(self):
        field_crop_sco_use = any((fc.sco_use for fc in self.farm_crops()))
        if self.arcco_base_acres > 0 and field_crop_sco_use:
            raise ValidationError({'arcco_base_acres': _(
                "ARC-CO base acres must be zero if SCO is set for related farm crop")})
        if (self.arcco_base_acres > 0 and
                not any((fc.has_budget() for fc in self.farm_crops))):
            raise ValidationError({'arcco_base_acres': _(
                "County yield required. ARC-CO Base acres can be set only " +
                "after selecting a budget in the 'Crop Acreage' form.")})

    def __str__(self):
        return f'{self.fsa_crop_type}'

    class Meta:
        ordering = ['fsa_crop_type_id']
