"""
Module indemnity

Defines a base class: Indemnity with two subclasses:
IndemnityArea and IndemnityEnt.  From these are derived
six classes which can be instantiated:

IndemnityAreaRp, IndemnityAreaRpHpe, IndemnityAreaYo
IndemnityEntRp, IndemnityEntRpHpe, IndemnityEntYo

From IndemnityArea is derived IndemnityOption,
which is a base class for three derived classes representing SCO or ECO optional
indemnities and which can be instantiated:

IndemnityOptionRp,  IndemnityOptionRpHpe and IndemnityOptionYo

Instances for specific crops are available as attributes of a CropIns instance
based on user-specified crop insurance choicies.

The concrete class instances load data from text files for a given crop year.
Their main function is to return the total indemnity payment for the farm for
the specified crop and crop year corresponding to an arbitrary sensitivity
factors for yield and price.

Note: Some methods have unused optional arguments.  This is intentional and
nessary to support the object hierarchy, the purpose of which is to eliminate
any duplication of functionality
"""
from .analysis import Analysis
from .util import crop_in, Crop


class Indemnity(Analysis):
    """
    DO NOT construct an instance of this class.  Instead get an instance of one
    of the six concrete derived classes
    """
    DATA_FILES = 'farm_data crop_ins_data crop_ins_indemnity'

    def __init__(self, crop_year, crop, *args, **kwargs):
        """
        Initialize the base class, then set some useful attributes.
        The 'kind' argument must be one of 'base', 'eco' or 'sco' and should
        correspond to the kind of Indemnity the instance represents.
        The 'crop' argument allows an Indemnity instance to know its crop.
        """
        super().__init__(crop_year, *args, **kwargs)
        self.crop = crop

    def __repr__(self):
        class_name = type(self).__name__
        return '{}({!r}, {!r})'.format(class_name, self.crop_year, self.crop)

    def revenue_trigger_feb_price(self):
        """
        Government Crop Insurance F41: The product of the actual fall harvest
        futures price in February with the yield trigger (defined in derived
        classes).
        """
        return (self.yield_trigger() *
                self.fall_futures_price[self.crop])

    def sensitized_fall_price(self, pf=1):
        """
        Government Crop Insurance F12: The price sensitized estimate of the
        fall harvest futures price.
        """
        return self.fall_fut_price_at_harvest[self.crop] * pf

    def ins_harvest_price(self, pf=1):
        """
        Government Crop Insurance F13: Insurance harvest price, limited
        to twice the price-sensitized, projected fall price.
        """
        return min((self.fall_futures_price[self.crop] *
                    self.price_cap_factor),
                   self.sensitized_fall_price(pf))

    def acres_insured(self):
        """
        Government Crop Insurance F53:
        For now, we assume that all crop acres or none are insured.
        This is not a requirement of the program and may change in the future.
        """
        return self.acres[self.crop]

    def harvest_indemnity_pmt(self, pf=1, yf=1):
        """
        Government Crop Insurance F54: Sensitized harvest indemnity payment
        in dollars.
        """
        return (self.harvest_indemnity_pmt_per_acre(pf, yf) *
                self.acres_insured())

    def rev_trigger_condition(self, pf=1, yf=1):
        """
        Helper used by revised_revenue_trigger and revenue_loss.
        """
        return (self.ins_harvest_price(pf)
                if (self.ins_harvest_price(pf) >
                    self.fall_futures_price[self.crop])
                else 0)

    def revised_revenue_trigger(self, pf=1, yf=1):
        """
        Government Crop Insurance F43: Sensitized revised revenue trigger.
        """
        return self.yield_trigger() * self.rev_trigger_condition(pf, yf)

    def revenue_loss(self, pf=1, yf=1):
        """
        Government Crop Insurance F46: Sensitized revenue loss.
        """
        return max(max(self.revenue_trigger_feb_price(),
                       self.revised_revenue_trigger(pf, yf)) -
                   self.actual_revenue(pf, yf), 0)


