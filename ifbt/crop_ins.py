"""
Module crop_ins

Contains a single class, CropIns, which loads its data from text files
for a given crop year when an instance is created.  Its main function
is to return total estimated net insurance cost for the farm for the given
crop year corresponding to an arbitrary sensitivity factor for yield.
"""
from .analysis import Analysis, crop_in
from .indemnity import (IndemnityAreaRp, IndemnityAreaRpHpe, IndemnityAreaYo,
                        IndemnityEntRp, IndemnityEntRpHpe, IndemnityEntYo,
                        IndemnityOptionRp, IndemnityOptionRpHpe, IndemnityOptionYo)
NO, YES = (0, 1)
AREA, ENT = (0, 1)
RP, RPHPE, YO = (0, 1, 2)
NONE, DFLT = (0, 1)

UNITS = 'area ent'.split()
PROTS = 'rp rphpe yo'.split()


class CropIns(Analysis):
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
    DATA_FILES = 'farm_data crop_ins_data crop_ins_premiums'

    def __init__(self, *args, **kwargs):
        super(CropIns, self).__init__(*args, **kwargs)
        for crop in ['corn', 'soy']:
            self.validate_settings(crop)
        self.indemnity_factory()

    def validate_settings(self, crop):
        """
        Perform basic validation (sanity check) on the input data
        """
        msg = (f'insure_{crop} must be either 0 or 1'
               if self.c('insure', crop) not in (0, 1) else
               f'unit_{crop} must be either 0 or 1'
               if self.c('unit', crop) not in (0, 1) else
               f'protection_{crop} must be 0, 1 or 2'
               if self.c('protection', crop) not in (0, 1, 2) else
               f'level_{crop} must be one of: 50, 55, ..., or 85'
               if (self.c('unit', crop) == 1 and self.c('level', crop)
                   not in range(50, 86, 5)) else
               f'level_{crop} must be one of: 70, 75, ..., or 90'
               if (self.c('unit', crop) == 0 and self.c('level', crop)
                   not in range(70, 91, 5)) else
               (f'sco_level_{crop} must be 0 or 1 OR one of: 50, 55, ..., 85 ' +
                'equalling or exceeding base level')
               if (self.c('sco_level', crop) not in (0, 1) and
                   self.c('sco_level', crop) < self.c('level', crop)) else
               f'eco_{crop} must be 0, 90 or 95'
               if self.c('eco_level', crop) not in (0, 90, 95) else '')
        if len(msg) > 0:
            raise ValueError(f'Invalid setting(s) in text file: {msg}.')

    def indemnity_factory(self):
        """
        Provides CropIns instances with attributes such as
        indemnity_corn and sco_soy which are instances of concrete
        Indemnity classes.

        Note: ECO/SCO options can only be added to an enterprise base policy.
        In order to use the SCO option, the gov_pmt program must be PLC, but
        that rule cannot be enforced at this level.
        """
        def add_indemnity_attr(crop_year, crop, kind, attr_name, unit,
                               prot, level, sco_level, eco_level, pmt_factor):
            """
            Helper to select the appropriate class, get an instance,
            set that instance as a property of the CropInsurance instance,
            Then set some key properties on it for consistency.
            """
            setattr(self, attr_name,
                    (IndemnityAreaRp(crop_year, crop=crop, kind=kind)
                     if unit == AREA and prot == RP and kind == 'base' else
                     IndemnityAreaRpHpe(crop_year, crop=crop, kind=kind)
                     if unit == AREA and prot == RPHPE and kind == 'base' else
                     IndemnityAreaYo(crop_year, crop=crop, kind=kind)
                     if unit == AREA and prot == YO and kind == 'base' else
                     IndemnityEntRp(crop_year, crop=crop, kind=kind)
                     if unit == ENT and prot == RP and kind == 'base' else
                     IndemnityEntRpHpe(crop_year, crop=crop, kind=kind)
                     if unit == ENT and prot == RPHPE and kind == 'base' else
                     IndemnityEntYo(crop_year, crop=crop, kind=kind)
                     if unit == ENT and prot == YO and kind == 'base' else
                     IndemnityOptionRp(crop_year, crop=crop, kind=kind)
                     if unit == AREA and prot == RP and kind in ('sco', 'eco') else
                     IndemnityOptionRpHpe(crop_year, crop=crop, kind=kind)
                     if unit == AREA and prot == RPHPE and kind in ('sco', 'eco') else
                     IndemnityOptionYo(crop_year, crop=crop, kind=kind)))

            # Ensure commonly overridden properties are set on indemnity instances
            new_attr = getattr(self, attr_name)
            setattr(new_attr, f'unit_{crop}', unit)
            setattr(new_attr, f'prot_{crop}', prot)
            setattr(new_attr, f'level_{crop}', level)
            setattr(new_attr, f'sco_level_{crop}', sco_level)
            setattr(new_attr, f'eco_level_{crop}', eco_level)
            setattr(new_attr, f'selected_pmt_factor_{crop}', pmt_factor)
            return None

        for crop in ['corn', 'soy']:
            ins = self.c('insure', crop)
            sco_level = self.c('sco_level', crop)
            eco_level = self.c('eco_level', crop)
            base_unit = self.c('unit', crop)
            base_protection = self.c('protection', crop)
            base_level = self.c('level', crop)
            base_pmt_factor = self.c('selected_pmt_factor', crop)
            if ins:
                add_indemnity_attr(
                    self.crop_year, crop, 'base', f'indemnity_{crop}',
                    base_unit, base_protection, base_level, sco_level,
                    eco_level, base_pmt_factor)
            if ins and sco_level > 0:
                if base_unit == AREA:
                    raise ValueError('Cannot add SCO because base unit is Area')
                add_indemnity_attr(
                    self.crop_year, crop, 'sco', f'sco_{crop}',
                    AREA, base_protection, base_level, sco_level,
                    eco_level, base_pmt_factor)
            if ins and eco_level > 0:
                if base_unit == AREA:
                    raise ValueError('Cannot add ECO because base unit is Area')
                add_indemnity_attr(
                    self.crop_year, crop, 'eco', f'eco_{crop}',
                    AREA, base_protection, base_level, sco_level,
                    eco_level, base_pmt_factor)

    def c4(self, unit, prot, level, crop):
        """
        Helper for base insurance premium lookup
        """
        return getattr(
            self, f'{UNITS[unit]}_{PROTS[prot]}_{crop}_{str(level)}')

    def c5(self, prot, level, crop):
        """
        Helper for SCO premium lookup
        """
        lvl = f'{str(level)}_86' if level > 1 else 0
        return (0 if lvl == 0 else
                getattr(self, f'sco_{PROTS[prot]}_{crop}_{lvl}'))

    def c6(self, prot, level, crop, eco_level):
        """
        Helper for ECO premium lookup
        """
        lvl = f'86_{str(eco_level)}'
        return getattr(
            self, f'eco_{PROTS[prot]}_{crop}_{lvl}')

    @crop_in('corn', 'soy')
    def crop_ins_premium_per_acre_crop(self, crop):
        """
        Crop insurance per-acre premium based on choices of
        'unit', 'protection' and 'level' for the crop
        Note: payment factor is used only for area unit as far as we know
        """
        unit = self.c('unit', crop)
        prot = self.c('protection', crop)
        level = self.c('level', crop)

        return (self.c4(unit, prot, level, crop) *
                (self.c('selected_pmt_factor', crop) if unit == AREA else 1)
                if self.c('insure', crop) == YES else 0)

    @crop_in('corn', 'soy')
    def crop_ins_premium_crop(self, crop):
        """
        Crop insurance premium in dollars
        """
        return (self.crop_ins_premium_per_acre_crop(crop) *
                self.c('acres', crop))

    @crop_in('corn', 'soy')
    def sco_ins_premium_per_acre_crop(self, crop):
        """
        If the crop is not insured, return zero, otherwise, get the
        sco premium to bring coverage from the specified sco_level to 86%.
        sco_level=1 specifies that the SCO coverage should begin at the base
        level.  This avoids leaving a gap in the coverage.
        """
        prot = self.c('protection', crop)
        level = self.c('level', crop)
        sco_level = self.c('sco_level', crop)
        insure = self.c('insure', crop) == YES
        return (self.c5(
            prot,
            (level if (insure and sco_level == DFLT) else
             sco_level if (insure and sco_level > DFLT) else NONE),
            crop))

    @crop_in('corn', 'soy')
    def sco_ins_premium_crop(self, crop):
        """
        SCO premium in dollars
        """
        return (self.sco_ins_premium_per_acre_crop(crop) *
                self.c('acres', crop))

    @crop_in('corn', 'soy')
    def eco_ins_premium_per_acre_crop(self, crop):
        """
        If the crop is not insured or eco has not been added, return zero.
        Otherwise return premium for the specified eco level
        """
        return (self.c6(
            self.c('protection', crop),
            self.c('level', crop),
            crop,
            self.c('eco_level', crop))
                if self.c('insure', crop) == YES
                and self.c('eco_level', crop) > 0 else 0)

    @crop_in('corn', 'soy')
    def eco_ins_premium_crop(self, crop):
        """
        ECO premium in dollars
        """
        return (self.eco_ins_premium_per_acre_crop(crop) *
                self.c('acres', crop))

    @crop_in('corn', 'soy')
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
        Return the premium for the crop insurance and selected options.
        """
        return sum([self.total_premium_crop(crop) for crop in ['corn', 'soy']])

    @crop_in('corn', 'soy')
    def total_indemnity_crop(self, crop, pf=1, yf=1):
        """
        Return the price/yield sensitized total indemnity for the crop.
        """
        return (
            (self.c('indemnity', crop).total_indemnity_pmt_received(pf, yf)
             if hasattr(self, f'indemnity_{crop}') else 0) +
            (self.c('sco', crop).harvest_indemnity_pmt(pf, yf)
             if hasattr(self, f'sco_{crop}') else 0) +
            (self.c('eco', crop).harvest_indemnity_pmt(pf, yf)
             if hasattr(self, f'eco_{crop}') else 0))

    def total_indemnity(self, pf=1, yf=1):
        """
        Return the price/yield sensitized total indemnity.
        """
        return sum([self.total_indemnity_crop(crop, pf, yf)
                    for crop in ['corn', 'soy']])

    @crop_in('corn', 'soy')
    def net_crop_ins_indemnity_crop(self, crop, pf=1, yf=1):
        """
        Return the sensitized net crop insurance payment (subtracting premium)
        for the crop.
        """
        return (self.total_indemnity_crop(crop, pf, yf) -
                self.total_premium_crop(crop))

    def total_net_crop_ins_indemnity(self, pf=1, yf=1):
        """
        Return the sensiztized net crop insurance payment over all crops.
        """
        return (self.total_indemnity(pf, yf) - self.total_premium())
