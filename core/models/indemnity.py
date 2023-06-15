"""
Module indemnity
Provides class Indemnity for computing crop insurance indemnity payments
"""
from numpy import zeros, ones, array
import numpy as np


class Indemnity():
    """
    Class encapsulating crop insurance indemnity payments
    """
    PRICE_CAP_FACTOR = 2
    LOSS_LIMIT_FACTOR = 0.18
    SCO_TOP_LEVEL = 86

    def __init__(self, tayield=165, projected_price=5.5, harvest_futures_price=5.25,
                 rma_cty_expected_yield=None, prot_factor=1,
                 farm_expected_yield=210, cty_expected_yield=192):
        """
        Initialize the class, setting some useful attributes.
        """
        # RMA Rate Yield (TA/YE adjusted APH yield)
        self.tayield = tayield
        # RMA Projected Price set after discovery period
        self.projected_price = projected_price
        # The sensitized current futures harvest price or RMA final price for the crop
        self.harvest_futures_price = harvest_futures_price
        # The RMA county expected yield
        self.rma_cty_expected_yield = rma_cty_expected_yield
        # The sensitized farm expected yield
        self.farm_expected_yield = farm_expected_yield
        # sensitized estimated county yield or RMA final county yield
        self.cty_expected_yield = cty_expected_yield
        # The protecton factor (scales county premiums and indemnities)
        self.prot_factor = prot_factor
        # Coverage levels for enterprise, SCO
        self.cover = array(range(50, 86, 5))
        # Coverage levels for county area
        self.cover_area = array(range(70, 91, 5))
        # Coverage levels for ECO
        self.cover_eco = array([90, 95])
        self.indemnity_ent = None
        self.indemnity_area = None
        self.indemnity_sco = None
        self.indemnity_eco = None

    # -----------
    # MAIN METHOD
    # -----------
    def compute_indems(self):
        indemnity_ent = self.harvest_indemnity_pmt_per_acre().round(2)
        indemnity_area = self.harvest_indemnity_pmt_per_acre_area().round(2)
        indemnity_sco = self.harvest_indemnity_pmt_per_acre_opt(self.cover).round(2)
        indemnity_eco = self.harvest_indemnity_pmt_per_acre_opt(self.cover_eco).round(2)
        return indemnity_ent, indemnity_area, indemnity_sco, indemnity_eco

    # --------------------------
    # MAIN METHOD FOR ENTERPRISE
    # --------------------------
    def harvest_indemnity_pmt_per_acre(self):
        """ array(8,3)
        Government Crop Insurance J52: Sensitized harvest indemnity payment.
        in dollars per acre.
        """
        harv_indem_per_acre = zeros((8, 3))
        harv_indem_per_acre[:] = self.revenue_loss()
        harv_indem_per_acre[:, 2] = (self.yield_shortfall() * self.projected_price)
        return harv_indem_per_acre

    def yield_shortfall(self):
        """YO  array(8)
        Government Crop Insurance L47: Yield-sensitized yield shortfall.
        """
        return np.maximum(
            self.yield_trigger() - self.farm_expected_yield, 0)

    def revenue_loss(self):
        """ array(8, 3)
        Government Crop Insurance F46: Sensitized revenue loss.
        """
        return np.maximum(
            np.maximum(
                self.revenue_trigger_feb_price().reshape(8, 1),
                self.revised_revenue_trigger()) - self.actual_revenue(),
            0)

    def revenue_trigger_feb_price(self):
        """ array(8)
        Government Crop Insurance F41: The product of the actual fall harvest
        futures price in February with the yield trigger (defined in derived
        classes).
        """
        return self.yield_trigger() * self.projected_price

    def revised_revenue_trigger(self):
        """ array(8, 3)
        Government Crop Insurance F43: Sensitized revised revenue trigger.
        """
        revised_rev_trig = ones((8, 3)) * self.yield_trigger().reshape(8, 1)
        revised_rev_trig[:, 0] *= self.rev_trigger_condition()
        revised_rev_trig[:, 2] *= self.rev_trigger_condition()
        revised_rev_trig[:, 1] *= (
            0 if self.ins_harvest_price() > self.projected_price
            else self.projected_price)
        return revised_rev_trig

    def actual_revenue(self):
        """ scalar
        Government Crop Insurance J45: Sensitized actual revenue.
        """
        return self.farm_expected_yield * self.ins_harvest_price()

    def yield_trigger(self):
        """ array(8)
        Government Crop Insurance J40: Yield trigger.
        """
        return (self.tayield * self.cover / 100)

    def rev_trigger_condition(self):
        """ scalar
        Helper used by revised_revenue_trigger and revenue_loss.
        """
        return (self.ins_harvest_price()
                if self.ins_harvest_price() > self.projected_price else 0)

    def ins_harvest_price(self):
        """ scalar
        Government Crop Insurance F13:
        """
        return min(self.projected_price * Indemnity.PRICE_CAP_FACTOR,
                   self.harvest_futures_price)

    # -------------------
    # MAIN METHOD FOR ARC
    # -------------------
    def harvest_indemnity_pmt_per_acre_area(self):
        """
        Government Crop Insurance FGH52: Sensitized per acre indemnity payment
        in dollars per acre.
        array(5, 3)
        """
        harv_indem_pmt_per_acre = ones((5, 3))
        harv_indem_pmt_per_acre *= self.payment_factor_area()
        harv_indem_pmt_per_acre[:, 0] *= max(
            self.minimum_dollars_protection_area(),
            self.revised_dollars_of_protection_area())
        harv_indem_pmt_per_acre[:, 1:] *= self.minimum_dollars_protection_area()
        return harv_indem_pmt_per_acre

    def minimum_dollars_protection_area(self):
        """
        Government Crop Insurance F42: Minimum dollars of protection.
        scalar
        """
        return (self.rma_cty_expected_yield *
                self.projected_price *
                self.prot_factor)

    def revised_dollars_of_protection_area(self):
        """
        scalar
        AREA RP used above
        Government Crop Insurance F44: Sensitized revised dollars of protection.
        """
        return (self.rma_cty_expected_yield *
                self.prot_factor *
                self.rev_trigger_condition())  # not ARC-specific

    def payment_factor_area(self):
        """
        Government Crop Insurance FGH50: Sensiized payment factor.
        array(5, 3)
        """
        rev_yo = np.maximum(
            0, self.yield_trigger_area() - self.cty_expected_yield)
        rev = self.revenue_loss_area()
        pmt_factor = zeros((5, 3))
        pmt_factor[:] = rev
        pmt_factor[:, 2] = rev_yo
        pmt_factor /= self.maximum_loss_pmt_area()
        return pmt_factor

    def maximum_loss_pmt_area(self):
        """ AREA RP
        Government Crop Insurance F49: Sensitized maximum loss payment.
        array(5,3)
        """
        max_loss_pmt = zeros((5, 3))
        max_loss_pmt[:] -= self.limiting_revenue_factor_area()
        max_loss_pmt[:, 0] += np.maximum(
            self.revenue_trigger_feb_price_area(),
            self.revised_revenue_trigger_area())
        max_loss_pmt[:, 1] += self.revenue_trigger_feb_price_area()
        max_loss_pmt[:, 2] += self.yield_trigger_area()
        return max_loss_pmt

    def limiting_revenue_factor_area(self):
        """
        array(3)
        Government Crop Insurance FGH48: Price-sensitized limiting revenue factor.
        """
        limiting_revenue_fact = (
            ones(3) * self.rma_cty_expected_yield *
            Indemnity.LOSS_LIMIT_FACTOR)

        limiting_revenue_fact[0] *= max(
            self.projected_price,
            self.ins_harvest_price())
        limiting_revenue_fact[1] *= self.projected_price
        return limiting_revenue_fact

    def revenue_loss_area(self):
        """
        array(5, 3) TODO: test maximums
        Government Crop Insurance F46: Sensitized revenue loss.
        """
        maxfactor = np.maximum(
            self.revenue_trigger_feb_price_area(),
            self.revised_revenue_trigger_area())
        rev_loss = ones((5, 3))
        rev_loss[:, 0] = maxfactor
        rev_loss[:, 1] = self.revenue_trigger_feb_price_area()
        rev_loss[:, 2] = maxfactor
        rev_loss[:, :2] = np.maximum(
            rev_loss[:, :2] - self.actual_revenue_area(), 0)
        return rev_loss

    def revised_revenue_trigger_area(self):
        """ from base class
        Government Crop Insurance F43: Sensitized revised revenue trigger.
        array(5)
        """
        return self.yield_trigger_area() * self.rev_trigger_condition()

    def revenue_trigger_feb_price_area(self):
        """ from base class
        Government Crop Insurance F41: The product of the actual fall harvest
        futures price in February with the yield trigger (defined in derived
        classes).
        array(5)
        """
        return self.yield_trigger_area() * self.projected_price

    def actual_revenue_area(self):
        """
        Government Crop Insurance F45: Sensitized actual revenue.
        scalar
        """
        return self.cty_expected_yield * self.ins_harvest_price()

    def yield_trigger_area(self):
        """
        Government Crop Insurance F40: Trigger based on historical county
        yield.
        array(5)
        """
        return (self.rma_cty_expected_yield * self.cover_area / 100)

    # ------------------
    # OPTIONS (SCO, ECO)
    # ------------------
    def harvest_indemnity_pmt_per_acre_opt(self, cov):
        """
        Government Crop Insurance J84: Sensitized harvest indemnity per acre.
        Used by all derived classes.
        array(len(cov))
        """
        # TODO: Investigate this: We can compute option premiums without
        # rma_cty_expected_yield, but not indemnities?
        if self.rma_cty_expected_yield is None:
            return zeros((len(cov), 3))
        is_eco = len(cov) == 2
        sco_top_level = Indemnity.SCO_TOP_LEVEL/100
        lvl = cov/100 if is_eco else ones(len(cov)) * sco_top_level
        diff = (cov/100 - sco_top_level if is_eco
                else sco_top_level - cov/100)
        return (self.farm_crop_value(diff) *
                self.payment_factor(lvl, diff))

    def farm_crop_value(self, diff):
        """
        Government Crop Insurance J83: Price-sensitized farm crop value.
        Used by RP-HPE and YO derived classes.
        array(len(diff), 3)
        """
        farm_crop_val = ones((len(diff), 3))
        farm_crop_val *= self.tayield
        farm_crop_val *= diff.reshape(len(diff), 1)
        farm_crop_val[:, 0] *= max(self.ins_harvest_price(), self.projected_price)
        farm_crop_val[:, 1:] *= self.projected_price
        return farm_crop_val

    def payment_factor(self, lvl, diff):
        """ array(len(lvl), 3)
        Government Crop Insurance J82: Sensitized payment factor.
        Used by all derived classes.
        """
        lvlrs = lvl.reshape(len(lvl), 1)
        diffrs = diff.reshape(len(lvl), 1)
        return np.where(
            self.county_rev_as_ratio(diff) > lvlrs,
            zeros((len(lvl), 3)),
            np.minimum((lvlrs - self.county_rev_as_ratio(diff)) / diffrs, 1))

    def county_rev_as_ratio(self, diff):
        """ array(len(diff), 3)
        Government Crop Insurance J81: Sensitized ratio of actual to insured
        county revenue.  Used by all derived classes.
        """
        cty_rev_as_ratio = ones((len(diff), 3))
        cty_rev_as_ratio[:] *= (
            self.actual_revenue_opt() /
            self.county_insured_revenue())
        return cty_rev_as_ratio

    def actual_revenue_opt(self):
        """
        Government Crop Insurance F45: Sensitized actual revenue.
        scalar
        array(3)
        """
        actual_rev_area = ones(3) * self.cty_expected_yield
        actual_rev_area[:2] *= self.ins_harvest_price()
        actual_rev_area[2] *= self.projected_price
        return actual_rev_area

    def county_insured_revenue(self):
        """option base
        Government Crop Insurance J80: Price-sensitized county insured revenue.
        Used by RP-HPE and YO derived classes.
        array(3)
        """
        cty_insured_rev = ones(3)
        cty_insured_rev *= self.rma_cty_expected_yield
        cty_insured_rev[1:] *= self.projected_price
        cty_insured_rev[0] *= max(self.ins_harvest_price(), self.projected_price)
        return cty_insured_rev


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