class IndemnityArea(Indemnity):
    """
    Base class for Area (county) Indemnity classes
    DO NOT construct an instance of this class.  Instead get an instance of one
    of the six concrete derived classes
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @crop_in(Crop.CORN, Crop.SOY, Crop.WHEAT)
    def county_rma_yield(self, crop, yf=1):
        """
        Government Crop Insurance F15: Yield-sensitized county RMA yield for the
        specified crop.  This formula works if and only if the county yields
        correlate with the farm yields.  A conservative farm to county premium
        is used.
        """
        return (self.projected_yield_crop(crop, yf) /
                (1 + self.farm_yield_premium_to_county[crop]))

    def yield_trigger(self):
        """
        Government Crop Insurance F40: Trigger based on historical county
        yield.
        """
        return (self.hist_yield_for_ins_area[self.crop] *
                self.level[self.crop] / 100)

    def actual_revenue(self, pf=1, yf=1):
        """
        Government Crop Insurance F45: Sensitized actual revenue.
        """
        return (self.county_rma_yield(self.crop, yf) *
                self.ins_harvest_price(pf))

    def payment_factor(self, pf=1, yf=1):
        """
        Government Crop Insurance F50: Sensiized payment factor.
        """
        return min(1, (self.revenue_loss(pf, yf) /
                       self.maximum_loss_pmt(pf, yf)))

    def minimum_dollars_protection(self):
        """
        Government Crop Insurance F42: Minimum dollars of protection.
        """
        return (self.hist_yield_for_ins_area[self.crop] *
                self.fall_futures_price[self.crop] *
                self.selected_pmt_factor[self.crop])

    def harvest_indemnity_pmt_per_acre(self, pf=1, yf=1):
        """
        Government Crop Insurance F52: Sensitized per acre indemnity payment
        in dollars per acre.
        """
        return (self.minimum_dollars_protection() *
                self.payment_factor(pf, yf))

    def total_indemnity_pmt_received(self, pf=1, yf=1):
        """
        Government Crop Insurance F61: Sensitized indemnity payment received.
        """
        return self.harvest_indemnity_pmt(pf, yf)


class IndemnityEnt(Indemnity):
    """
    Base class for Enterprise Indemnity classes.
    DO NOT construct an instance of this class.  Instead, get an instance of one
    of the six concrete derived classes
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def yield_trigger(self):
        """
        Government Crop Insurance J40: Yield trigger.
        """
        return (self.hist_yield_for_ins_ent[self.crop] *
                self.level[self.crop] / 100)

    def actual_revenue(self, pf=1, yf=1):
        """
        Government Crop Insurance J45: Sensitized actual revenue.
        """
        return (self.projected_yield_crop(self.crop, yf) *
                self.ins_harvest_price(pf))

    def replant_acres(self):
        """
        Government Crop Insurance J57: Replant acres expected.
        Note: replant protection option is only for Enterprise units.
        """
        return (self.replant_frac_acres_assumed[self.crop] *
                self.acres[self.crop])

    def replant_bushels(self):
        """
        Government Crop Insurance J58: Replant bushels expected.
        """
        return (self.replant_acres() *
                self.replant_yield_loss_bpa[self.crop])

    def replant_indemnity_pmt(self):
        """
        Government Crop Insurance J59: Replant payment expected.
        """
        return (self.replant_bushels() *
                self.fall_futures_price[self.crop])

    def harvest_indemnity_pmt_per_acre(self, pf=1, yf=1):
        """
        Government Crop Insurance J52: Sensitized harvest indemnity payment.
        in dollars per acre.
        """
        return self.revenue_loss(pf, yf)

    def total_indemnity_pmt_received(self, pf=1, yf=1):
        """
        Government Crop Insurance J61: Sensitized total indemnity payment.
        """
        return (self.harvest_indemnity_pmt(pf, yf) +
                self.replant_indemnity_pmt())


