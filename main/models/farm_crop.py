import math
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import (
    MinValueValidator as MinVal, MaxValueValidator as MaxVal)
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import gettext_lazy as _
from ext.models import (Subcounty, SubcountyAvail, BudgetCrop, FarmCropType,
                        InsCropType, PriceYield, AreaRate, BenchmarkRevenue)
from core.models.premium import Premium
from core.models.indemnity import Indemnity
from .farm_year import FarmYear, BaselineFarmYear
from .market_crop import MarketCrop, BaselineMarketCrop
from . import util


class FarmCrop(models.Model):
    """
    Farm crop-specific data.  A column in the operator input sheet.
    It holds references to the associated market_crop and farm_year models
    for convenience.
    """
    COUNTY = 0
    FARM = 1
    COVERAGE_TYPES = [(0, 'County'), (1, 'Farm'), ]
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
        d['baseline_yield_for_var_rent'] = d['farm_yield']
        d['farm_crop_id'] = farm_crop_id
        d['farm_year_id'] = FarmCrop.objects.get(pk=farm_crop_id).farm_year_id
        d['budget_crop_id'] = budget_crop_id
        d['budget_date'] = bc.budget.created_on
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
        default=1, validators=[MinVal(0.8), MaxVal(1.2)],
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
    ins_practice = models.SmallIntegerField(
        verbose_name='Irrigated?',
        choices=list(FarmYear.IRR_PRACTICE.items()), blank=False)
    ins_practices = ArrayField(models.SmallIntegerField(), null=True)

    # store date for which premiums were computed
    prems_computed_for = models.DateField(null=True)

    # RMA dates computed when the farm crop is created, never changed.
    proj_price_disc_end = models.DateField(null=True)
    harv_price_disc_end = models.DateField(null=True)
    cty_yield_final = models.DateField(null=True)
    # Cached computed value changed if irr status changes
    benchmark_revenue = models.FloatField(null=True)
    yield_factor = models.FloatField(default=1, validators=[MinVal(0), MaxVal(2)],
                                     verbose_name='yield sensititivity factor')

    def __str__(self):
        irr = 'Irrigated' if self.is_irrigated() else 'Non-irrigated'
        return f'{self.farm_crop_type}, {irr}'

    def price_factor(self):
        return self.market_crop.price_factor

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

    def get_benchmark_revenue(self):
        result = BenchmarkRevenue.objects.filter(
            state_id=self.farm_year.state_id, county_code=self.farm_year.county_code,
            crop=(1 if self.farm_crop_type == 1 else
                  2 if self.farm_crop_type in (2, 5) else 3),
            crop_year=self.farm_year.crop_year,
            practice__in=([0, 1] if self.is_irrigated() else [0, 2]))[0]
        return result.benchmark_revenue

    # ------------------------
    # Crop Ins-related methods
    # ------------------------
    def allowed_coverage_types(self):
        covtypes = ([(1, 'Farm (enterprise)')]
                    if AreaRate.objects.filter(
                        state_id=self.farm_year.state_id,
                        county_code=self.farm_year.county_code,
                        crop_id=self.farm_crop_type.ins_crop_id,
                        crop_type_id=self.ins_crop_type_id,
                        practice=self.ins_practice,
                        insurance_plan_id=4).count() == 0
                    else FarmCrop.COVERAGE_TYPES[:])
        covtypes.insert(0, ('', '-'*9))
        return covtypes

    def coverage_type_name(self):
        return (None if self.coverage_type is None else
                dict(FarmCrop.COVERAGE_TYPES)[self.coverage_type])

    def product_type_name(self):
        return (None if self.product_type is None else
                dict(FarmCrop.PRODUCT_TYPES)[self.product_type])

    def ins_practice_choices(self):
        return [(p, FarmYear.IRR_PRACTICE[p]) for p in self.ins_practices]

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

    def update_related_crop_ins_settings(self):
        """
        Ensure that fs beans and dc beans have the same settings
        """
        if self.farm_crop_type_id in (2, 5):
            other_bean_crop = (self.farm_year.farm_crops
                               .filter(farm_crop_type_id__in=[2, 5])
                               .exclude(pk=self.pk))
            if other_bean_crop.count() > 0:
                other_crop = other_bean_crop[0]
                other_crop.coverage_type = self.coverage_type
                other_crop.product_type = self.product_type
                other_crop.base_coverage_level = self.base_coverage_level
                other_crop.sco_use = self.sco_use
                other_crop.eco_level = self.eco_level
                other_crop.prot_factor = self.prot_factor
                other_crop.save(change_related=True)

    # -------------------------------------------------
    # Crop Ins Premium-related methods values in $/acre
    # -------------------------------------------------
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

    def price_period_changed(self):
        """ used to invalidate cached premiums """
        pcf = self.prems_computed_for
        mrd = self.farm_year.get_model_run_date()
        rco = self.proj_price_disc_end
        return pcf is None or pcf < rco <= mrd or mrd < rco <= pcf

    def prem_price_yield_data(self):
        """
        If model run is before price_discovery_end, we use the previous year's
        price volatility factor and the current futures price as projected price
        """
        post_discov = self.farm_year.get_model_run_date() > self.proj_price_disc_end
        py = PriceYield.objects.get(
            crop_year=self.farm_year.crop_year, state_id=self.farm_year.state_id,
            county_code=self.farm_year.county_code,
            crop_id=self.farm_crop_type.ins_crop_id, crop_type_id=self.ins_crop_type_id,
            practice=self.ins_practice)
        exp_yield = py.expected_yield
        proj_price = (py.projected_price if post_discov
                      and py.projected_price is not None else
                      self.harvest_price())
        price_vol = (py.price_volatility_factor if post_discov
                     and py.price_volatility_factor is not None else
                     py.price_volatility_factor_prevyr)
        return price_vol, proj_price, exp_yield

    def set_prems(self):
        """
        Note: price_volatility factor and projected_price are ignored
        by compute_prems if is_post_discovery=True
        """
        price_vol, projected_price, expected_yield = self.prem_price_yield_data()
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
            price_volatility_factor=int(round(price_vol * 100)),
            projected_price=projected_price,
            expected_yield=expected_yield,
            subcounty=None if self.subcounty == '' else self.subcounty, )
        if prems is not None:
            names = 'Farm County SCO ECO'.split()
            self.crop_ins_prems = {key: None if ar is None else ar.tolist()
                                   for key, ar in zip(names, prems[:4])}

    def get_selected_premiums(self):
        if self.crop_ins_prems is None:
            return None
        return self.get_selected_ins_items(self.crop_ins_prems)

    def get_total_premiums(self):
        prems = self.get_selected_premiums()
        if prems is not None:
            return sum((v for v in prems.values() if v is not None))

    # ----------------------------------
    # Crop Ins Indemnity-related methods
    # values in $/acre
    # ----------------------------------
    def indem_price_yield_data(self, pf=1, yf=1):
        """
        Helper for get_indemnities
        """
        mrd = self.farm_year.get_model_run_date()
        pre_discov = mrd <= self.proj_price_disc_end
        pre_harv = mrd <= self.harv_price_disc_end
        pre_cty_yield = mrd <= self.cty_yield_final
        harv_price = self.sens_harvest_price(pf)
        sens_harv_price = harv_price * pf
        py = PriceYield.objects.get(
            crop_year=self.farm_year.crop_year, state_id=self.farm_year.state_id,
            county_code=self.farm_year.county_code,
            crop_id=self.farm_crop_type.ins_crop_id, crop_type_id=self.ins_crop_type_id,
            practice=self.ins_practice)
        exp_yield = py.expected_yield
        sens_cty_exp_yield = (self.market_crop.county_bean_yield(yf)
                              if self.farm_crop_type_id in (2, 5) else
                              self.sens_cty_expected_yield(yf))
        proj_price = (harv_price if pre_discov or py.projected_price is None else
                      py.projected_price)
        harvest_price = (sens_harv_price if pre_harv or py.harvest_price is None else
                         py.harvest_price)
        cty_yield = (sens_cty_exp_yield if pre_cty_yield or py.final_yield is None else
                     py.final_yield)
        return exp_yield, proj_price, harvest_price, cty_yield

    def get_indemnities(self, pf=None, yf=None):
        if pf is None:
            pf = self.price_factor()
        if yf is None:
            yf = self.yield_factor
        data = self.indem_price_yield_data(pf, yf)
        expected_yield, proj_price, harvest_price, cty_yield = data
        indem = Indemnity(
            tayield=self.ta_aph_yield,
            projected_price=proj_price,
            harvest_futures_price=harvest_price,
            rma_cty_expected_yield=expected_yield,
            prot_factor=self.prot_factor,
            farm_expected_yield=self.sens_farm_expected_yield(yf),
            cty_expected_yield=cty_yield)
        indems = indem.compute_indems()
        names = 'Farm County SCO ECO'.split()
        return {key: None if ar is None else ar.tolist()
                for key, ar in zip(names, indems)}

    def get_selected_indemnities(self, pf=None, yf=None):
        if pf is None:
            pf = self.price_factor()
        if yf is None:
            yf = self.yield_factor
        return self.get_selected_ins_items(self.get_indemnities(pf, yf))

    def get_total_indemnities(self, pf=None, yf=None):
        if pf is None:
            pf = self.price_factor()
        if yf is None:
            yf = self.yield_factor
        indems = self.get_selected_indemnities(pf, yf)
        if indems is not None:
            return sum((v for v in indems.values() if v is not None))

    # ----------------------------
    # Yield and Production methods
    # ----------------------------
    def sens_farm_expected_yield(self, yf=None):
        if yf is None:
            yf = self.yield_factor
        if not self.has_budget():
            return self.ta_aph_yield * yf
        mrd = self.farm_year.get_model_run_date()
        yieldfinal = self.farmbudgetcrop.farm_yield_final_on
        sens = (yieldfinal is None or yieldfinal > mrd)
        return self.farmbudgetcrop.farm_yield * (yf if sens else 1)

    def cty_expected_yield(self):
        return (self.farmbudgetcrop.county_yield if self.has_budget()
                else self.ta_aph_yield)

    def sens_cty_expected_yield(self, yf=None):
        if yf is None:
            yf = self.yield_factor
        return self.cty_expected_yield() * yf

    def sens_production_bu(self, yf=None):
        if yf is None:
            yf = self.yield_factor
        return self.planted_acres * self.sens_farm_expected_yield(yf)

    def fut_contracted_bu(self):
        mcacres = self.market_crop.planted_acres()
        return (0 if mcacres == 0 else (self.market_crop.contracted_bu *
                self.planted_acres / mcacres))

    def sens_fut_uncontracted_bu(self, yf=None):
        if yf is None:
            yf = self.yield_factor
        return self.sens_production_bu(yf) - self.fut_contracted_bu()

    def basis_bu_locked(self):
        return self.market_crop.basis_bu_locked

    def sens_basis_uncontracted_bu(self, yf=None):
        if yf is None:
            yf = self.yield_factor
        return self.sens_production_bu(yf) - self.basis_bu_locked()

    # -----------------------------------------------
    # Revenue methods (return values in $ by default)
    # -----------------------------------------------
    def contract_fut_revenue(self):
        return self.fut_contracted_bu() * self.avg_contract_price()

    def pretax_amount(self, pf=None, yf=None, is_cash_flow=False, is_per_acre=False,
                      sprice=None, bprice=None):
        """ returns pretax amount in dollars unless is_per_acre is True """
        if sprice is None and pf is None:
            pf = self.price_factor()
        if yf is None:
            yf = self.yield_factor
        acres = self.planted_acres
        return (0 if acres == 0 else
                self.gross_rev(pf, yf, sprice) /
                (acres if is_per_acre else 1) -
                self.total_cost(pf, yf, is_cash_flow, sprice, bprice) *
                (1 if is_per_acre else acres))

    def gross_rev(self, pf=None, yf=None, sprice=None):
        if sprice is None and pf is None:
            pf = self.price_factor()
        if yf is None:
            yf = self.yield_factor
        return (self.gross_rev_no_title_indem(pf, yf, sprice) +
                (self.gov_pmt_portion(pf, yf, is_per_acre=True) +
                 self.get_total_indemnities()) * self.planted_acres)

    def gross_rev_no_title_indem(self, pf=None, yf=None, is_per_acre=False,
                                 sprice=None):
        if sprice is None and pf is None:
            pf = self.price_factor()
        if yf is None:
            yf = self.yield_factor
        acres = self.planted_acres
        return (0 if acres == 0 else
                self.grain_revenue(pf, yf, sprice) /
                (acres if is_per_acre else 1) +
                (self.farmbudgetcrop.other_gov_pmts +
                 self.farmbudgetcrop.other_revenue) *
                (1 if is_per_acre else acres))

    def noncontract_fut_revenue(self, pf=None, yf=None, sprice=None):
        if sprice is None and pf is None:
            pf = self.price_factor()
        if yf is None:
            yf = self.yield_factor
        result = (
            self.sens_fut_uncontracted_bu(yf) *
            (self.sens_harvest_price(pf) if sprice is None else sprice))
        return result

    def noncontract_basis_revenue(self, yf=None):
        if yf is None:
            yf = self.yield_factor
        return (self.sens_basis_uncontracted_bu(yf) *
                self.assumed_basis_for_new())

    def noncontract_revenue(self, pf=None, yf=None, sprice=None):
        if sprice is None and pf is None:
            pf = self.price_factor()
        if yf is None:
            yf = self.yield_factor
        return (self.noncontract_fut_revenue(yf, pf, sprice) +
                self.noncontract_basis_revenue(yf))

    def frac_rev_excess(self, pf=None, yf=None, sprice=None, bprice=None):
        """ fraction revenue excess or (shortfall) """
        if sprice is None and pf is None:
            pf = self.price_factor()
        if yf is None:
            yf = self.yield_factor
        _, proj_price, harvest_price, _ = self.indem_price_yield_data(pf=pf)
        base_rev = (self.planted_acres *
                    self.farmbudgetcrop.baseline_yield_for_var_rent * proj_price)
        sens_rev = (self.planted_acres * self.sens_farm_expected_yield(yf=yf) *
                    harvest_price)
        result = (0 if base_rev == 0 else (sens_rev - base_rev) / base_rev)
        return result

    def grain_revenue(self, pf=None, yf=None, sprice=None):
        if sprice is None and pf is None:
            pf = self.price_factor()
        if yf is None:
            yf = self.yield_factor
        return (self.contract_fut_revenue() + self.contract_basis_revenue() +
                self.noncontract_fut_revenue(pf, yf, sprice) +
                self.noncontract_basis_revenue(yf))

    def contract_basis_revenue(self):
        return self.basis_bu_locked() * self.avg_locked_basis()

    def gov_pmt_portion(self, pf=None, yf=None, is_per_acre=False):
        return (self.farm_year.calc_gov_pmt(pf, yf, is_per_acre=True) *
                (1 if is_per_acre else self.planted_acres))

    # -----------------------------------------
    # Cost methods in $/acre except where noted
    # -----------------------------------------
    def total_direct_costs(self):
        fbc = self.farmbudgetcrop
        return (fbc.fertilizers + fbc.pesticides + fbc.seed + fbc.drying +
                fbc.storage + self.get_total_premiums() + fbc.other_direct_costs)

    def total_nonland_costs(self):
        fbc = self.farmbudgetcrop
        result = (
            self.total_direct_costs() +
            fbc.machine_hire_lease + fbc.utilities + fbc.machine_repair +
            fbc.fuel_and_oil + fbc.light_vehicle + fbc.machine_depr +
            fbc.labor_and_mgmt + fbc.building_repair_and_rent + fbc.building_depr +
            fbc.insurance + fbc.misc_overhead_costs + fbc.interest_nonland +
            fbc.other_overhead_costs)
        return result

    def yield_adj_to_nonland_costs(self, yf=None):
        """ a fraction """
        if yf is None:
            yf = self.yield_factor
        fbc = self.farmbudgetcrop
        mrd = self.farm_year.get_model_run_date()
        yfo = fbc.farm_yield_final_on
        sens = yfo is None or yfo > mrd
        return (fbc.yield_variability *
                ((yf - 1) if sens else fbc.farm_yield/fbc.baseline_yield_for_var_rent))

    def revenue_based_adj_to_land_rent(self, pf=None, yf=None,
                                       sprice=None, bprice=None):
        """ a fraction """
        if sprice is None and pf is None:
            pf = self.price_factor()
        if yf is None:
            yf = self.yield_factor
        cf = self.farm_year.var_rent_cap_floor_frac
        fv = self.farm_year.frac_var_rent()
        fre = self.frac_rev_excess(pf, yf, sprice, bprice)
        result = fv * math.copysign(cf, fre) if abs(fre) > cf else fre
        return result

    def rented_land_costs(self, pf=None, yf=None, sprice=None, bprice=None):
        """ in dollars per planted acre (landcost=0 for dc soybeans in std. budgets) """
        if sprice is None and pf is None:
            pf = self.price_factor()
        if yf is None:
            yf = self.yield_factor
        # rent cost per planted acre
        rented_costperacre = (self.farmbudgetcrop.rented_land_costs *
                              self.farm_year.total_rented_acres() /
                              self.farm_year.total_farm_acres())
        return (rented_costperacre *
                (1 + self.revenue_based_adj_to_land_rent(pf, yf, sprice, bprice)))

    def owned_land_costs(self):
        return (0 if self.farm_crop_type.is_fac else
                (self.farm_year.total_owned_land_expense() /
                 self.farm_year.total_farm_acres()))

    def land_costs(self, pf=None, yf=None, is_cash_flow=False,
                   sprice=None, bprice=None):
        if sprice is None and pf is None:
            pf = self.price_factor()
        if yf is None:
            yf = self.yield_factor
        return (self.rented_land_costs(pf, yf, sprice, bprice) +
                self.owned_land_costs())

    def total_cost(self, pf=None, yf=None, is_cash_flow=False,
                   sprice=None, bprice=None):
        """ used in sensitivity table """
        if sprice is None and pf is None:
            pf = self.price_factor()
        if yf is None:
            yf = self.yield_factor
        return (self.total_nonland_costs() * (1 + self.yield_adj_to_nonland_costs(yf)) +
                self.land_costs(pf, yf, is_cash_flow, sprice, bprice))

    # -------------
    # Price methods
    # -------------

    def harvest_price(self):
        return self.market_crop.harvest_futures_price_info(price_only=True)

    def sens_harvest_price(self, pf=None):
        return self.market_crop.sens_harvest_price(pf=pf)

    def avg_contract_price(self):
        return self.market_crop.avg_contract_price

    def avg_locked_basis(self):
        return self.market_crop.avg_locked_basis

    def assumed_basis_for_new(self):
        return self.market_crop.assumed_basis_for_new

    def avg_realized_price(self, pf=None, yf=None):
        if pf is None:
            pf = self.price_factor()
        if yf is None:
            yf = self.yield_factor
        bu = self.sens_production_bu(yf)
        return 0 if bu == 0 else self.grain_revenue(pf, yf) / bu

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
        if self.benchmark_revenue is None or util.any_changed(self, 'ins_practice'):
            self.benchmark_revenue = self.get_benchmark_revenue()
        if util.any_changed(self, 'planted_acres'):
            # invalidate memory cached variable
            self.farm_year.totalplantedacres = None
        if ('change_related' not in kwargs and
            util.any_changed(self, 'coverage_type', 'product_type',
                             'base_coverage_level', 'sco_use', 'eco_level',
                             'prot_factor')):
            self.update_related_crop_ins_settings()
        elif 'change_related' in kwargs:
            del kwargs['change_related']
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['farm_crop_type_id']


class BaselineFarmCrop(models.Model):
    farm_crop_type = models.ForeignKey(FarmCropType, on_delete=models.CASCADE)
    market_crop = models.ForeignKey(BaselineMarketCrop,
                                    on_delete=models.CASCADE,
                                    related_name='farm_crops')
    farm_year = models.ForeignKey(BaselineFarmYear, on_delete=models.CASCADE,
                                  related_name='farm_crops')
