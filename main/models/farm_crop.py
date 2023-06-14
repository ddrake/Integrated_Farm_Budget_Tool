from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import (
    MinValueValidator as MinVal, MaxValueValidator as MaxVal)
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import gettext_lazy as _
from ext.models import (Subcounty, SubcountyAvail, BudgetCrop, FarmCropType,
                        InsCropType, PricePrevyear, Price, ExpectedYield)
from core.models.premium import Premium
from core.models.indemnity import Indemnity
from .farm_year import FarmYear, BaselineFarmYear
from .market_crop import MarketCrop, BaselineMarketCrop
from . import util


class FarmCrop(models.Model):
    """
    Farm crop-specific data.  A column in the operator input sheet.
    It holds references to the associated fsa_crop and farm_year models
    for convenience.
    Its name is just the name of its farm_crop_type (TODO: add method)
    We can get its crop insurance type from the farm_crop_type.
    We can infer its crop insurance practice from its is_irrigated
    and its farm_crop_type is_fac properties.
    We (re)compute and store all premiums only if the crop, practice, type or subcounty
    changes (or if the state or county is changed).  A change in user selections,
    e.g. coverage_type or level is just a quick lookup.
    Todo: Change premiums.py so it returns nested lists instead of numpy arrays.
    """
    COUNTY = 0
    FARM = 1
    COVERAGE_TYPES = [(0, 'County (area)'), (1, 'Farm (enterprise)'), ]
    PRODUCT_TYPES = [(0, 'RP'), (1, 'RP-HPE'), (2, 'YP'), ]
    COVERAGE_LEVELS = [
        (.5, '50%'), (.55, '55%'), (.6, '60%'), (.65, '65%'),
        (.7, '70%'), (.75, '75%'), (.8, '80%'), (.85, '85%'), (.9, '90%'), ]
    COVERAGE_LEVELS_ECO = [(.9, '90%'), (.95, '95%'), ]

    @classmethod
    def add_farm_budget_crop(cls, farm_crop_id, budget_crop_id):
        from . import farm_budget_crop as fbc
        fbc.FarmBudgetCrop.objects.filter(
            farm_crop=farm_crop_id).delete()
        bc = BudgetCrop.objects.get(pk=budget_crop_id)
        d = {k: v for k, v in bc.__dict__.items() if k not in ['_state', 'id']}
        d['county_yield'] = d['farm_yield']
        d['farm_crop_id'] = farm_crop_id
        d['farm_year_id'] = FarmCrop.objects.get(pk=farm_crop_id).farm_year_id
        d['budget_crop_id'] = budget_crop_id
        fbc.FarmBudgetCrop.objects.create(**d)

    planted_acres = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(99999)],)
    ta_aph_yield = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(400)], verbose_name="TA APH yield",
        help_text="Trend-adjusted average prodution history yield provided by insurer.")
    adj_yield = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(400)], verbose_name="Adjusted yield",
        help_text="Adjusted yield provided by insurer.")
    rate_yield = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(400)],
        help_text="Rate yield provided by insurer.")
    ye_use = models.BooleanField(
        default=False, verbose_name='use YE?',
        help_text="Use yield exclusion option? (e.g. exclude 2012 yields)")
    ta_use = models.BooleanField(
        default=False, verbose_name='use TA?',
        help_text="Use trend adjustment option? (apply a trend adjustment to yields).")
    subcounty = models.CharField(
        max_length=8, blank=True, verbose_name="risk class", default='',
        choices=[(v[0], v[0]) for v in Subcounty.objects.all().values_list('id')],
        help_text="Primary risk class (subcounty ID) provided by crop insurer")
    # TODO: we should give the user sensible defaults for these during the period
    # when they are required (prior year value for price volatility and board price
    # for projected price) and hide the form fields once they are known.
    coverage_type = models.SmallIntegerField(
        choices=COVERAGE_TYPES, null=True, blank=True,
        help_text="Crop insurance coverage type.")
    product_type = models.SmallIntegerField(
        choices=PRODUCT_TYPES, null=True, blank=True,
        help_text="Crop insurance product type.")
    base_coverage_level = models.FloatField(
        null=True, blank=True, choices=COVERAGE_LEVELS,
        help_text="Coverage level for selected crop insurance product.")
    sco_use = models.BooleanField(
        default=False, verbose_name="add SCO option?",
        help_text="Add Supplemental coverage option to bring coverage level to 86%?")
    eco_level = models.FloatField(
        null=True, blank=True, choices=COVERAGE_LEVELS_ECO,
        verbose_name="ECO level", help_text="Enhanced coverage level")
    prot_factor = models.FloatField(
        default=1, validators=[MinVal(0), MaxVal(1)],
        verbose_name="selected payment factor",
        help_text="Selected payment factor for county premiums/indemnities.")
    farm_crop_type = models.ForeignKey(FarmCropType, on_delete=models.CASCADE)
    market_crop = models.ForeignKey(MarketCrop, on_delete=models.CASCADE,
                                    related_name='farm_crops')
    farm_year = models.ForeignKey(FarmYear, on_delete=models.CASCADE,
                                  related_name='farm_crops')
    crop_ins_prems = models.JSONField(null=True, blank=True)
    ins_crop_type = models.ForeignKey(InsCropType, on_delete=models.CASCADE,
                                      related_name='farm_crop_types')
    # holds currently selected practice
    # TODO: May need to replace the choices for subcounty if this changes.
    # If so, the currently selected subcounty might need to be cleared (if it's
    # not in the updated choices list.
    ins_practice = models.SmallIntegerField(
        verbose_name='Irrigated?',
        choices=list(FarmYear.IRR_PRACTICE.items()), blank=False)
    ins_practices = ArrayField(models.SmallIntegerField(), null=True)

    # Cached portion of gov payment (set by method in FarmYear)
    gov_pmt_portion = models.FloatField(null=True, blank=True)
    prems_computed_for = models.DateField(null=True)

    def __str__(self):
        irr = 'Irrigated' if self.is_irrigated() else 'Non-irrigated'
        return f'{self.farm_crop_type}, {irr}'

    def is_irrigated(self):
        return FarmYear.IRR_PRACTICE[self.ins_practice] == 'Irrigated'

    def allowed_subcounties(self):
        values = SubcountyAvail.objects.filter(
            state_id=self.farm_year.state_id, county_code=self.farm_year.county_code,
            crop_id=self.farm_crop_type.ins_crop,
            croptype_id=self.ins_crop_type,
            practice=self.ins_practice).values_list('subcounty_id')
        return [('', '-'*9)] + [(v[0], v[0]) for v in values]

    def allowed_practices(self):
        return [(prac, FarmYear.IRR_PRACTICE[prac])
                for prac in self.ins_practices]

    # ------------------------------
    # Crop Insurance-related methods
    # ------------------------------
    def coverage_type_name(self):
        return (None if self.coverage_type is None else
                dict(FarmCrop.COVERAGE_TYPES)[self.coverage_type])

    def product_type_name(self):
        return (None if self.product_type is None else
                dict(FarmCrop.PRODUCT_TYPES)[self.product_type])

    def get_crop_ins_prems(self):
        """
        Compute and cache premiums if not set; return cached value.
        """
        if (self.crop_ins_prems is None and
            self.planted_acres > 0 and self.rate_yield > 0 and self.adj_yield > 0
                and self.ta_aph_yield > 0):
            self.set_prems()
            self.prems_computed_for = self.farm_year.get_model_run_date()
            self.save()
        return self.crop_ins_prems

    def rma_discovery_complete_on(self):
        return datetime(self.farm_year.crop_year, 3, 1).date()

    def is_post_discovery_end(self):
        return self.farm_year.get_model_run_date() >= self.rma_discovery_complete_on()

    def price_period_changed(self):
        """ used to invalidate cached premiums """
        pcf = self.prems_computed_for
        mrd = self.farm_year.get_model_run_date()
        rco = self.rma_discovery_complete_on()
        return pcf is None or pcf < rco <= mrd or mrd < rco <= pcf

    def ins_practice_choices(self):
        return [(p, FarmYear.IRR_PRACTICE[p]) for p in self.ins_practices]

    def rma_proj_harv_price(self):
        """ Needed for computing indemnity """
        return (self.get_rma_proj_harv_price() if self.is_post_discovery_end()
                else self.harvest_price())

    def get_rma_proj_harv_price(self):
        return Price.objects.get(
            state_id=self.farm_year.state_id, county_code=self.farm_year.county_code,
            crop_id=self.farm_crop_type.ins_crop_id,
            crop_type_id=self.ins_crop_type_id).projected_price

    def rma_expected_yield(self):
        try:
            return ExpectedYield.objects.get(
                state_id=self.farm_year.state_id,
                county_code=self.farm_year.county_code,
                crop_id=self.farm_crop_type.ins_crop_id,
                crop_type_id=self.ins_crop_type_id).expected_yield
        except ObjectDoesNotExist:
            return None

    def prev_year_price_vol(self):
        """
        Return the default price volatility factor (the previous year's value)
        """
        return PricePrevyear.objects.get(
            state_id=self.farm_year.state_id, county_code=self.farm_year.county_code,
            crop_id=self.farm_crop_type.ins_crop_id,
            crop_type_id=self.ins_crop_type_id).price_volatility_factor

    def set_prems(self):
        """
        Note: price_volatility factor and projected_price are ignored
        by compute_prems if is_post_discovery=True
        """
        p = Premium()
        prems = p.compute_prems(
            state=self.farm_year.state_id,
            county=self.farm_year.county_code,
            crop=self.farm_crop_type.ins_crop_id,
            croptype=self.ins_crop_type_id,
            practice=self.ins_practice,
            rateyield=self.rate_yield,
            adjyield=self.adj_yield,
            tayield=self.ta_aph_yield,
            acres=self.planted_acres,
            tause=self.ta_use,
            yieldexcl=self.ye_use,
            prot_factor=self.prot_factor,
            price_volatility_factor=self.prev_year_price_vol(),
            projected_price=self.harvest_price(),
            subcounty=None if self.subcounty == '' else self.subcounty,
            is_post_discovery=self.is_post_discovery_end(), )
        if prems is not None:
            names = 'Farm County SCO ECO'.split()
            self.crop_ins_prems = {key: None if ar is None else ar.tolist()
                                   for key, ar in zip(names, prems[:4])}

    def get_indemnities(self, pf=None, yf=None):
        if pf is None:
            pf = self.farm_year.price_factor
        if yf is None:
            yf = self.farm_year.yield_factor
        indem = Indemnity(
            self.ta_aph_yield, self.rma_proj_harv_price(), self.harvest_price(),
            self.rma_expected_yield(), self.prot_factor,
            self.farm_expected_yield(), self.cty_expected_yield())
        indems = indem.compute_indems(pf, yf)
        names = 'Farm County SCO ECO'.split()
        return {key: None if ar is None else ar.tolist()
                for key, ar in zip(names, indems)}

    def get_selected_premiums(self):
        if self.crop_ins_prems is None:
            return None
        return self.get_selected_ins_items(self.crop_ins_prems)

    def get_selected_indemnities(self, pf=None, yf=None):
        if pf is None:
            pf = self.farm_year.price_factor
        if yf is None:
            yf = self.farm_year.yield_factor
        return self.get_selected_ins_items(self.get_indemnities(pf, yf))

    def get_selected_ins_items(self, ins_list):
        ct, bcl, pt = self.coverage_type, self.base_coverage_level, self.product_type
        farm, county, sco = ins_list['Farm'], ins_list['County'], ins_list['SCO']
        ecolvl, eco = self.eco_level, ins_list['ECO']
        covtype = 'County' if ct == 0 else 'Farm' if ct == 1 else None
        base = (0 if ct is None or bcl is None or pt is None or
                ct == 0 and county is None or ct == 1 and farm is None else
                ins_list[covtype][
                    int((bcl - (.5 if covtype == 'Farm' else .7))/.05)][pt])
        sco = (0 if ct is None or bcl is None or pt is None or
               ct == 1 and sco is None or not self.sco_use else
               sco[int((bcl - .5)/.05)][pt])
        eco = (0 if ct is None or bcl is None or pt is None or
               ecolvl is None or eco is None else
               eco[int((ecolvl - .9)/.05)][pt])
        return {'base': base, 'sco': sco, 'eco': eco}

    def get_total_premiums(self):
        prems = self.get_selected_premiums()
        if prems is not None:
            return sum((v for v in prems.values() if v is not None))

    def get_total_indemnities(self, pf=None, yf=None):
        if pf is None:
            pf = self.farm_year.price_factor
        if yf is None:
            yf = self.farm_year.yield_factor
        indems = self.get_selected_indemnities(pf, yf)
        if indems is not None:
            return sum((v for v in indems.values() if v is not None))

    # ----------------------------
    # Yield and Production methods
    # ----------------------------
    def farm_expected_yield(self):
        return (self.farmbudgetcrop.farm_yield if self.has_budget()
                else self.ta_aph_yield)

    def sens_farm_expected_yield(self, yf=None):
        if yf is None:
            yf = self.farm_year.yield_factor
        return self.farm_expected_yield() * yf

    def cty_expected_yield(self):
        return (self.farmbudgetcrop.county_yield if self.has_budget()
                else self.ta_aph_yield)

    def sens_cty_expected_yield(self, yf=None):
        if yf is None:
            yf = self.farm_year.yield_factor
        return self.cty_expected_yield() * yf

    def sens_production_bu(self, yf=None):
        if yf is None:
            yf = self.farm_year.yield_factor
        return self.planted_acres * self.sens_farm_expected_yield(yf)

    def fut_contracted_bu(self):
        return (self.market_crop.contracted_bu *
                self.planted_acres / self.market_crop.planted_acres())

    def sens_fut_uncontracted_bu(self, yf=None):
        if yf is None:
            yf = self.farm_year.yield_factor
        return self.sens_production_bu(yf) - self.fut_contracted_bu()

    def basis_bu_locked(self):
        return self.market_crop.basis_bu_locked

    def sens_basis_uncontracted_bu(self, yf=None):
        if yf is None:
            yf = self.farm_year.yield_factor
        return self.sens_production_bu(yf) - self.basis_bu_locked()

    # ---------------
    # Revenue methods
    # ---------------

    def contract_fut_revenue(self):
        return self.fut_contracted_bu() * self.avg_contract_price()

    def pretax_income(self, pf=None, yf=None):
        if pf is None:
            pf = self.farm_year.price_factor
        if yf is None:
            yf = self.farm_year.yield_factor
        pass

    def pretax_cash_flow(self, pf=None, yf=None):
        if pf is None:
            pf = self.farm_year.price_factor
        if yf is None:
            yf = self.farm_year.yield_factor
        pass

    def gross_rev_no_title_indem(self, pf=None, yf=None):
        if pf is None:
            pf = self.farm_year.price_factor
        if yf is None:
            yf = self.farm_year.yield_factor
        pass

    def total_cost(self, pf=None, yf=None):
        if pf is None:
            pf = self.farm_year.price_factor
        if yf is None:
            yf = self.farm_year.yield_factor
        pass

    def contract_basis_revenue(self):
        return self.basis_bu_locked() * self.avg_locked_basis()

    def noncontract_fut_revenue(self, pf=None, yf=None):
        if pf is None:
            pf = self.farm_year.price_factor
        if yf is None:
            yf = self.farm_year.yield_factor
        return (self.sens_fut_uncontracted_bu(yf) *
                self.sens_harvest_price(pf))

    def noncontract_basis_revenue(self, yf=None):
        if yf is None:
            yf = self.farm_year.yield_factor
        return (self.sens_basis_uncontracted_bu(yf) *
                self.assumed_basis_for_new())

    def noncontract_revenue(self, pf=None, yf=None):
        if pf is None:
            pf = self.farm_year.price_factor
        if yf is None:
            yf = self.farm_year.yield_factor
        return (self.noncontract_fut_revenue(yf, pf) +
                self.noncontract_basis_revenue(yf))

    def frac_rev_excess(self):
        """ fraction revenue excess or (shortfall) """
        base_rev = self.noncontract_revenue(pf=1, yf=1)
        return (0 if base_rev == 0 else
                (self.noncontract_revenue() - base_rev) / base_rev)

    def grain_revenue(self, pf=None, yf=None):
        if pf is None:
            pf = self.farm_year.price_factor
        if yf is None:
            yf = self.farm_year.yield_factor
        return (self.contract_fut_revenue() + self.contract_basis_revenue() +
                self.noncontract_fut_revenue(pf, yf) +
                self.noncontract_basis_revenue(yf))

    def avg_realized_price(self, pf=None, yf=None):
        if pf is None:
            pf = self.farm_year.price_factor
        if yf is None:
            yf = self.farm_year.yield_factor
        return self.grain_revenue(pf, yf) / self.sens_production_bu(yf)

    # -------------
    # Price methods
    # -------------

    def harvest_price(self):
        return self.market_crop.harvest_futures_price_info(price_only=True)

    def sens_harvest_price(self, pf=None):
        if pf is None:
            pf = self.farm_year.price_factor
        return self.harvest_price() * pf

    def avg_contract_price(self):
        return self.market_crop.avg_contract_price

    def avg_locked_basis(self):
        return self.market_crop.avg_locked_basis

    def assumed_basis_for_new(self):
        return self.market_crop.assumed_basis_for_new

    # --------------
    # Budget methods
    # --------------
    def get_budget_crops(self):
        return [(it.id, str(it)) for it in
                BudgetCrop.objects.filter(farm_crop_type_id=self.farm_crop_type,
                                          is_irr=self.is_irrigated())]

    def has_budget(self):
        try:
            self.farmbudgetcrop
            return True
        except ObjectDoesNotExist:
            return False

    # ---------------------
    # Validation and saving
    # ---------------------
    def clean(self):
        fsa_crop_has_arcco = (self.market_crop.fsa_crop.arcco_base_acres > 0)
        if self.sco_use and fsa_crop_has_arcco:
            raise ValidationError({'sco_use': _(
                "ARC-CO base acres must be zero if SCO is set for related farm crop")})

    def save(self, *args, **kwargs):
        # invalidate cached premiums upon changes to key fields
        if util.any_changed(self, 'ins_practice', 'rate_yield', 'adj_yield',
                            'ta_aph_yield', 'planted_acres', 'ta_use', 'ye_use',
                            'prot_factor', 'subcounty') or self.price_period_changed():
            self.crop_ins_prems = None
            self.prems_computed_for = None
        super().save(*args, **kwargs)


class BaselineFarmCrop(models.Model):
    farm_crop_type = models.ForeignKey(FarmCropType, on_delete=models.CASCADE)
    market_crop = models.ForeignKey(BaselineMarketCrop,
                                    on_delete=models.CASCADE,
                                    related_name='farm_crops')
    farm_year = models.ForeignKey(BaselineFarmYear, on_delete=models.CASCADE,
                                  related_name='farm_crops')