class IndemnityOption(IndemnityArea):
    """
    Base class for IndemnityOption classes.
    DO NOT construct an instance of this class.  Instead, get an instance of one
    of the three concrete derived classes
    """
    def __init__(self, crop_year, crop, kind, *args, **kwargs):
        super().__init__(crop_year, crop, *args, **kwargs)
        self.kind = kind
        self.lvl = None
        self.diff = None

    def __repr__(self):
        class_name = type(self).__name__
        return '{}({!r}, {!r}, {!r})'.format(class_name, self.crop_year,
                                             self.crop, self.kind)

    def county_insured_revenue(self, pf=1):
        """
        Government Crop Insurance J80: Price-sensitized county insured revenue.
        Used by RP-HPE and YO derived classes.
        """
        return (self.fall_futures_price[self.crop] *
                self.hist_yield_for_ins_area[self.crop])

    def county_rev_as_ratio(self, pf=1, yf=1):
        """
        Government Crop Insurance J81: Sensitized ratio of actual to insured
        county revenue.  Used by all derived classes.
        """
        return (self.actual_revenue(pf, yf) /
                self.county_insured_revenue(pf))

    def payment_factor(self, pf=1, yf=1):
        """
        Government Crop Insurance J82: Sensitized payment factor.
        Used by all derived classes.
        """
        return (
            0 if self.county_rev_as_ratio(pf, yf) > self.lvl else
            min((self.lvl - self.county_rev_as_ratio(pf, yf)) / self.diff, 1))

    def farm_crop_value(self, pf=1):
        """
        Government Crop Insurance J83: Price-sensitized farm crop vaue.
        Used by RP-HPE and YO derived classes.
        """
        return (self.hist_yield_for_ins_ent[self.crop] *
                self.fall_futures_price[self.crop] * self.diff)

    def harvest_indemnity_pmt_per_acre(self, pf=1, yf=1):
        """
        Government Crop Insurance J84: Sensitized harvest indemnity per acre.
        Used by all derived classes.
        """
        is_eco = self.kind == 'eco'
        level = self.level[self.crop]/100
        sco_top_level = self.sco_top_level/100
        eco_level = self.eco_level[self.crop]/100
        sco_bot_level = (level if self.sco_level[self.crop] == 1 else
                         self.sco_level[self.crop]/100)

        self.lvl = eco_level if is_eco else sco_top_level
        self.diff = ((eco_level - sco_top_level) if is_eco else
                     (sco_top_level - sco_bot_level))

        return (self.farm_crop_value(pf) *
                self.payment_factor(pf, yf))

    def harvest_indemnity_pmt(self, pf=1, yf=1):
        """
        Government Crop Insurance J86: Sensitized harvest indemnity payment.
        Used by all derived classes.
        """
        return (self.harvest_indemnity_pmt_per_acre(pf, yf) *
                self.acres_insured())


# CONCRETE INDEMNITY CLASSES
# --------------------------


class IndemnityAreaRp(IndemnityArea):
    """
    Computes crop insurance indemnity payment for County Area unit
    with RP protection for the farm crop year
    corresponding to arbitrary sensitivity factors for yield and price.
    This class is designed to be instantiated by the CropIns class.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def limiting_revenue_factor(self, pf=1):
        """
        Government Crop Insurance F48: Price-sensitized limiting revenue factor.
        """
        return (self.hist_yield_for_ins_area[self.crop] *
                max(self.fall_futures_price[self.crop],
                    self.ins_harvest_price(pf)) *
                self.loss_limit_factor)

    def maximum_loss_pmt(self, pf=1, yf=1):
        """
        Government Crop Insurance F49: Sensitized maximum loss payment.
        """
        return (max(self.revenue_trigger_feb_price(),
                    self.revised_revenue_trigger(pf, yf)) -
                self.limiting_revenue_factor(pf))

    def revised_dollars_of_protection(self, pf=1, yf=1):
        """
        Government Crop Insurance F44: Sensitized revised dollars of protection.
        """
        return (self.hist_yield_for_ins_area[self.crop] *
                self.selected_pmt_factor[self.crop] *
                self.rev_trigger_condition(pf, yf))

    def harvest_indemnity_pmt_per_acre(self, pf=1, yf=1):
        """
        Government Crop Insurance F52: Sensitized harvest indemnity
        in dollars per acre.
        """
        return (max(self.minimum_dollars_protection(),
                    self.revised_dollars_of_protection(pf, yf)) *
                self.payment_factor(pf, yf))


class IndemnityAreaRpHpe(IndemnityArea):
    """
    Computes crop insurance indemnity payment for County Area unit
    with RP-HPE protection for the farm crop year
    corresponding to arbitrary sensitivity factors for yield and price.
    This class is designed to be instantiated by the CropIns class.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def revenue_loss(self, pf=1, yf=1):
        """
        Government Crop Insurance G46: Sensitized revenue loss.
        """
        return max((self.revenue_trigger_feb_price() -
                    self.actual_revenue(pf, yf)), 0)

    def limiting_revenue_factor(self):
        """
        Government Crop Insurance G48: Limiting revenue factor.
        """
        return (self.hist_yield_for_ins_area[self.crop] *
                self.fall_futures_price[self.crop] *
                self.loss_limit_factor)

    def maximum_loss_pmt(self, pf=1, yf=1):
        """
        Government Crop Insurance G49: Sensitized maximum loss payment.
        yf and pf are not used here (see note in module docstring), but
        payment_factor needs to pass them (the RP method needs them).
        """
        return (self.revenue_trigger_feb_price() -
                self.limiting_revenue_factor())


