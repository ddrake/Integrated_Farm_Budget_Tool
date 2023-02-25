"""
Module crop_ins

Contains a single class, CropIns, which loads its data from text files
for a given crop year when an instance is created.  Its main function
is to return total estimated net insurance cost for the farm for the given
crop year corresponding to an arbitrary sensitivity factor for yield.
"""
from .analysis import Analysis, crop_in, CORN, SOY
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
      from ifbt import CropIns
      c = CropIns(2023)
      c.total_cost(pf=.7)        # yield factor defaults to 1
      c.total_cost(pf=.7, yf=.8) # specifies both price and yield factors
    """
    DATA_FILES = 'farm_data crop_ins_data crop_ins_premiums'

    def __init__(self, *args, **kwargs):
        super(CropIns, self).__init__(*args, **kwargs)
        for crop in [CORN, SOY]:
            self.validate_settings(crop)
        self.indemnity_factory()

    def validate_settings(self, crop):
        """
        Perform basic validation (sanity check) on the input data
        """
        msg = (f'insure_{crop} must be either 0 or 1'
               if self.insure[crop] not in (0, 1) else
               f'unit_{crop} must be either 0 or 1'
               if self.unit[crop] not in (0, 1) else
               f'protection_{crop} must be 0, 1 or 2'
               if self.protection[crop] not in (0, 1, 2) else
               f'level_{crop} must be one of: 50, 55, ..., or 85'
               if (self.unit[crop] == 1 and self.level[crop]
                   not in range(50, 86, 5)) else
               f'level_{crop} must be one of: 70, 75, ..., or 90'
               if (self.unit[crop] == 0 and self.level[crop]
                   not in range(70, 91, 5)) else
               (f'sco_level_{crop} must be 0 or 1 OR one of: 50, 55, ..., 85 ' +
                'equalling or exceeding base level')
               if (self.sco_level[crop] not in (0, 1) and
                   self.sco_level[crop] < self.level[crop]) else
               f'eco_{crop} must be 0, 90 or 95'
               if self.eco_level[crop] not in (0, 90, 95) else '')
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
        def add_indemnity_attr(crop_year, crop, attr_name, unit,
                               prot, level, sco_level, eco_level, pmt_factor):
            """
            Helper to select the appropriate class, get an instance,
            set that instance as a property of the CropInsurance instance,
            Then set some key properties on it for consistency.
            """
            instance = (
                IndemnityAreaRp(crop_year, crop)
                if unit == AREA and prot == RP and attr_name == 'indemnity' else
                IndemnityAreaRpHpe(crop_year, crop)
                if unit == AREA and prot == RPHPE and attr_name == 'indemnity' else
                IndemnityAreaYo(crop_year, crop)
                if unit == AREA and prot == YO and attr_name == 'indemnity' else
                IndemnityEntRp(crop_year, crop)
                if unit == ENT and prot == RP and attr_name == 'indemnity' else
                IndemnityEntRpHpe(crop_year, crop)
                if unit == ENT and prot == RPHPE and attr_name == 'indemnity' else
                IndemnityEntYo(crop_year, crop)
                if unit == ENT and prot == YO and attr_name == 'indemnity' else
                IndemnityOptionRp(crop_year, crop, attr_name)
                if unit == AREA and prot == RP else
                IndemnityOptionRpHpe(crop_year, crop, attr_name)
                if unit == AREA and prot == RPHPE else
                IndemnityOptionYo(crop_year, crop, attr_name))

            if hasattr(self, attr_name):
                attr = getattr(self, attr_name)
                attr.update({crop: instance})
            else:
                setattr(self, attr_name, {crop: instance})

            # Ensure commonly overridden properties are set consistently
            # on indemnity instances

            new_attr = getattr(self, attr_name)
            for name, val in [
                    ('unit', unit), ('protection', prot), ('level', level),
                    ('sco_level', sco_level), ('eco_level', eco_level),
                    ('selected_pmt_factor', pmt_factor)]:
                attr = getattr(new_attr[crop], name)
                attr.update({crop: val})
            return None

        for crop in [CORN, SOY]:
            ins = self.insure[crop]
            sco_level = self.sco_level[crop]
            eco_level = self.eco_level[crop]
            base_unit = self.unit[crop]
            base_protection = self.protection[crop]
            base_level = self.level[crop]
            base_pmt_factor = self.selected_pmt_factor[crop]
            if ins:
                add_indemnity_attr(
                    self.crop_year, crop, 'indemnity',
                    base_unit, base_protection, base_level, sco_level,
                    eco_level, base_pmt_factor)
            if ins and sco_level > 0:
                if base_unit == AREA:
                    raise ValueError('Cannot add SCO because base unit is Area')
                add_indemnity_attr(
                    self.crop_year, crop, 'sco',
                    AREA, base_protection, base_level, sco_level,
                    eco_level, base_pmt_factor)
            if ins and eco_level > 0:
                if base_unit == AREA:
                    raise ValueError('Cannot add ECO because base unit is Area')
                add_indemnity_attr(
                    self.crop_year, crop, 'eco',
                    AREA, base_protection, base_level, sco_level,
                    eco_level, base_pmt_factor)

    @crop_in(CORN, SOY)
    def crop_ins_premium_per_acre_crop(self, crop):
        """
        Crop insurance per-acre premium based on choices of
        'unit', 'protection' and 'level' for the crop
        Note: payment factor is used only for area unit as far as we know
        """
        unit = self.unit[crop]
        prot = self.protection[crop]
        level = self.level[crop]
        insure = self.insure[crop] == YES

        return (0 if not insure else
                self.premium[(unit, prot, crop, level)] *
                (self.selected_pmt_factor[crop] if unit == AREA else 1))

    @crop_in(CORN, SOY)
    def crop_ins_premium_crop(self, crop):
        """
        Crop insurance premium in dollars
        """
        return (self.crop_ins_premium_per_acre_crop(crop) *
                self.acres[crop])

    @crop_in(CORN, SOY)
    def sco_ins_premium_per_acre_crop(self, crop):
        """
        If the crop is not insured, return zero, otherwise, get the
        sco premium to bring coverage from the specified sco_level to 86%.
        sco_level=1 specifies that the SCO coverage should begin at the base
        level.  This avoids leaving a gap in the coverage.
        """
        prot = self.protection[crop]
        level = self.level[crop]
        sco_level = self.sco_level[crop]
        insure = self.insure[crop] == YES
        return (
            0 if not insure or sco_level == NONE else
            self.sco_premium[
                (prot, crop, level if sco_level == DFLT else sco_level)])

    @crop_in(CORN, SOY)
    def sco_ins_premium_crop(self, crop):
        """
        SCO premium in dollars
        """
        return (self.sco_ins_premium_per_acre_crop(crop) *
                self.acres[crop])

    @crop_in(CORN, SOY)
    def eco_ins_premium_per_acre_crop(self, crop):
        """
        If the crop is not insured or eco has not been added, return zero.
        Otherwise return premium for the specified eco level
        """
        prot = self.protection[crop]
        eco_level = self.eco_level[crop]
        insure = self.insure[crop] == YES
        return (
            0 if not insure or eco_level == NONE else
            self.eco_premium[(prot, crop, eco_level)])

    @crop_in(CORN, SOY)
    def eco_ins_premium_crop(self, crop):
        """
        ECO premium in dollars
        """
        return (self.eco_ins_premium_per_acre_crop(crop) *
                self.acres[crop])

    @crop_in(CORN, SOY)
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
        return sum([self.total_premium_crop(crop) for crop in [CORN, SOY]])

    @crop_in(CORN, SOY)
    def total_indemnity_crop(self, crop, pf=1, yf=1):
        """
        Return the price/yield sensitized total indemnity for the crop.
        """
        return (
            (self.indemnity[crop].total_indemnity_pmt_received(pf, yf)
             if hasattr(self, 'indemnity') and crop in self.indemnity else 0) +
            (self.sco[crop].harvest_indemnity_pmt(pf, yf)
             if hasattr(self, 'sco') and crop in self.sco else 0) +
            (self.eco[crop].harvest_indemnity_pmt(pf, yf)
             if hasattr(self, 'eco') and crop in self.eco else 0))

    def total_indemnity(self, pf=1, yf=1):
        """
        Return the price/yield sensitized total indemnity.
        """
        return sum([self.total_indemnity_crop(crop, pf, yf)
                    for crop in [CORN, SOY]])

    @crop_in(CORN, SOY)
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
