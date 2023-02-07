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
    def __init__(self, crop_year, crop, kind='base'):
        """
        The optional argument kind should be 'base', 'sco' or 'eco'
        Get an instance for the given crop year and set attributes from
        key/value pairs read from text files.
        """
        self.crop_year = crop_year
        self.crop = crop
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

    def proj_yield_farm(self):
        """
        Helper method providing projected yields for all crops
        """
        return (
            ((self.acres_wheat_dc_soy *
              self.proj_yield_farm_dc_soy +
              (self.acres_soy -
               self.acres_wheat_dc_soy) *
              self.proj_yield_farm_full_soy) / self.acres_soy)
            if self.crop == 'soy' else self.proj_yield_farm_corn)

    def revenue_trigger_feb_price(self):
        """
        F41
        """
        return (self.yield_trigger() *
                self.c('spring_proj_harv_price', self.crop))

    def sensitized_fall_price(self, pf=1):
        """
        F12
        """
        return self.c('fall_fut_price_at_harvest', self.crop) * pf

    def ins_harvest_price(self, pf=1):
        """
        F13
        """
        return min((self.c('spring_proj_harv_price', self.crop) *
                    self.price_cap_factor),
                   self.sensitized_fall_price(pf))

    def sensitized_yield(self, yf=1):
        """
        F14  Leave in base class, not needed for Area logic, but nice to have
        """
        return self.proj_yield_farm() * yf

    def acres_insured(self):
        """
        F53
        For now, we assume that all crop acres or none are applied
        This is not always the case and may change in the future.
        """
        return self.c('acres', self.crop)

    def harvest_indemnity_pmt(self, pf=1, yf=1):
        """
        F54 in dollars
        """
        return (self.harvest_indemnity_pmt_per_acre(pf, yf) *
                self.acres_insured())

    def rev_trigger_condition(self, pf=1, yf=1):
        """
        Helper used by two methods
        """
        return (self.ins_harvest_price(pf)
                if (self.ins_harvest_price(pf) >
                    self.c('spring_proj_harv_price', self.crop))
                else 0)

    def revised_revenue_trigger(self, pf=1, yf=1):
        """
        F43
        """
        return self.yield_trigger() * self.rev_trigger_condition(pf, yf)

    def revenue_loss(self, pf=1, yf=1):
        """
        F46
        """
        return max(max(self.revenue_trigger_feb_price(),
                       self.revised_revenue_trigger(pf, yf)) -
                   self.actual_revenue(pf, yf), 0)


class IndemnityArea(Indemnity):
    """
    DO NOT construct an instance of this class.  Instead get an instance of one
    of the six concrete derived classes
    """
    def __init__(self, *args, **kwargs):
        super(IndemnityArea, self).__init__(*args, **kwargs)

    def yield_trigger(self):
        """
        F40
        """
        return (self.c('hist_yield_for_ins_area', self.crop) *
                self.c('level', self.crop) / 100)

    def sensitized_cty_rma_yield(self, yf=1):
        return self.c('assumed_cty_rma_yield', self.crop) * yf

    def actual_revenue(self, pf=1, yf=1):
        """
        F45
        """
        return (self.sensitized_cty_rma_yield(yf) *
                self.ins_harvest_price(pf))

    def payment_factor(self, pf=1, yf=1):
        """
        F50
        """
        return min(1, (self.revenue_loss(pf, yf) /
                       self.maximum_loss_payment(pf, yf)))

    def minimum_dollars_protection(self):
        """
        F42
        """
        return (self.c('hist_yield_for_ins_area', self.crop) *
                self.c('spring_proj_harv_price', self.crop) *
                self.c('selected_payment_factor', self.crop))

    def harvest_indemnity_pmt_per_acre(self, pf=1, yf=1):
        """
        F52 (in dollars per acre)
        """
        return (self.minimum_dollars_protection() *
                self.payment_factor(pf, yf))

    def tot_indemnity_pmt_received(self, pf=1, yf=1):
        """
        F61
        """
        return self.harvest_indemnity_pmt(pf, yf)

    # SCO/ECO methods - Only avaliable for Area
    # -----------------------------------------

    def opt_county_actual_revenue(self, pf=1, yf=1):
        """
        J79 For RP and RP-HPE
        """
        return (self.ins_harvest_price(pf) *
                self.sensitized_cty_rma_yield(yf))

    def opt_county_insured_revenue(self, pf=1):
        """
        J80 for RP-HPE and YO
        """
        return (self.c('spring_proj_harv_price', self.crop) *
                self.c('hist_yield_for_ins_area', self.crop))

    def opt_cty_rev_as_ratio(self, pf=1, yf=1):
        """
        J81 same for all
        """
        return (self.opt_county_actual_revenue(pf, yf) /
                self.opt_county_insured_revenue(pf))

    def opt_payment_factor(self, pf=1, yf=1):
        """
        J82 same for all
        """
        return (
            0 if self.opt_cty_rev_as_ratio(pf, yf) > self.lvl else
            min((self.lvl - self.opt_cty_rev_as_ratio(pf, yf)) / self.diff, 1))

    def opt_farm_crop_value(self, pf=1):
        """
        J83 for RP-HPE and YO
        """
        return (self.c('hist_yield_for_ins_ent', self.crop) *
                self.c('spring_proj_harv_price', self.crop) * self.diff)

    def opt_harvest_indemnity_per_acre(self, pf=1, yf=1):
        """
        J84 same for all
        """
        is_eco = self.kind == 'eco'
        self.lvl = (self.c('eco_level', self.crop) if is_eco else self.sco_level)/100
        self.diff = ((self.lvl - self.sco_level/100)
                     if is_eco else (self.sco_level - self.c('level', self.crop))/100)

        return (self.opt_farm_crop_value(pf) *
                self.opt_payment_factor(pf, yf))

    def opt_harvest_indemnity_pmt(self, pf=1, yf=1):
        """
        J86 same for all
        """
        return (self.opt_harvest_indemnity_per_acre(pf, yf) *
                self.acres_insured())

