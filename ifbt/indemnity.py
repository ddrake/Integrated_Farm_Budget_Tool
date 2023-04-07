"""
"""
from numpy import zeros, ones, array
import numpy as np

from .analysis import Analysis
from .util import Crop, crop_in, SEASON_CROPS, Unit, Lvl


class Indemnity(Analysis):
    """
    Class encapsulating crop insurance indemnitiy payments
    """
    DATA_FILES = 'farm_data crop_ins_data'

    def __init__(self, *args, **kwargs):
        """
        Initialize the class, setting some useful attributes.
        """
        super().__init__(*args, **kwargs)
        self.crop = None  # set when one of the main methods is called
        self.cover = array(range(50, 86, 5))
        self.cover_arc = array(range(70, 91, 5))
        self.cover_eco = array([90, 95])
        self.indemnity_ent = None
        self.indemnity_arc = None
        self.indemnity_sco = None
        self.indemnity_eco = None

    # --------------------------
    # MAIN METHOD FOR ENTERPRISE
    # --------------------------
    @crop_in(*SEASON_CROPS)
    def compute_indems_ent(self, crop, pf=1, yf=1):
        """ array(8,3)
        Government Crop Insurance J61: Sensitized total indemnity payment.
        """
        self.crop = crop
        self.indemnity_ent = (self.harvest_indemnity_pmt_per_acre(pf, yf))
        return self.indemnity_ent

    def harvest_indemnity_pmt_per_acre(self, pf=1, yf=1):
        """ array(8,3)
        Government Crop Insurance J52: Sensitized harvest indemnity payment.
        in dollars per acre.
        """
        harv_indem_per_acre = zeros((8, 3))
        harv_indem_per_acre[:] = self.revenue_loss(pf, yf)
        harv_indem_per_acre[:, 2] = (self.yield_shortfall(yf) *
                                     self.ins_spring_proj_harv_price[self.crop])
        return harv_indem_per_acre

    def yield_shortfall(self, yf=1):
        """YO  array(8)
        Government Crop Insurance L47: Yield-sensitized yield shortfall.
        """
        return np.maximum(
            self.yield_trigger() - self.projected_yield_crop(self.crop, yf), 0)

    def revenue_loss(self, pf=1, yf=1):
        """ array(8, 3)
        Government Crop Insurance F46: Sensitized revenue loss.
        """
        return np.maximum(
            np.maximum(
                self.revenue_trigger_feb_price().reshape(8, 1),
                self.revised_revenue_trigger(pf, yf)) - self.actual_revenue(pf, yf),
            0)

    def revenue_trigger_feb_price(self):
        """ array(8)
        Government Crop Insurance F41: The product of the actual fall harvest
        futures price in February with the yield trigger (defined in derived
        classes).
        """
        return self.yield_trigger() * self.ins_spring_proj_harv_price[self.crop]

    def revised_revenue_trigger(self, pf=1, yf=1):
        """ array(8, 3)
        Government Crop Insurance F43: Sensitized revised revenue trigger.
        """
        revised_rev_trig = ones((8, 3)) * self.yield_trigger().reshape(8, 1)
        revised_rev_trig[:, 0] *= self.rev_trigger_condition(pf, yf)
        revised_rev_trig[:, 2] *= self.rev_trigger_condition(pf, yf)
        revised_rev_trig[:, 1] *= (
            0 if (self.ins_harvest_price(pf) >
                  self.ins_spring_proj_harv_price[self.crop])
            else self.ins_spring_proj_harv_price[self.crop])
        return revised_rev_trig

    def actual_revenue(self, pf=1, yf=1):
        """ scalar
        Government Crop Insurance J45: Sensitized actual revenue.
        """
        return (self.projected_yield_crop(self.crop, yf) *
                self.ins_harvest_price(pf))

    def yield_trigger(self):
        """ array(8)
        Government Crop Insurance J40: Yield trigger.
        """
        return (self.hist_yield_for_ins_ent[self.crop] *
                self.cover / 100)

    def rev_trigger_condition(self, pf=1, yf=1):
        """ scalar
        Helper used by revised_revenue_trigger and revenue_loss.
        """
        return (self.ins_harvest_price(pf)
                if (self.ins_harvest_price(pf) >
                    self.ins_spring_proj_harv_price[self.crop])
                else 0)

    def sensitized_fall_price(self, pf=1):
        """ scalar
        Government Crop Insurance F12: The price sensitized estimate of the
        fall harvest futures price.
        """
        return self.fall_futures_price[self.base_crop()] * pf

    def ins_harvest_price(self, pf=1):
        """ scalar
        Government Crop Insurance F13:
        """
        return min((self.ins_spring_proj_harv_price[self.crop] *
                    self.price_cap_factor),
                   self.sensitized_fall_price(pf))

    # -------------------
    # MAIN METHOD FOR ARC
    # -------------------
    @crop_in(*SEASON_CROPS)
    def compute_indems_arc(self, crop, pf=1, yf=1):
        """
        array(5,3)
        Sensitized total indemnity payment for all protections and levels.
        """
        self.crop = crop
        self.indemnity_arc = self.harvest_indemnity_pmt_per_acre_arc(pf, yf)
        return self.indemnity_arc

    def harvest_indemnity_pmt_per_acre_arc(self, pf=1, yf=1):
        """
        Government Crop Insurance FGH52: Sensitized per acre indemnity payment
        in dollars per acre.
        array(5, 3)
        """
        harv_indem_pmt_per_acre = ones((5, 3))
        harv_indem_pmt_per_acre *= self.payment_factor_arc(pf, yf)
        harv_indem_pmt_per_acre[:, 0] *= max(
            self.minimum_dollars_protection_arc(),
            self.revised_dollars_of_protection_arc(pf, yf))
        harv_indem_pmt_per_acre[:, 1:] *= self.minimum_dollars_protection_arc()
        return harv_indem_pmt_per_acre

    def minimum_dollars_protection_arc(self):
        """
        Government Crop Insurance F42: Minimum dollars of protection.
        scalar
        """
        return (self.hist_yield_for_ins_area[self.crop] *
                self.ins_spring_proj_harv_price[self.crop] *
                self.prot_factor[self.crop])

    def revised_dollars_of_protection_arc(self, pf=1, yf=1):
        """
        scalar
        AREA RP used above
        Government Crop Insurance F44: Sensitized revised dollars of protection.
        """
        return (self.hist_yield_for_ins_area[self.crop] *
                self.prot_factor[self.crop] *
                self.rev_trigger_condition(pf, yf))  # not ARC-specific

    def payment_factor_arc(self, pf=1, yf=1):
        """
        Government Crop Insurance FGH50: Sensiized payment factor.
        array(5, 3)
        """
        rev_yo = np.maximum(
            0, self.yield_trigger_arc() - self.county_rma_yield(yf))
        rev = self.revenue_loss_arc(pf, yf)
        pmt_factor = zeros((5, 3))
        pmt_factor[:] = rev
        pmt_factor[:, 2] = rev_yo
        pmt_factor /= self.maximum_loss_pmt_arc(pf, yf)
        return pmt_factor

    def maximum_loss_pmt_arc(self, pf=1, yf=1):
        """ AREA RP
        Government Crop Insurance F49: Sensitized maximum loss payment.
        array(5,3)
        """
        max_loss_pmt = zeros((5, 3))
        max_loss_pmt[:] -= self.limiting_revenue_factor_arc(pf)
        max_loss_pmt[:, 0] += np.maximum(
            self.revenue_trigger_feb_price_arc(),
            self.revised_revenue_trigger_arc(pf, yf))
        max_loss_pmt[:, 1] += self.revenue_trigger_feb_price_arc()
        max_loss_pmt[:, 2] += self.yield_trigger_arc()
        return max_loss_pmt

    def limiting_revenue_factor_arc(self, pf=1):
        """
        array(3)
        Government Crop Insurance FGH48: Price-sensitized limiting revenue factor.
        """
        limiting_revenue_fact = (
            ones(3) * self.hist_yield_for_ins_area[self.crop] *
            self.loss_limit_factor)

        limiting_revenue_fact[0] *= max(
            self.ins_spring_proj_harv_price[self.crop],
            self.ins_harvest_price(pf))
        limiting_revenue_fact[1] *= self.ins_spring_proj_harv_price[self.crop]
        return limiting_revenue_fact

    def revenue_loss_arc(self, pf=1, yf=1):
        """
        array(5, 3) TODO: test maximums
        Government Crop Insurance F46: Sensitized revenue loss.
        """
        maxfactor = np.maximum(
            self.revenue_trigger_feb_price_arc(),
            self.revised_revenue_trigger_arc(pf, yf))
        rev_loss = ones((5, 3))
        rev_loss[:, 0] = maxfactor
        rev_loss[:, 1] = self.revenue_trigger_feb_price_arc()
        rev_loss[:, 2] = maxfactor
        rev_loss[:, :2] = np.maximum(
            rev_loss[:, :2] - self.actual_revenue_arc(pf, yf), 0)
        return rev_loss

    def revised_revenue_trigger_arc(self, pf=1, yf=1):
        """ from base class
        Government Crop Insurance F43: Sensitized revised revenue trigger.
        array(5)
        """
        return self.yield_trigger_arc() * self.rev_trigger_condition(pf, yf)

    def revenue_trigger_feb_price_arc(self):
        """ from base class
        Government Crop Insurance F41: The product of the actual fall harvest
        futures price in February with the yield trigger (defined in derived
        classes).
        array(5)
        """
        return (self.yield_trigger_arc() *
                self.ins_spring_proj_harv_price[self.crop])

    def actual_revenue_arc(self, pf=1, yf=1):
        """
        Government Crop Insurance F45: Sensitized actual revenue.
        scalar
        """
        return (self.county_rma_yield(yf) *
                self.ins_harvest_price(pf))

    def county_rma_yield(self, yf=1):
        """
        Government Crop Insurance F15: Yield-sensitized county RMA yield for the
        specified crop.  This formula works if and only if the county yields
        correlate with the farm yields.  A conservative farm to county premium
        is used.
        Note: County RMA doesn't distinguish between soy_fs and soy_dc, so we
        return the same value for full and dc here.
        scalar
        """
        crop = Crop.FULL_SOY if self.crop == Crop.DC_SOY else self.crop
        return (self.projected_yield_crop(crop, yf) /
                (1 + self.farm_yield_premium_to_county[crop]))

    def yield_trigger_arc(self):
        """
        Government Crop Insurance F40: Trigger based on historical county
        yield.
        array(5)
        """
        return (self.hist_yield_for_ins_area[self.crop] *
                self.cover_arc / 100)

    # ------------------
    # OPTIONS (SCO, ECO)
    # ------------------
    @crop_in(*SEASON_CROPS)
    def compute_indems_sco(self, crop, pf=1, yf=1):
        self.crop = crop
        self.indemnity_sco = self.harvest_indemnity_pmt_per_acre_opt(self.cover, pf, yf)
        return self.indemnity_sco

    @crop_in(*SEASON_CROPS)
    def compute_indems_eco(self, crop, pf=1, yf=1):
        self.crop = crop
        self.indemnity_eco = self.harvest_indemnity_pmt_per_acre_opt(self.cover_eco,
                                                                     pf, yf)
        return self.indemnity_eco

    def harvest_indemnity_pmt_per_acre_opt(self, cov, pf=1, yf=1):
        """
        Government Crop Insurance J84: Sensitized harvest indemnity per acre.
        Used by all derived classes.
        array(len(cov))
        """
        is_eco = len(cov) == 2
        sco_top_level = self.sco_top_level/100
        lvl = cov/100 if is_eco else ones(len(cov)) * sco_top_level
        diff = (cov/100 - sco_top_level if is_eco
                else sco_top_level - cov/100)
        return (self.farm_crop_value(diff, pf) *
                self.payment_factor(lvl, diff, pf, yf))

    def farm_crop_value(self, diff, pf=1):
        """
        Government Crop Insurance J83: Price-sensitized farm crop vaue.
        Used by RP-HPE and YO derived classes.
        array(len(diff), 3)
        """
        farm_crop_val = ones((len(diff), 3))
        farm_crop_val *= self.hist_yield_for_ins_ent[self.crop]
        farm_crop_val *= diff.reshape(len(diff), 1)
        farm_crop_val[:, 0] *= max(
            self.ins_harvest_price(pf),
            self.ins_spring_proj_harv_price[self.crop])
        farm_crop_val[:, 1:] *= self.ins_spring_proj_harv_price[self.crop]
        return farm_crop_val

    def payment_factor(self, lvl, diff, pf=1, yf=1):
        """ array(len(lvl), 3)
        Government Crop Insurance J82: Sensitized payment factor.
        Used by all derived classes.
        """
        lvlrs = lvl.reshape(len(lvl), 1)
        diffrs = diff.reshape(len(lvl), 1)
        return np.where(
            self.county_rev_as_ratio(diff, pf, yf) > lvlrs,
            zeros((len(lvl), 3)),
            np.minimum((lvlrs - self.county_rev_as_ratio(diff, pf, yf)) / diffrs, 1))

    def county_rev_as_ratio(self, diff, pf=1, yf=1):
        """ array(len(diff), 3)
        Government Crop Insurance J81: Sensitized ratio of actual to insured
        county revenue.  Used by all derived classes.
        """
        cty_rev_as_ratio = ones((len(diff), 3))
        cty_rev_as_ratio[:] *= (
            self.actual_revenue_opt(pf, yf) /
            self.county_insured_revenue(pf))
        return cty_rev_as_ratio

    def actual_revenue_opt(self, pf=1, yf=1):
        """
        Government Crop Insurance F45: Sensitized actual revenue.
        scalar
        array(3)
        """
        actual_rev_arc = ones(3) * self.county_rma_yield(yf)
        actual_rev_arc[:2] *= self.ins_harvest_price(pf)
        actual_rev_arc[2] *= self.ins_spring_proj_harv_price[self.crop]
        return actual_rev_arc

    def county_insured_revenue(self, pf=1):
        """option base
        Government Crop Insurance J80: Price-sensitized county insured revenue.
        Used by RP-HPE and YO derived classes.
        array(3)
        """
        cty_insured_rev = ones(3)
        cty_insured_rev *= self.hist_yield_for_ins_area[self.crop]
        cty_insured_rev[1:] *= self.ins_spring_proj_harv_price[self.crop]
        cty_insured_rev[0] *= max(
             self.ins_harvest_price(pf),
             self.ins_spring_proj_harv_price[self.crop])
        return cty_insured_rev

    # ------------------
    # Convenience Method
    # ------------------
    def get_all_indemnities(self, cropdicts=None, pf=1, yf=1):
        """
        Given a list of dicts, one for each crop, containing specific choices of
        unit, level, sco_level, eco_level, Return a dict of dicts, each containing
        individual indemnities for the base product and options.
        """
        indemnities = {}
        if cropdicts is None:
            return indemnities
        for d in cropdicts:
            crop = d['crop']
            self.prot_factor[crop] = d['prot_factor']
            values = {'base': 0, 'sco': 0, 'eco': 0}
            if d['unit'] == Unit.ENT:
                indems = self.compute_indems_ent(crop, pf, yf)
                values['base'] = indems[entlevel_idx(d['level']), d['protection']]
            else:
                indems = self.compute_indems_arc(crop, pf, yf)
                values['base'] = indems[arclevel_idx(d['level']), d['protection']]
            if d['sco_level'] > Lvl.NONE:
                indems = self.compute_indems_sco(crop, pf, yf)
                sco_level = d['level'] if d['sco_level'] == Lvl.DFLT else d['sco_level']
                values['sco'] = indems[entlevel_idx(sco_level), d['protection']]
            if d['eco_level'] > Lvl.NONE:
                indems = self.compute_indems_eco(crop, pf, yf)
                values['eco'] = (indems[0 if d['eco_level'] == 90
                                        else 1, d['protection']])
            indemnities[crop] = values
        return indemnities


# ----------------
# Helper functions
# ----------------
def entlevel_idx(intval):
    if intval < 50 or intval > 85:
        raise ValueError('Invalid level for Enterprise unit')
    return (intval - 50)//5


def arclevel_idx(intval):
    if intval < 70 or intval > 90:
        raise ValueError('Invalid level for ARC unit')
    return (intval - 70)//5
