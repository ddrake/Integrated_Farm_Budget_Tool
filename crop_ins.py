"""
Module crop_ins

Contains a single class, CropIns, which loads its data from text files
for a given crop year when an instance is created.  Its main function
is to return total estimated net insurance cost for the farm for the given
crop year corresponding to an arbitrary sensitivity factor for yield.
"""
from indemnity import (IndemnityAreaRp, IndemnityAreaRpHpe, IndemnityAreaYo,
                       IndemnityEntRp, IndemnityEntRpHpe, IndemnityEntYo)


UNITS = 'area ent'.split()
PROTS = 'rp rphpe yo'.split()


class CropIns(object):
    """
    Computes total net (after payout) crop insurance cost for the farm crop year
    corresponding to an arbitrary sensitivity factor for yield.

    The optional argument 'overrides' is a dict intended to override settings
    from the data file(s).  It is primarily used to ensure that changes to key
    settings in the data files(s) do not cause tests to fail.

    Sample usage in a python or ipython console:
      from crop_ins import CropIns
      c = CropIns(2023)
      print(c.total_cost(pf=.7)        # yield factor defaults to 1
      print(c.total_cost(pf=.7, yf=.8) # specifies both price and yield factors
    """
    def __init__(self, crop_year, overrides=None):
        """
        Get an instance for the given crop year and set attributes from
        key/value pairs read from text files.
        """
        self.crop_year = crop_year
        for k, v in self._load_required_data():
            setattr(self, k, float(v) if '.' in v else int(v))
        if overrides is not None:
            for k, v in overrides.items():
                setattr(self, k, float(v) if '.' in v else int(v))
        for crop in ['corn', 'soy']:
            self.validate_settings(crop)
        self.indemnity_factory()

    def _load_required_data(self):
        """
        Load individual revenue items from data file
        return a list with all the key/value pairs
        """
        data = []
        for name in 'farm_data crop_ins_data crop_ins_premiums'.split():
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

    def indemnity_factory(self):
        """
        Provides CropIns instances with attributes such as
        indemnity_corn and sco_soy which are instances of concrete
        Indemnity classes.

        Note: ECO/SCO options can only be added to an enterprise base policy.
        In order to use the SCO option, the gov_pmt program must be PLC, but
        This rule is not enforced through validation yet.
        """
        def add_indemnity_attr(kind, attr_name, unit, prot, crop_year):
            setattr(self, attr_name,
                    (IndemnityAreaRp(crop_year, kind=kind)
                     if unit == 0 and prot == 0 else
                     IndemnityAreaRpHpe(crop_year, kind=kind)
                     if unit == 0 and prot == 1 else
                     IndemnityAreaYo(crop_year, kind=kind)
                     if unit == 0 and prot == 2 else
                     IndemnityEntRp(crop_year, kind=kind)
                     if unit == 1 and prot == 0 else
                     IndemnityEntRpHpe(crop_year, kind=kind)
                     if unit == 1 and prot == 1 else
                     IndemnityEntYo(crop_year, kind=kind)))
            return None

        for crop in ['corn', 'soy']:
            ins = self.c('insure', crop)
            add_sco = self.c('add_sco', crop)
            eco_level = self.c('eco_level', crop)
            base_unit = self.c('unit', crop)
            base_protection = self.c('protection', crop)
            if ins:
                add_indemnity_attr(
                    'base', f'indemnity_{crop}', base_unit,
                    base_protection, self.crop_year)
            if ins and add_sco:
                if base_unit != 1:
                    raise ValueError('Cannot add SCO because base unit is Area')
                add_indemnity_attr(
                    'sco', f'sco_{crop}', 0, base_protection, self.crop_year)
            if ins and eco_level > 0:
                if not add_sco:
                    raise ValueError('Cannot add ECO unless using SCO')
                add_indemnity_attr(
                    'eco', f'eco_{crop}', 0, base_protection, self.crop_year)

    def c(self, s, crop):
        """
        Helper to simplify syntax for reading crop-dependent attributes
        imported from textfile
        """
        return getattr(self, f'{s}_{crop}')

    def c4(self, unit, prot, level, crop):
        """
        Helper to concatentate four values for insurance premiums
        """
        return getattr(
            self, f'{UNITS[unit]}_{PROTS[prot]}_{crop}_{str(level)}')

    def c5(self, unit, prot, level, crop):
        """
        Helper for SCO premium lookup
        """
        lvl = f'{str(level)}_86'
        return getattr(
            self, f'{UNITS[unit]}_sco_{PROTS[prot]}_{crop}_{lvl}')

    def c6(self, unit, prot, level, crop, eco_level):
        """
        Helper for ECO premium lookup
        """
        lvl = f'86_{str(eco_level)}'
        return getattr(
            self, f'{UNITS[unit]}_eco_{PROTS[prot]}_{crop}_{lvl}')

    def validate_settings(self, crop):
        """
        Perform basic validation (sanity check) on the input data
        """
        msg = (f'insure_{crop} must be either 0 or 1'
               if self.c('insure', crop) not in (0, 1) else
               f'unit_{crop} must be either 0 or 1'
               if self.c('unit', crop) not in (0, 1) else
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
        used in calculating fuel and payroll costs
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return (
            ((self.acres_wheat_dc_soy *
              self.proj_yield_farm_dc_soy +
              (self.acres_soy -
               self.acres_wheat_dc_soy) *
              self.proj_yield_farm_full_soy) / self.acres_soy)
            if crop == 'soy' else self.proj_yield_farm_corn
            if crop == 'corn' else self.proj_yield_farm_wheat)

    def crop_ins_premium_per_acre_crop(self, crop):
        """
        Crop insurance per-acre premium based on choices of
        'unit', 'protection' and 'level' for the crop
        """
        return (self.c4(
            self.c('unit', crop), self.c('protection', crop),
            self.c('level', crop), crop)
                if self.c('insure', crop) == 1 else 0)

    def crop_ins_premium_crop(self, crop):
        """
        Crop insurance premium in dollars
        """
        return (self.crop_ins_premium_per_acre_crop(crop) *
                self.c('acres', crop))

    def sco_ins_premium_per_acre_crop(self, crop):
        """
        If the crop is not insured, return zero, otherwise, get the
        sco premium to bring coverage to 86%
        """
        return (self.c5(
            self.c('unit', crop), self.c('protection', crop),
            self.c('level', crop), crop)
                if self.c('insure', crop) == 1
                and self.c('add_sco', crop) == 1 else 0)

    def sco_ins_premium_crop(self, crop):
        """
        SCO premium in dollars
        """
        return (self.sco_ins_premium_per_acre_crop(crop) *
                self.c('acres', crop))

    def eco_ins_premium_per_acre_crop(self, crop):
        """
        If the crop is not insured or sco has not been added, return zero.
        Otherwise return premium for the specified eco level
        """
        return (self.c6(
            self.c('unit', crop), self.c('protection', crop),
            self.c('level', crop), crop, self.c('eco_level', crop))
                if self.c('insure', crop) == 1
                and self.c('add_sco', crop) == 1
                and self.c('eco_level', crop) > 0 else 0)

    def eco_ins_premium_crop(self, crop):
        """
        ECO premium in dollars
        """
        return (self.eco_ins_premium_per_acre_crop(crop) *
                self.c('acres', crop))

    def total_premium_crop(self, crop):
        """
        Return the premium for the crop insurance and option selection
        for the given crop
        """
        return (self.crop_ins_premium_crop(crop) +
                self.sco_ins_premium_crop(crop) +
                self.eco_ins_premium_crop(crop))

    def total_premium(self):
        """
        Return the premium for the crop insurance and selected options
        """
        return sum([self.total_premium_crop(crop) for crop in ['corn', 'soy']])

    def total_indemnity_crop(self, crop, pf=1, yf=1):
        """
        Return the total indemnity for the crop
        """
        return (
            (self.c('indemnity', crop).tot_indemnity_pmt_received(crop, pf, yf)
             if hasattr(self, f'sco_{crop}') else 0) +
            (self.c('sco', crop).opt_harvest_indemnity_pmt(crop, pf, yf)
             if hasattr(self, f'sco_{crop}') else 0) +
            (self.c('eco', crop).opt_harvest_indemnity_pmt(crop, pf, yf)
             if hasattr(self, f'eco_{crop}') else 0))

    def total_indemnity(self, pf=1, yf=1):
        """
        Return the total indemnity
        """
        return sum([self.total_indemnity_crop(crop, pf, yf)
                    for crop in ['corn', 'soy']])

    def net_crop_ins_indemnity_crop(self, crop, pf=1, yf=1):
        """
        Return the net crop insurance expense (subtracting indemnity)
        for the crop with given sensitivity factors
        """
        return (self.total_indemnity_crop(crop, pf, yf) -
                self.total_premium_crop(crop))

    def total_net_crop_ins_indemnity(self, pf=1, yf=1):
        return (self.total_indemnity(pf, yf) - self.total_premium())