# CONCRETE INDEMNITY AREA CLASSES
# -------------------------------


class IndemnityAreaRp(IndemnityArea):
    """
    Computes crop insurance indemnity payment for County Area unit
    with RP protection for the farm crop year
    corresponding to arbitrary sensitivity factors for yield and price.
    This class is designed to be instantiated by the CropIns class.
    """

    def __init__(self, *args, **kwargs):
        super(IndemnityAreaRp, self).__init__(*args, **kwargs)

    def limiting_revenue_factor(self, pf=1):
        """
        F48 different for all three Area classes
        """
        return (self.c('hist_yield_for_ins_area', self.crop) *
                max(self.c('spring_proj_harv_price', self.crop),
                    self.ins_harvest_price(pf)) *
                self.loss_limit_factor)

    def maximum_loss_payment(self, pf=1, yf=1):
        """
        F49  different for all three concrete Area classes
        """
        return (max(self.revenue_trigger_feb_price(),
                    self.revised_revenue_trigger(pf, yf)) -
                self.limiting_revenue_factor(pf))

    def revised_dollars_of_protection(self, pf=1, yf=1):
        """
        F44 method exists for this concrete class only
        """
        return (self.c('hist_yield_for_ins_area', self.crop) *
                self.c('selected_payment_factor', self.crop) *
                self.rev_trigger_condition(pf, yf))

    def harvest_indemnity_pmt_per_acre(self, pf=1, yf=1):
        """
        F52 (in dollars per acre) overrides method in IndemnityArea
        """
        return (max(self.minimum_dollars_protection(),
                    self.revised_dollars_of_protection(pf, yf)) *
                self.payment_factor(pf, yf))

    # SCO/ECO overrides
    # -----------------

    def opt_county_insured_revenue(self, pf=1):
        """
        J80 Only for RP
        """
        return (self.c('hist_yield_for_ins_area', self.crop) *
                max(self.ins_harvest_price(pf),
                    self.c('spring_proj_harv_price', self.crop)))

    def opt_farm_crop_value(self, pf=1):
        """
        J83 Only for RP
        """
        return (self.c('hist_yield_for_ins_ent', self.crop) *
                max(self.ins_harvest_price(pf),
                    self.c('spring_proj_harv_price', self.crop)) * self.diff)


