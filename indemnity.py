"""
Module indemnity

Contains an abstract base class: Indemnity, two abstract subclasses:
IndemnityArea and IndemnityEnt.  From these latter two are derived
six concrete subclasses:

IndemnityAreaRp, IndemnityAreaRpHpe, IndemnityAreaYo
IndemnityEntRp, IndemnityEntRpHpe, IndemnityEntYo
which override certain methods in the base class.

Instances of one or two of these subclasses will be selected by CropIns
instances to compute the indemnity for a specified configuration.

The concrete class instances load data from text files
for a given crop year.  Their main function
is to return the total indemnity payment for the farm for the specified
crop and crop year corresponding to an arbitrary sensitivity factors
for yield and price.

Note: Some methods have unused optional arguments.  This is intentional and
nessary to support the object hierarchy, the purpose of which is to eliminate
any duplication of functionality

Note: Some docstrings currently reference cells on the Crop Insurance sheet
This may be helpful for debugging and testing in the short run.
"""

UNITS = 'area ent'.split()
PROTS = 'rp rphpe yo'.split()


class Indemnity(object):
    """
    DO NOT construct an instance of this class.  Instead get an instance of one
    of the six concrete derived classes
    """
    def __init__(self, crop_year, kind='base'):
        """
        The optional argument kind should be 'base', 'sco' or 'eco'
        Get an instance for the given crop year and set attributes from
        key/value pairs read from text files.
        """
        self.crop_year = crop_year
        self.kind = kind
        for k, v in self._load_required_data():
            setattr(self, k, float(v) if '.' in v else int(v))
        for crop in ['corn', 'soy']:
            self.validate_settings(crop)

    def _load_required_data(self):
        """
        Load individual revenue items from data file
        return a list with all the key/value pairs
        """
        data = []
        for name in 'farm_data crop_ins_data crop_ins_indemnity'.split():
            data += self._load_textfile(f'{self.crop_year}_{name}.txt')
        return data

    def _load_textfile(self, filename):
        """
        Load a textfile with the given name into a list of key/value pairs,
        ignoring blank lines and comment lines that begin with '#'
        """
        with open(filename) as f:
            contents = f.read()

        lines = contents.strip().split('\n')
        lines = filter(lambda line: len(line) > 0 and line[0] != '#',
                       [line.strip() for line in lines])
        return [line.split() for line in lines]

    def c(self, s, crop):
        """
        Helper to simplify syntax for reading crop-dependent attributes
        created via import from textfile
        """
        return getattr(self, f'{s}_{crop}')

    def validate_settings(self, crop):
        """
        Perform basic validation (sanity check) on the input data
        """
        msg = (f'insure_{crop} must be either 0 or 1'
               if self.c('insure', crop) not in (0, 1) else
               f'protection_{crop} must be 0, 1 or 2'
               if self.c('protection', crop) not in [0, 1, 2] else
               f'level_{crop} must be one of: 50, 55, ..., or 85'
               if self.c('level', crop) not in
               [50 + 5*i for i in range(8)] else
               f'add_sco_{crop} must be 0 or 1'
               if self.c('add_sco', crop) not in [0, 1] else
               f'eco_{crop} must be 0, 90 or 95'
               if self.c('eco_level', crop) not in [0, 90, 95] else '')
        if len(msg) > 0:
            raise ValueError(f'Invalid setting(s) in text file: {msg}.')

    def proj_yield_farm_crop(self, crop):
        """
        Helper method providing projected yields for all crops
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return (
            ((self.acres_wheat_dc_soy *
              self.proj_yield_farm_dc_soy +
              (self.acres_soy -
               self.acres_wheat_dc_soy) *
              self.proj_yield_farm_full_soy) / self.acres_soy)
            if crop == 'soy' else self.proj_yield_farm_corn)

    def revenue_trigger_feb_price(self, crop):
        """
        F41
        """
        return (self.yield_trigger(crop) *
                self.c('spring_proj_harv_price', crop))

    def sensitized_fall_price(self, crop, pf=1):
        """
        F12
        """
        return self.c('fall_fut_price_at_harvest', crop) * pf

    def ins_harvest_price(self, crop, pf=1):
        """
        F13
        """
        return min((self.c('spring_proj_harv_price', crop) *
                    self.price_cap_factor),
                   self.sensitized_fall_price(crop, pf))

    def sensitized_yield(self, crop, yf=1):
        """
        F14  Leave in base class, not needed for Area logic, but nice to have
        """
        return self.proj_yield_farm_crop(crop) * yf

    def acres_insured(self, crop):
        """
        F53
        For now, we assume that all crop acres or none are applied
        This is not always the case and may change in the future.
        """
        return self.c('acres', crop)

    def harvest_indemnity_pmt(self, crop, pf=1, yf=1):
        """
        F54 in dollars
        """
        return (self.harvest_indemnity_pmt_per_acre(crop, pf, yf) *
                self.acres_insured(crop))

    def rev_trigger_condition(self, crop, pf=1, yf=1):
        """
        Helper used by two methods
        """
        return (self.ins_harvest_price(crop, pf)
                if (self.ins_harvest_price(crop, pf) >
                    self.c('spring_proj_harv_price', crop))
                else 0)

    def revised_revenue_trigger(self, crop, pf=1, yf=1):
        """
        F43
        """
        return self.yield_trigger(crop) * self.rev_trigger_condition(crop, pf, yf)

    def revenue_loss(self, crop, pf=1, yf=1):
        """
        F46
        """
        return max(max(self.revenue_trigger_feb_price(crop),
                       self.revised_revenue_trigger(crop, pf, yf)) -
                   self.actual_revenue(crop, pf, yf), 0)


class IndemnityArea(Indemnity):
    """
    DO NOT construct an instance of this class.  Instead get an instance of one
    of the six concrete derived classes
    """
    def __init__(self, *args, **kwargs):
        super(IndemnityArea, self).__init__(*args, **kwargs)

    def yield_trigger(self, crop):
        """
        F40
        """
        return (self.c('hist_yield_for_ins_area', crop) *
                self.c('level', crop) / 100)

    def sensitized_cty_rma_yield(self, crop, yf=1):
        return self.c('assumed_cty_rma_yield', crop) * yf

    def actual_revenue(self, crop, pf=1, yf=1):
        """
        F45
        """
        return (self.sensitized_cty_rma_yield(crop, yf) *
                self.ins_harvest_price(crop, pf))

    def payment_factor(self, crop, pf=1, yf=1):
        """
        F50
        """
        return min(1, (self.revenue_loss(crop, pf, yf) /
                       self.maximum_loss_payment(crop, yf)))

    def minimum_dollars_protection(self, crop):
        """
        F42
        """
        return (self.c('hist_yield_for_ins_area', crop) *
                self.c('spring_proj_harv_price', crop) *
                self.c('selected_payment_factor', crop))

    def harvest_indemnity_pmt_per_acre(self, crop, pf=1, yf=1):
        """
        F52 (in dollars per acre)
        """
        return (self.minimum_dollars_protection(crop) *
                self.payment_factor(crop, pf, yf))

    def tot_indemnity_pmt_received(self, crop, pf=1, yf=1):
        """
        F61
        """
        return self.harvest_indemnity_pmt(crop, pf, yf)

    # SCO/ECO methods - Only avaliable for Area
    # -----------------------------------------

    def opt_county_actual_revenue(self, crop, pf=1, yf=1):
        """
        J79 For RP and RP-HPE
        """
        return (self.ins_harvest_price(crop, pf) *
                self.sensitized_cty_rma_yield(crop, yf))

    def opt_county_insured_revenue(self, crop, pf=1):
        """
        J80 for RP-HPE and YO
        """
        return (self.c('spring_proj_harv_price', crop) *
                self.c('hist_yield_for_ins_area', crop))

    def opt_cty_rev_as_ratio(self, crop, pf=1, yf=1):
        """
        J81 same for all
        """
        return (self.opt_county_actual_revenue(crop, pf, yf) /
                self.opt_county_insured_revenue(crop, pf))

    def opt_payment_factor(self, lvl, diff, crop, pf=1, yf=1):
        """
        J82 same for all
        """
        return (
            0 if self.opt_cty_rev_as_ratio(crop, pf, yf) > lvl else
            min((lvl - self.opt_cty_rev_as_ratio(crop, pf, yf)) / diff, 1))

    def opt_farm_crop_value(self, diff, crop, pf=1):
        """
        J83 for RP-HPE and YO
        """
        return (self.c('hist_yield_for_ins_ent', crop) *
                self.c('spring_proj_harv_price', crop) * diff)

    def opt_harvest_indemnity_per_acre(self, crop, pf=1, yf=1):
        """
        J84 same for all
        """
        is_eco = self.kind == 'eco'
        lvl = (self.c('eco_level', crop) if is_eco else self.sco_level)/100
        diff = ((lvl - self.sco_level/100)
                if is_eco else (self.sco_level - self.c('level', crop))/100)

        return (self.opt_farm_crop_value(diff, crop, pf) *
                self.opt_payment_factor(lvl, diff, crop, pf, yf))

    def opt_harvest_indemnity_pmt(self, crop, pf=1, yf=1):
        """
        J86 same for all
        """
        return (self.opt_harvest_indemnity_per_acre(crop, pf, yf) *
                self.acres_insured(crop))


class IndemnityEnt(Indemnity):
    """
    DO NOT construct an instance of this class.  Instead get an instance of one
    of the six concrete derived classes
    """
    def __init__(self, *args, **kwargs):
        super(IndemnityEnt, self).__init__(*args, **kwargs)

    def yield_trigger(self, crop):
        """
        F40
        """
        return (self.c('hist_yield_for_ins_ent', crop) *
                self.c('level', crop) / 100)

    def actual_revenue(self, crop, pf=1, yf=1):
        """
        J45 all classes excep yo  (Ent version)
        """
        return (self.sensitized_yield(crop, yf) *
                self.ins_harvest_price(crop, pf))

    def replant_acres(self, crop):
        """
        J57
        """
        return (self.c('replant_frac_acres_assumed', crop) *
                self.c('acres', crop))

    def replant_bushels(self, crop):
        """
        J58
        """
        return (self.replant_acres(crop) *
                self.c('replant_yield_loss_bpa', crop))

    def replant_indemnity_pmt(self, crop):
        """
        J59
        """
        return (self.replant_bushels(crop) *
                self.c('spring_proj_harv_price', crop))

    def harvest_indemnity_pmt_per_acre(self, crop, pf=1, yf=1):
        """
        F52 (in dollars per acre)
        """
        return self.revenue_loss(crop, pf, yf)

    def tot_indemnity_pmt_received(self, crop, pf=1, yf=1):
        """
        F61
        """
        return (self.harvest_indemnity_pmt(crop, pf, yf) +
                self.replant_indemnity_pmt(crop))


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
        super(IndemnityAreaRp, self).__init__(*args, **kwargs)

    def limiting_revenue_factor(self, crop, pf=1):
        """
        F48 different for all three Area classes
        """
        return (self.c('hist_yield_for_ins_area', crop) *
                max(self.c('spring_proj_harv_price', crop),
                    self.ins_harvest_price(crop, pf)) *
                self.loss_limit_factor)

    def maximum_loss_payment(self, crop, pf=1, yf=1):
        """
        F49  different for all three concrete Area classes
        """
        return (max(self.revenue_trigger_feb_price(crop),
                    self.revised_revenue_trigger(crop, pf, yf)) -
                self.limiting_revenue_factor(crop))

    def revised_dollars_of_protection(self, crop, pf=1, yf=1):
        """
        F44 method exists for this concrete class only
        """
        return (self.c('hist_yield_for_ins_area', crop) *
                self.c('selected_payment_factor', crop) *
                self.rev_trigger_condition(crop, pf, yf))

    def harvest_indemnity_pmt_per_acre(self, crop, pf=1, yf=1):
        """
        F52 (in dollars per acre) overrides method in IndemnityArea
        """
        return (max(self.minimum_dollars_protection(crop),
                    self.revised_dollars_of_protection(crop, pf, yf)) *
                self.payment_factor(crop, pf, yf))

    # SCO/ECO overrides
    # -----------------

    def opt_county_insured_revenue(self, crop, pf=1):
        """
        J80 Only for RP
        """
        return (self.c('hist_yield_for_ins_area', crop) *
                max(self.ins_harvest_price(crop, pf),
                    self.c('spring_proj_harv_price', crop)))

    def opt_farm_crop_value(self, diff, crop, pf=1):
        """
        J83 Only for RP
        """
        return (self.c('hist_yield_for_ins_ent', crop) *
                max(self.ins_harvest_price(crop, pf),
                    self.c('spring_proj_harv_price', crop)) * diff)


class IndemnityAreaRpHpe(IndemnityArea):
    """
    Computes crop insurance indemnity payment for County Area unit
    with RP-HPE protection for the farm crop year
    corresponding to arbitrary sensitivity factors for yield and price.
    This class is designed to be instantiated by the CropIns class.
    """

    def __init__(self, *args, **kwargs):
        super(IndemnityAreaRpHpe, self).__init__(*args, **kwargs)

    def revenue_loss(self, crop, pf=1, yf=1):
        """
        F46 Overrides method in Area RP-HPE
        """
        return max((self.revenue_trigger_feb_price(crop) -
                    self.actual_revenue(crop, pf, yf)), 0)

    def limiting_revenue_factor(self, crop, pf=1):
        """
        F48 different for all three Area classes
        """
        return (self.c('hist_yield_for_ins_area', crop) *
                self.ins_harvest_price(crop, pf) *
                self.loss_limit_factor)

    def maximum_loss_payment(self, crop, yf=1):
        """
        F49  different for all three concrete Area classes
        we don't use yf here, but payment_factor needs to pass it
        because the RP class needs it.
        """
        return (self.revenue_trigger_feb_price(crop) -
                self.limiting_revenue_factor(crop))


class IndemnityAreaYo(IndemnityArea):
    """
    Computes crop insurance indemnity payment for County Area unit
    with YO protection for the farm crop year
    corresponding to arbitrary sensitivity factors for yield and price.
    This class is designed to be instantiated by the CropIns class.
    """

    def __init__(self, *args, **kwargs):
        super(IndemnityAreaYo, self).__init__(*args, **kwargs)

    def limiting_revenue_factor(self, crop):
        """
        F48 different for all three Area classes
        """
        return (self.c('hist_yield_for_ins_area', crop) *
                self.loss_limit_factor)

    def yield_shortfall(self, crop, yf=1):
        """
        47  different for both AreaYo and EntYo
        """
        return max((self.yield_trigger(crop) -
                    self.sensitized_cty_rma_yield(crop, yf)), 0)

    def payment_factor(self, crop, pf=1, yf=1):
        """
        F50 Overrides method in IndemnityArea
        """
        return min(1, (self.yield_shortfall(crop, yf) /
                       self.maximum_loss_payment(crop, yf)))

    def maximum_loss_payment(self, crop, yf=1):
        """
        F49
        """
        return (self.yield_trigger(crop) -
                self.limiting_revenue_factor(crop))

    # SCO/ECO overrides
    # -----------------

    def opt_county_actual_revenue(self, crop, pf=1, yf=1):
        """
        J79
        """
        return (self.c('spring_proj_harv_price', crop) *
                self.sensitized_cty_rma_yield(crop, yf))


class IndemnityEntRp(IndemnityEnt):
    """
    Computes crop insurance indemnity payment for Enterprise unit
    with RP protection for the farm crop year
    corresponding to arbitrary sensitivity factors for yield and price.
    This class is designed to be instantiated by the CropIns class.
    """
    def __init__(self, *args, **kwargs):
        super(IndemnityEntRp, self).__init__(*args, **kwargs)


class IndemnityEntRpHpe(IndemnityEnt):
    """
    Computes crop insurance indemnity payment for Enterprise unit
    with RP-HPE protection for the farm crop year
    corresponding to arbitrary sensitivity factors for yield and price.
    This class is designed to be instantiated by the CropIns class.
    """
    def __init__(self, *args, **kwargs):
        super(IndemnityEntRpHpe, self).__init__(*args, **kwargs)

    def revised_revenue_trigger(self, crop, pf=1, yf=1):
        """
        F43
        """
        return (self.yield_trigger(crop) *
                (0 if (self.ins_harvest_price(crop, pf) >
                       self.c('spring_proj_harv_price', crop))
                else self.c('spring_proj_harv_price', crop)))


class IndemnityEntYo(IndemnityEnt):
    """
    Computes crop insurance indemnity payment for Enterprise unit
    with YO protection for the farm crop year
    corresponding to arbitrary sensitivity factors for yield and price.
    This class is designed to be instantiated by the CropIns class.
    """
    def __init__(self, *args, **kwargs):
        super(IndemnityEntYo, self).__init__(*args, **kwargs)

    def yield_shortfall(self, crop, yf=1):
        """
        47
        """
        return max((self.yield_trigger(crop) -
                    self.sensitized_yield(crop, yf)), 0)

    def harvest_indemnity_pmt_per_acre(self, crop, pf=1, yf=1):
        """
        F52 (in dollars per acre)
        """
        return (self.yield_shortfall(crop, yf) *
                self.c('spring_proj_harv_price', crop))
