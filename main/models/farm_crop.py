from datetime import datetime
import numpy as np
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import (
    MinValueValidator as MinVal, MaxValueValidator as MaxVal)
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import gettext_lazy as _
from ext.models import (Subcounty, SubcountyAvail, FarmCropType, InsCropType,
                        PriceYield, AreaRate, State, Budget, BudgetCrop,
                        get_budget_crop_description, ProjDiscoveryPrices,
                        HarvDiscoveryPrices)
from core.models.premium import Premium
from core.models.indemnity import Indemnity
from .farm_year import FarmYear
from .market_crop import MarketCrop
from .util import any_changed, scal, one_like, zero_like


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

    @staticmethod
    def add_farm_budget_crop(farm_crop_id, budget_crop_id):
        FarmBudgetCrop.objects.filter(
            farm_crop=farm_crop_id).delete()
        bc = BudgetCrop.objects.get(pk=budget_crop_id)
        d = {k: v for k, v in bc.__dict__.items() if k not in ['_state', 'id']}
        d['county_yield'] = d['farm_yield']
        d['baseline_yield_for_var_rent'] = d['farm_yield']
        d['farm_crop_id'] = farm_crop_id
        d['farm_year_id'] = FarmCrop.objects.get(pk=farm_crop_id).farm_year_id
        d['budget_crop_id'] = budget_crop_id
        d['budget_date'] = bc.budget.created_on
        FarmBudgetCrop.objects.create(**d)

    @staticmethod
    def delete_farm_budget_crop(farm_crop_id):
        FarmBudgetCrop.objects.filter(
            farm_crop=farm_crop_id)[0].delete()

    planted_acres = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(99999)],)
    appr_yield = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(400)], verbose_name="Approved yield",
        help_text="Approved yield provided by insurer, based on selections of YE/TA.")
    adj_yield = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(400)], verbose_name="Adjusted yield",
        help_text="Adjusted yield provided by insurer.")
    rate_yield = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(400)],
        help_text="Rate yield provided by insurer.")
    ye = models.BooleanField(
        default=False, verbose_name='use YE?',
        help_text="Use yield exclusion option? (e.g. exclude 2012 yields)")
    ta = models.BooleanField(
        default=False, verbose_name='use TA?',
        help_text="Use trend adjustment option? (apply a trend adjustment to yields).")
    ql = models.BooleanField(
        default=False, verbose_name='use QL?',
        help_text="Apply quality loss option?")
    ya = models.BooleanField(
        default=False, verbose_name='use YA?',
        help_text="Apply yield averaging option?")
    yc = models.BooleanField(
        default=False, verbose_name='use YC?',
        help_text="Apply yield cup option?")
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
        default=1,
        validators=[
            MinVal(0.8, message="Ensure this value is greater than or equal to 80"),
            MaxVal(1.2, message="Ensure this value is less than or equal to 120")],
        verbose_name="selected payment factor",
        help_text="Selected percent payment factor for county premiums/indemnities.")
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
    proj_price_disc_start = models.DateField(null=True)
    proj_price_disc_end = models.DateField(null=True)
    harv_price_disc_start = models.DateField(null=True)
    harv_price_disc_end = models.DateField(null=True)
    cty_yield_final = models.DateField(null=True)

    def __init__(self, *args, **kwargs):
        """
        Cache results of expensive functions during request which have a single
        return point.
        The method indem_price_yield_data_scal() is called by both
        premium (pf=None, yf=None) and
        indemnity (pf=array, yf=array) in the context of sensitivity tables
        so we must cache vector and scalar results separately.
        """
        self.has_budget_mem = None
        self.indem_price_yield_data_scal_mem = None
        self.indem_price_yield_data_vec_mem = None
        self.sens_cty_expected_yield_mem = None

        super().__init__(*args, **kwargs)

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

    def is_beans(self):
        return self.farm_crop_type_id in (2, 5)

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
        def get_item(ar, lvl, pt):
            if len(ar.shape) == 2:
                # prems or indemnities for array(lvl, pt)
                return ar[lvl, pt]
            else:
                # prems or indemnities for array(pf, yf, lvl, pt)
                #    or array(pf, yf, bf, lvl, pt)
                return ar[..., lvl, pt]

        if ins_list is None:
            return None
        ct, bcl, pt = self.coverage_type, self.base_coverage_level, self.product_type
        farm, county, sco = ins_list['Farm'], ins_list['County'], ins_list['SCO']
        ecolvl, eco = self.eco_level, ins_list['ECO']
        covtype, basearray = (('County', county * self.prot_factor) if ct == 0 else
                              ('Farm', farm) if ct == 1 else (None, None))
        farm0 = farm[..., 0, 0]  # just used to size zero arrays
        base = (zero_like(farm0) if ct is None or bcl is None or pt is None or
                ct == 0 and county is None or ct == 1 and farm is None else
                get_item(basearray,
                         int(round((bcl - (.5 if covtype == 'Farm' else .7))/.05)),
                         pt))
        sco = (zero_like(farm0) if ct is None or bcl is None or pt is None or
               ct == 1 and sco is None or not self.sco_use else
               get_item(sco, int(round((bcl - .5)/.05)), pt))
        eco = (zero_like(farm0) if ct is None or bcl is None or pt is None or
               ecolvl is None or eco is None else
               get_item(eco, int(round((ecolvl - .9)/.05)), pt))
        return {'base': base, 'sco': sco, 'eco': eco}

    def update_related_crop_ins_settings(self):
        """
        Ensure that fs beans and dc beans have the same settings
        """
        if self.is_beans():
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
    def old_farm_year(self):
        return self.farm_year.crop_year < datetime.now().year

    def get_total_premiums(self, selected_prems=None):
        if selected_prems is None:
            selected_prems = self.get_selected_premiums()
        return sum((v for v in selected_prems.values() if v is not None))

    def get_selected_premiums(self):
        prems = self.get_crop_ins_prems()
        return ({'base': 0, 'sco': 0, 'eco': 0} if prems is None else
                self.get_selected_ins_items(prems))

    def get_crop_ins_prems(self):
        """
        Compute and save premiums; return computed value.
        Note: We're not trying to cache these except to have premiums once the crop year
        is over.
        """
        if not self.old_farm_year():
            self.set_prems()
            self.prems_computed_for = self.farm_year.get_model_run_date()
            self.save(no_check=True)
        # handle case when premiums can't be computed because key data is missing.
        return (None if self.crop_ins_prems is None else
                {k: np.array(v) for k, v in self.crop_ins_prems.items()})

    def set_prems(self):
        """
        Note: price_volatility factor and projected_price are ignored
        by compute_prems if is_post_discovery=True
        """
        if (self.planted_acres == 0 or self.rate_yield == 0 or self.adj_yield == 0 or
                self.appr_yield == 0):
            self.crop_ins_prems = None
            return

        d = self.indem_price_yield_data()
        price_vol, projected_price, expected_yield = d['pv'][0], d['pp'][0], d['ey'][0]
        p = Premium()
        prems = p.compute_prems(
            state=self.farm_year.state_id,
            county=self.farm_year.county_code,
            crop=self.farm_crop_type.ins_crop_id,
            croptype=self.ins_crop_type_id,
            practice=self.ins_practice,
            rateyield=self.rate_yield,
            adjyield=self.adj_yield,
            appryield=self.appr_yield,
            acres=self.planted_acres,
            ql=self.ql,
            ta=self.ta,
            ya=self.ya,
            yc=self.yc,
            ye=self.ye,
            price_volatility_factor=int(round(price_vol * 100)),
            projected_price=projected_price,
            expected_yield=expected_yield,
            subcounty=None if self.subcounty == '' else self.subcounty, )
        if prems is not None:
            names = 'Farm County SCO ECO'.split()
            self.crop_ins_prems = {key: None if ar is None else ar.tolist()
                                   for key, ar in zip(names, prems[:4])}

    # ----------------------------------
    # Crop Ins Indemnity-related methods
    # values in $/acre
    # ----------------------------------
    def indem_price_yield_data(self, pf=None, yf=None):
        """
        Returns a dict where some values may be scalar or array(np, ny)
        Used by budget, sensitivity, listview
        Since this method is called with pf=None, yf=None for crop_ins
        for sensitivity tables, then called with pf, yf arrays for indemnity,
        we cache scalar and vector values separately.
        """
        if (scal(pf) and self.indem_price_yield_data_scal_mem is not None):
            return self.indem_price_yield_data_scal_mem
        elif (not scal(pf) and self.indem_price_yield_data_vec_mem is not None):
            return self.indem_price_yield_data_vec_mem
        else:
            crop_year = self.farm_year.crop_year
            state_id = self.farm_year.state_id
            county_code = self.farm_year.county_code
            crop_id = self.farm_crop_type.ins_crop_id
            crop_type_id = self.ins_crop_type_id
            practice = self.ins_practice
            market_crop_type_id = self.market_crop.market_crop_type_id
            py = PriceYield.objects.get(
                crop_year=crop_year, state_id=state_id, county_code=county_code,
                crop_id=crop_id, crop_type_id=crop_type_id, practice=practice)
            mrd = self.farm_year.get_model_run_date()
            # projected price discovery
            pre_proj_discov = mrd <= self.proj_price_disc_start
            post_proj_discov = (py.projected_price is not None and
                                mrd >= self.proj_price_disc_end)

            # harvest price discovery
            pre_harv_discov = mrd <= self.harv_price_disc_start
            post_harv_discov = (py.harvest_price is not None and
                                mrd >= self.harv_price_disc_end)

            proj_price_final, harvest_price_final = False, False
            if pre_proj_discov:
                proj_price = self.harvest_price()
                price_vol = py.price_volatility_factor_prevyr
            elif post_proj_discov:
                proj_price = py.projected_price
                price_vol = py.price_volatility_factor
                proj_price_final = True
            else:
                proj_price = ProjDiscoveryPrices.avg_proj_price(
                    crop_year, state_id, county_code, market_crop_type_id,
                    min(mrd, self.proj_price_disc_end))
                price_vol = py.price_volatility_factor_prevyr

            if pre_harv_discov:
                harvest_price = self.sens_harvest_price(pf)
            elif post_harv_discov:
                harvest_price = py.harvest_price
                harvest_price_final = True
            else:
                harvest_price = HarvDiscoveryPrices.avg_harv_price(
                    crop_year, state_id, county_code, market_crop_type_id,
                    min(mrd, self.harv_price_disc_end))
            if not scal(pf) and scal(harvest_price):
                harvest_price *= np.ones_like(pf)

            exp_yield = py.expected_yield
            # scalar or 1d array, bool
            sens_cty, is_rma_final = self.sens_cty_expected_yield(yf)
            sens_cty_exp_yield = (
                self.market_crop.county_bean_yield(yf)
                if self.is_beans() and not is_rma_final else sens_cty)
            result = (
                {'ey': [exp_yield, True],
                 'pp': [proj_price, proj_price_final],
                 'pv': [price_vol, proj_price_final],
                 'hp': [harvest_price, harvest_price_final],
                 'cy': [sens_cty_exp_yield, is_rma_final]})

            if scal(pf):
                self.indem_price_yield_data_scal_mem = result
            else:
                self.indem_price_yield_data_vec_mem = result
        return result

    def get_indemnities(self, pf=None, yf=None):
        """ scalar or 2d array """
        data = self.indem_price_yield_data(pf=pf, yf=yf)
        indem = Indemnity(
            appryield=self.appr_yield,
            projected_price=data['pp'][0],
            # sensitized harvest price (scalar or 1d array)
            harvest_futures_price=data['hp'][0],
            rma_cty_expected_yield=data['ey'][0],
            # sensitized yields (scalars or 1d arrays)
            farm_expected_yield=self.sens_farm_expected_yield(yf),
            cty_expected_yield=data['cy'][0])
        indems = indem.compute_indems()
        names = 'Farm County SCO ECO'.split()
        return {key: None if ar is None else ar
                for key, ar in zip(names, indems)}

    def get_selected_indemnities(self, pf=None, yf=None):
        """ scalar or array(np, ny) """
        return self.get_selected_ins_items(self.get_indemnities(pf, yf))

    def get_total_indemnities(self, pf=None, yf=None):
        """ scalar or array(np, ny) used by both budget and sensitivity """
        if not self.has_budget():
            return (0 if scal(pf) else np.zeros((len(pf), len(yf))))
        indems = self.get_selected_indemnities(pf, yf)
        if indems is not None:
            return sum((v for v in indems.values() if v is not None))

    # ----------------------------
    # Yield and Production methods
    # ----------------------------
    # These should all check for a budget because they may be called from market crop.
    # They should also be defensive with yf because they could be called from a view.
    def farm_expected_yield(self):
        """ non-sensitized expected yield used by key data """
        return 0 if not self.has_budget() else self.farmbudgetcrop.farm_yield

    def sens_farm_expected_yield(self, yf=None):
        """ scalar or array(ny) used by budget and sensitivity """
        if not self.has_budget():
            return zero_like(yf)
        if yf is None:
            yf = self.farmbudgetcrop.yield_factor
        yieldfinal = self.farmbudgetcrop.is_farm_yield_final
        farmyield = self.farmbudgetcrop.farm_yield
        return farmyield * (one_like(yf) if yieldfinal else yf)

    def sens_cty_expected_yield(self, yf=None):
        """
        scalar or array(ny) used by budget and sensitivity
        1. If the RMA final county yield is available, use it.
        2. If the county_yield in the budget has been flagged as final, use that
        3. Otherwise return the sensitized budget county_yield
        This needs to do the budget check because it's called from get_indemnities
        """
        if self.sens_cty_expected_yield_mem is not None:
            return self.sens_cty_expected_yield_mem
        else:
            is_rma_final = False
            if not self.has_budget():
                result = zero_like(yf)
            else:
                if yf is None:
                    yf = self.farmbudgetcrop.yield_factor
                # we need this result as a fallback in case we're after the
                # release date, but the data hasn't been integrated yet.
                yieldfinal = self.farmbudgetcrop.is_farm_yield_final
                ctyyield = self.farmbudgetcrop.county_yield
                result = ctyyield * (one_like(yf) if yieldfinal else yf)
                if self.farm_year.get_model_run_date() > self.cty_yield_final:
                    py = PriceYield.objects.get(
                        crop_year=self.farm_year.crop_year,
                        state_id=self.farm_year.state_id,
                        county_code=self.farm_year.county_code,
                        crop_id=self.farm_crop_type.ins_crop_id,
                        crop_type_id=self.ins_crop_type_id,
                        practice=self.ins_practice)
                    if py.final_yield is not None:
                        result = py.final_yield * one_like(yf)
                        is_rma_final = True
            self.sens_cty_expected_yield_mem = result, is_rma_final
            return result, is_rma_final

    def sens_production_bu(self, yf=None):
        """ scalar or 1d array """
        if not self.has_budget():
            return zero_like(yf)
        return self.planted_acres * self.sens_farm_expected_yield(yf)

    def fut_contracted_bu(self, yf=None):
        """ apportion based on fraction of market crop production """
        if not self.has_budget():
            return zero_like(yf)
        if yf is None:
            yf = self.farmbudgetcrop.yield_factor
        return (self.market_crop.production_frac_for_farm_crop(self, yf) *
                self.market_crop.futures_contracted_bu())

    def basis_contracted_bu(self, yf=None):
        """ apportion based on fraction of market crop production """
        if not self.has_budget():
            return zero_like(yf)
        if yf is None:
            yf = self.farmbudgetcrop.yield_factor
        return (self.market_crop.production_frac_for_farm_crop(self, yf) *
                self.market_crop.basis_contracted_bu())

    def sens_fut_uncontracted_bu(self, yf=None):
        if not self.has_budget():
            return zero_like(yf)
        return self.sens_production_bu(yf) - self.fut_contracted_bu(yf)

    def sens_basis_uncontracted_bu(self, yf=None):
        if not self.has_budget():
            return zero_like(yf)
        return self.sens_production_bu(yf) - self.basis_contracted_bu(yf)

    # -----------------------------------------------
    # Revenue methods (return values in $ by default)
    # -----------------------------------------------
    def gross_rev_no_title_indem(self, pf=None, yf=None, bf=None):
        """ array(np, ny, nb) or array(np, ny) used only by sensitivity """
        acres = self.planted_acres
        if not self.has_budget() or acres == 0:
            if bf is None:
                return np.zeros((len(pf), len(yf)))
            else:
                return np.zeros((len(pf), len(yf), len(bf)))
        return (self.grain_revenue(pf=pf, yf=yf, bf=bf) +
                (self.farmbudgetcrop.other_gov_pmts +
                 self.farmbudgetcrop.other_revenue) * acres)

    def contract_fut_revenue(self, yf=None):
        return self.fut_contracted_bu(yf) * self.avg_futures_contract_price()

    def contract_basis_revenue(self, yf=None):
        return self.basis_contracted_bu(yf) * self.avg_basis_contract_price()

    def noncontract_fut_revenue(self, pf=None, yf=None):
        """ 2d array or scalar """
        if scal(pf):
            result = self.sens_fut_uncontracted_bu(yf) * self.sens_harvest_price(pf)
        else:
            result = np.outer(self.sens_harvest_price(pf),
                              self.sens_fut_uncontracted_bu(yf))
        return result

    def noncontract_basis_revenue(self, yf=None, bf=None):
        """ array(ny, nb), array(ny) or scalar """
        if scal(yf) or bf is None:
            return self.sens_basis_uncontracted_bu(yf) * self.assumed_basis_for_new()
        else:
            return np.outer(self.sens_basis_uncontracted_bu(yf),
                            self.assumed_basis_for_new(bf))

    def frac_rev_excess(self, pf=None, yf=None):
        """
        scalar or array(np, ny) fraction revenue excess or (shortfall)
        used by both budget and sensitivity.
        """
        data = self.indem_price_yield_data(pf=pf, yf=yf)
        base_rev = (self.planted_acres *
                    self.farmbudgetcrop.baseline_yield_for_var_rent * data['pp'][0])
        if scal(pf):
            sens_rev = (self.planted_acres * self.sens_farm_expected_yield(yf=yf) *
                        data['hp'][0])
        else:
            sens_rev = (self.planted_acres *
                        np.outer(data['hp'][0], self.sens_farm_expected_yield(yf=yf)))
        result = (0 if base_rev == 0 else (sens_rev - base_rev) / base_rev)
        return result

    def grain_revenue(self, pf=None, yf=None, bf=None):
        """ scalar or array(pf, yf) or array(pf, yf, bf) used by sensitivity, others """
        if scal(pf):
            return (self.contract_fut_revenue(yf=yf) +
                    self.contract_basis_revenue(yf=yf) +
                    self.noncontract_fut_revenue(pf=pf, yf=yf) +
                    self.noncontract_basis_revenue(yf=yf))
        elif bf is None:
            return ((self.contract_fut_revenue(yf=yf) +
                     self.contract_basis_revenue(yf=yf) +
                     self.noncontract_basis_revenue(yf=yf)).reshape(1, len(yf)) +
                    self.noncontract_fut_revenue(pf=pf, yf=yf))
        else:
            return ((self.contract_fut_revenue(yf=yf) +
                     self.contract_basis_revenue(yf=yf)).reshape(1, len(yf), 1) +
                    (self.noncontract_fut_revenue(pf=pf, yf=yf)
                     .reshape(len(pf), len(yf), 1)) +
                    (self.noncontract_basis_revenue(yf=yf, bf=bf)
                     .reshape(1, len(yf), len(bf))))

    # -----------------------------------------
    # Cost methods in $/acre except where noted
    # -----------------------------------------
    def total_direct_costs(self):
        if not self.has_budget():
            return 0
        fbc = self.farmbudgetcrop
        return (fbc.fertilizers + fbc.pesticides + fbc.seed + fbc.drying +
                fbc.storage + self.get_total_premiums() + fbc.other_direct_costs)

    def total_nonland_costs(self):
        """ used by sensitivity table and listview """
        if not self.has_budget():
            return 0
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
        """ a fraction - used by both budget table and sensitivity """
        if not self.has_budget():
            return zero_like(yf)
        if yf is None:
            yf = self.farmbudgetcrop.yield_factor
        fbc = self.farmbudgetcrop
        farm_yield = self.sens_farm_expected_yield(yf=yf)
        eff_yf = farm_yield / fbc.baseline_yield_for_var_rent
        costfinal = fbc.are_costs_final
        if scal(yf):
            return (0 if costfinal else
                    fbc.yield_variability * (eff_yf - 1))
        else:
            return (np.zeros_like(yf) if costfinal else
                    fbc.yield_variability * (eff_yf - 1))

    def revenue_based_adj_to_land_rent(self, pf=None, yf=None):
        """
        a fraction or array(np, ny) of fractions
        used by both budget table and sensitivity
        """
        if not self.has_budget():
            return (0 if scal(pf) else np.zeros((len(pf), len(yf))))
        cf = self.farm_year.var_rent_cap_floor_frac
        fv = self.farm_year.frac_var_rent()
        fre = self.frac_rev_excess(pf, yf)
        if scal(pf):
            result = fv * (np.copysign(cf, fre) if abs(fre) > cf else fre)
        else:
            result = fv * (np.where(abs(fre) > cf, np.copysign(cf, fre), fre))
        return result

    def rented_land_costs(self, pf=None, yf=None):
        """
        Scalar or array(np, ny) used by sensitivity table and listview.
        Rent cost in dollars per planted acre.
        Land cost = 0 for dc soybeans in std. budgets.
        """
        if not self.has_budget():
            return (0 if scal(pf) else np.zeros(len(pf), len(yf)))
        # rent cost per planted acre
        tot_acres = self.farm_year.total_farm_acres()
        rented_costperacre = (0 if tot_acres == 0 else
                              self.farmbudgetcrop.rented_land_costs *
                              self.farm_year.total_rented_acres() / tot_acres)
        return (rented_costperacre *
                (1 + self.revenue_based_adj_to_land_rent(pf, yf)))

    def owned_land_costs(self):
        """ scalar used only by sensitivity table """
        tot_acres = self.farm_year.total_farm_acres()
        return (0 if self.farm_crop_type.is_fac or tot_acres == 0 else
                (self.farm_year.total_owned_land_expense() / tot_acres))

    def land_costs(self, pf=None, yf=None):
        """ array(np, ny) used only by sensitivity table """
        return (self.rented_land_costs(pf, yf) + self.owned_land_costs())

    def total_cost(self, pf=None, yf=None):
        """ array(np, ny) used only by sensitivity table """
        if not self.has_budget():
            return (0 if scal(pf) else np.zeros((len(pf), len(yf))))
        tot_nonland_cost = self.total_nonland_costs()
        return ((tot_nonland_cost *
                 (1 + self.yield_adj_to_nonland_costs(yf))).reshape(1, len(yf)) +
                self.land_costs(pf, yf))

    # -------------
    # Price methods
    # -------------
    def harvest_price(self):
        return self.market_crop.harvest_futures_price_info(price_only=True)

    def sens_harvest_price(self, pf=None):
        """ cached scalar or array(pf) used by budget and sensitivity """
        return self.market_crop.sens_harvest_price(pf=pf)

    def avg_futures_contract_price(self):
        return self.market_crop.avg_futures_contract_price()

    def avg_basis_contract_price(self):
        return self.market_crop.avg_basis_contract_price()

    def assumed_basis_for_new(self, bf=None):
        """ scalar or array(nb) """
        return self.market_crop.assumed_basis_for_new + (0 if bf is None else bf)

    # --------------
    # Budget methods
    # --------------
    def get_budget_crops(self):
        return [
            (it, get_budget_crop_description(
                it.is_rot, it.description, it.farm_yield, it.rented_land_costs,
                it.state.abbr))
            for it in BudgetCrop.objects.filter(
                farm_crop_type_id=self.farm_crop_type, is_irr=self.is_irrigated(),
                budget__crop_year=self.farm_year.crop_year).only(
                    "id", "budget_id", "is_rot", "description", "farm_yield",
                    "rented_land_costs", "state__abbr")]

    def has_budget(self):
        if self.has_budget_mem is None:
            try:
                self.farmbudgetcrop
                self.has_budget_mem = True
            except ObjectDoesNotExist:
                self.has_budget_mem = False
        return self.has_budget_mem

    # ---------------------
    # Validation and saving
    # ---------------------
    def clean(self):
        fsa_crop_has_arcco = (self.market_crop.fsa_crop.arcco_base_acres > 0)
        if self.sco_use and fsa_crop_has_arcco:
            raise ValidationError({'sco_use': _(
                "ARC-CO base acres must be zero if SCO is set for related farm crop")})
        # For now, allow users to set options freely.  The rules are not clear.
        # if self.is_irrigated() and self.ye:
        #     raise ValidationError({'ye': _(
        #         "Yield Exclusion (YE) is not available for irrigated crops")})
        # if self.is_beans() and self.ye:
        #     raise ValidationError({'ye': _(
        #         "Yield Exclusion (YE) is not available for soybeans")})

    def save(self, *args, **kwargs):
        no_check = kwargs.pop('no_check', None)
        change_related = kwargs.pop('change_related', None)
        if (change_related is None and no_check is None and
            any_changed(self, 'coverage_type', 'product_type',
                        'base_coverage_level', 'sco_use', 'eco_level',
                        'prot_factor')):
            self.update_related_crop_ins_settings()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['farm_crop_type_id']