class IndemnityAreaRpHpe(IndemnityArea):
    """
    Computes crop insurance indemnity payment for County Area unit
    with RP-HPE protection for the farm crop year
    corresponding to arbitrary sensitivity factors for yield and price.
    This class is designed to be instantiated by the CropIns class.
    """

    def __init__(self, *args, **kwargs):
        super(IndemnityAreaRpHpe, self).__init__(*args, **kwargs)

    def revenue_loss(self, pf=1, yf=1):
        """
        F46 Overrides method in Area RP-HPE
        """
        return max((self.revenue_trigger_feb_price() -
                    self.actual_revenue(pf, yf)), 0)

    def limiting_revenue_factor(self):
        """
        F48 different for all three Area classes
        """
        return (self.c('hist_yield_for_ins_area', self.crop) *
                self.c('spring_proj_harv_price', self.crop) *
                self.loss_limit_factor)

    def maximum_loss_payment(self, pf=1, yf=1):
        """
        F49  different for all three concrete Area classes
        we don't use yf or pf here, but payment_factor needs to pass them
        because the RP class needs it.
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
        super(IndemnityAreaYo, self).__init__(*args, **kwargs)

    def limiting_revenue_factor(self):
        """
        F48 different for all three Area classes
        """
        return (self.c('hist_yield_for_ins_area', self.crop) *
                self.loss_limit_factor)

    def yield_shortfall(self, yf=1):
        """
        47  different for both AreaYo and EntYo
        """
        return max((self.yield_trigger() -
                    self.sensitized_cty_rma_yield(yf)), 0)

    def payment_factor(self, pf=1, yf=1):
        """
        F50 Overrides method in IndemnityArea
        """
        return min(1, (self.yield_shortfall(yf) /
                       self.maximum_loss_payment(pf, yf)))

    def maximum_loss_payment(self, pf=1, yf=1):
        """
        F49
        """
        return (self.yield_trigger() -
                self.limiting_revenue_factor())

    # SCO/ECO overrides
    # -----------------

    def opt_county_actual_revenue(self, pf=1, yf=1):
        """
        J79
        """
        return (self.c('spring_proj_harv_price', self.crop) *
                self.sensitized_cty_rma_yield(yf))


class IndemnityEnt(Indemnity):
    """
    DO NOT construct an instance of this class.  Instead get an instance of one
    of the six concrete derived classes
    """
    def __init__(self, *args, **kwargs):
        super(IndemnityEnt, self).__init__(*args, **kwargs)

    def yield_trigger(self):
        """
        F40
        """
        return (self.c('hist_yield_for_ins_ent', self.crop) *
                self.c('level', self.crop) / 100)

    def actual_revenue(self, pf=1, yf=1):
        """
        J45 all classes excep yo  (Ent version)
        """
        return (self.sensitized_yield(yf) *
                self.ins_harvest_price(pf))

    def replant_acres(self):
        """
        J57
        """
        return (self.c('replant_frac_acres_assumed', self.crop) *
                self.c('acres', self.crop))

    def replant_bushels(self):
        """
        J58
        """
        return (self.replant_acres() *
                self.c('replant_yield_loss_bpa', self.crop))

    def replant_indemnity_pmt(self):
        """
        J59
        """
        return (self.replant_bushels() *
                self.c('spring_proj_harv_price', self.crop))

    def harvest_indemnity_pmt_per_acre(self, pf=1, yf=1):
        """
        F52 (in dollars per acre)
        """
        return self.revenue_loss(pf, yf)

    def tot_indemnity_pmt_received(self, pf=1, yf=1):
        """
        F61
        """
        return (self.harvest_indemnity_pmt(pf, yf) +
                self.replant_indemnity_pmt())


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

    def revised_revenue_trigger(self, pf=1, yf=1):
        """
        F43
        """
        return (self.yield_trigger() *
                (0 if (self.ins_harvest_price(pf) >
                       self.c('spring_proj_harv_price', self.crop))
                else self.c('spring_proj_harv_price', self.crop)))


class IndemnityEntYo(IndemnityEnt):
    """
    Computes crop insurance indemnity payment for Enterprise unit
    with YO protection for the farm crop year
    corresponding to arbitrary sensitivity factors for yield and price.
    This class is designed to be instantiated by the CropIns class.
    """
    def __init__(self, *args, **kwargs):
        super(IndemnityEntYo, self).__init__(*args, **kwargs)

    def yield_shortfall(self, yf=1):
        """
        47
        """
        return max((self.yield_trigger() -
                    self.sensitized_yield(yf)), 0)

    def harvest_indemnity_pmt_per_acre(self, pf=1, yf=1):
        """
        F52 (in dollars per acre)
        """
        return (self.yield_shortfall(yf) *
                self.c('spring_proj_harv_price', self.crop))