class IndemnityAreaYo(IndemnityArea):
    """
    Computes crop insurance indemnity payment for County Area unit
    with YO protection for the farm crop year
    corresponding to arbitrary sensitivity factors for yield and price.
    This class is designed to be instantiated by the CropIns class.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def limiting_revenue_factor(self):
        """
        Government Crop Insurance H48: Limiting revenue factor.
        """
        return (self.hist_yield_for_ins_area[self.crop] *
                self.loss_limit_factor)

    def yield_shortfall(self, yf=1):
        """
        Government Crop Insurance H47: Price-sensitized yield shortfall.
        """
        return max((self.yield_trigger() -
                    self.county_rma_yield(self.crop, yf)), 0)

    def payment_factor(self, pf=1, yf=1):
        """
        Government Crop Insurance H50: Sensitized payment factor.
        """
        return min(1, (self.yield_shortfall(yf) /
                       self.maximum_loss_pmt(pf, yf)))

    def maximum_loss_pmt(self, pf=1, yf=1):
        """
        Government Crop Insurance H49: Maximum loss payment.
        """
        return (self.yield_trigger() -
                self.limiting_revenue_factor())


class IndemnityEntRp(IndemnityEnt):
    """
    Computes crop insurance indemnity payment for Enterprise unit
    with RP protection for the farm crop year
    corresponding to arbitrary sensitivity factors for yield and price.
    This class is designed to be instantiated by the CropIns class.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class IndemnityEntRpHpe(IndemnityEnt):
    """
    Computes crop insurance indemnity payment for Enterprise unit
    with RP-HPE protection for the farm crop year
    corresponding to arbitrary sensitivity factors for yield and price.
    This class is designed to be instantiated by the CropIns class.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def revised_revenue_trigger(self, pf=1, yf=1):
        """
        Government Crop Insurance K43: Price-sensitized revised revenue
        trigger.
        """
        return (self.yield_trigger() *
                (0 if (self.ins_harvest_price(pf) >
                       self.fall_futures_price[self.crop])
                else self.fall_futures_price[self.crop]))


class IndemnityEntYo(IndemnityEnt):
    """
    Computes crop insurance indemnity payment for Enterprise unit
    with YO protection for the farm crop year
    corresponding to arbitrary sensitivity factors for yield and price.
    This class is designed to be instantiated by the CropIns class.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def yield_shortfall(self, yf=1):
        """
        Government Crop Insurance L47: Yield-sensitized yield shortfall.
        """
        return max((self.yield_trigger() -
                    self.projected_yield_crop(self.crop, yf)), 0)

    def harvest_indemnity_pmt_per_acre(self, pf=1, yf=1):
        """
        Government Crop Insurance L52: Yield-sensitized harvest indemnity payment
        in dollars per acre.
        """
        return (self.yield_shortfall(yf) *
                self.fall_futures_price[self.crop])


# INDEMNITY OPTION CONCRETE CLASSES
# ---------------------------------


class IndemnityOptionRp(IndemnityOption):
    """
    An indemnity option (SCO or ECO) with RP protection
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def county_insured_revenue(self, pf=1):
        """
        Government Crop Insurance J80: Price-sensitized county insured revenue.
        """
        return (self.hist_yield_for_ins_area[self.crop] *
                max(self.ins_harvest_price(pf),
                    self.fall_futures_price[self.crop]))

    def farm_crop_value(self, pf=1):
        """
        Government Crop Insurance J83: Price-sensitized farm crop value.
        """
        return (self.hist_yield_for_ins_ent[self.crop] *
                max(self.ins_harvest_price(pf),
                    self.fall_futures_price[self.crop]) * self.diff)


class IndemnityOptionRpHpe(IndemnityOption):
    """
    An indemnity option (SCO or ECO) with RP-HPE protection
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class IndemnityOptionYo(IndemnityOption):
    """
    An indemnity option (SCO or ECO) with YO protection
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def actual_revenue(self, pf=1, yf=1):
        """
        Government Crop Insurance J79: Yield-sensitized county actual revenue.
        """
        return (self.fall_futures_price[self.crop] *
                self.county_rma_yield(self.crop, yf))