class FarmBudgetCrop(models.Model):
    """
    A possibly user-modfied copy of a budget column named by its budget_crop_type name.
    Cost items are in dollars per acre.  One or two (rotated/non-rotated) budget crops
    are assigned To each farm crop based on matching the farm_crop_type and
    irrigated status of the farm crop to the buddget crop type.
    """
    farm_yield = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(400)],
        help_text='Set this to the final farm yield after harvest')
    # the farm yield value is copied to county yield when the budget crop is copied.
    county_yield = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(400)],
        help_text='Set this to the estimated final county yield after harvest')
    description = models.CharField(max_length=50)
    yield_variability = models.FloatField(
        default=0, validators=[
            MinVal(0),
            MaxVal(1, message="Ensure this value is greater than or equal to 100")],
        help_text='Percent of nonland cost assumed to depend on yield')
    other_gov_pmts = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(99999)])
    other_revenue = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    fertilizers = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    pesticides = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    seed = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    drying = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    storage = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    other_direct_costs = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        help_text="Other (hauling, custom operations)")
    machine_hire_lease = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="machine hire or lease")
    utilities = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    machine_repair = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    fuel_and_oil = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    light_vehicle = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    machine_depr = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="machine depreciation")
    labor_and_mgmt = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="labor and management")
    building_repair_and_rent = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    building_depr = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="building depreciation")
    insurance = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    misc_overhead_costs = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    interest_nonland = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)],
        verbose_name="non-land interest cost")
    other_overhead_costs = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(999999)])
    rented_land_costs = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(9999999)])
    farm_crop_type = models.ForeignKey(
        FarmCropType, on_delete=models.CASCADE, null=True)
    farm_crop = models.OneToOneField(
        FarmCrop, on_delete=models.CASCADE, null=True)
    farm_year = models.ForeignKey(
        FarmYear, on_delete=models.CASCADE, null=True)
    budget = models.ForeignKey(Budget, on_delete=models.SET_NULL, null=True)
    budget_crop = models.ForeignKey(BudgetCrop, on_delete=models.SET_NULL, null=True)
    state = models.ForeignKey(
        State, on_delete=models.CASCADE, null=True, related_name='farm_budget_crops')
    is_rot = models.BooleanField(null=True)
    is_irr = models.BooleanField(default=False)
    # This is set to the ext_budget.created_on date when a farm budget crop is added.
    # If a budget for a crop year is updated, we can compare its created_on date with
    # corresponding user budget_date and notify users
    budget_date = models.DateField(null=True)
    baseline_yield_for_var_rent = models.FloatField(
        default=0, validators=[MinVal(0), MaxVal(400)],
        verbose_name="baseline yield",
        help_text=('Fixed farm yield used for variable rent ' +
                   'and yield-based cost adjustment'))
    is_farm_yield_final = models.BooleanField(
        default=False, verbose_name="Are yields final?",
        help_text='Adjust expected yield(s) and check this box after harvest')
    yield_factor = models.FloatField(
        default=1, validators=[
            MinVal(0),
            MaxVal(2, message="Ensure this value is less than or equal to 200")],
        verbose_name='yield sensititivity factor',
        help_text=('Percent of expected yield(s) assesed prior to harvest, ' +
                   'affecting detailed budget'))
    are_costs_final = models.BooleanField(
        default=False, verbose_name="Costs final?",
        help_text='Adjust costs and check this box (if desired) once costs are known')

    def __str__(self):
        rotstr = (' Rotating' if self.is_rot
                  else '' if self.is_rot is None else ' Continuous,')
        descr = '' if self.description == '' else f' {self.description},'
        result = (f'{self.state.abbr},{descr}{rotstr}')
        return result

    class Meta:
        ordering = ['farm_crop_type_id']

    def total_power_costs(self):
        """ for farm budget crop detail view """
        return (self.machine_hire_lease + self.utilities + self.machine_repair +
                self.fuel_and_oil + self.light_vehicle + self.machine_depr)

    def total_overhead_costs(self):
        """ for farm budget crop detail view """
        return (self.labor_and_mgmt + self.building_repair_and_rent +
                self.building_depr + self.insurance + self.misc_overhead_costs +
                self.interest_nonland + self.other_overhead_costs)
