"""
Module crop_ins

Contains a single class, CropIns, which loads its data from text files
for a given crop year when an instance is created.  Its main function
is to return total estimated net insurance cost for the farm for the given
crop year corresponding to an arbitrary sensitivity factor for yield.
"""
from .analysis import Analysis
from .indemnity import Indemnity
from .util import crop_in, Ins, Unit, Prot, Lvl, SEASON_CROPS


class CropIns(Analysis):
    """
    Computes total net (after payout) crop insurance cost for the farm crop year
    corresponding to arbitrary sensitivity factors for price and yield.

    The optional argument 'overrides' is a dict intended to override settings
    from the data file(s).  It is primarily used to ensure that changes to key
    settings in the data files(s) do not cause tests to fail.

    Sample usage in a python or ipython console:
      from ifbt import Premium, CropIns
      prem = Premium()
      c = CropIns(2023, prem=prem)
      c.total_cost(pf=.7)        # yield factor defaults to 1
      c.total_cost(pf=.7, yf=.8) # specifies both price and yield factors
    """
    DATA_FILES = 'farm_data crop_ins_data'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for crop in SEASON_CROPS:
            self._validate_settings(crop)
        if 'prem' not in kwargs:
            raise ValueError("CropIns constructor needs a Premium instance")
        self.prem = kwargs['prem']
        self.indem = Indemnity(self.crop_year)
        # cached arrays
        self.premiums = None
        self.indemnities = None

    def _validate_settings(self, crop):
        """
        Perform basic validation (sanity check) on the input data for insured crops.
        """
        insure = self.insure[crop]
        msg = (f'insure_{crop} must be either 0 or 1'
               if insure not in (Ins.NO, Ins.YES) else
               f'unit_{crop} must be either 0 or 1'
               if insure and self.unit[crop] not in (Unit.AREA, Unit.ENT) else
               f'protection_{crop} must be 0, 1 or 2'
               if insure and self.protection[crop] not in
               (Prot.RP, Prot.RPHPE, Prot.YO) else
               f'level_{crop} must be one of: 50, 55, ..., or 85'
               if (insure and self.unit[crop] == Unit.ENT and self.level[crop]
                   not in range(50, 86, 5)) else
               f'level_{crop} must be one of: 70, 75, ..., or 90'
               if (insure and self.unit[crop] == Unit.AREA and self.level[crop]
                   not in range(70, 91, 5)) else
               (f'sco_level_{crop} must be 0 or 1 OR one of: 50, 55, ..., 85 ' +
                'equalling or exceeding base level')
               if (insure and self.sco_level[crop] not in (Lvl.NONE, Lvl.DFLT) and
                   self.sco_level[crop] < self.level[crop]) else
               f'eco_{crop} must be 0, 90 or 95'
               if (insure and self.eco_level[crop] not in (Lvl.NONE, 90, 95)) else
               'Cannot add SCO if base unit is 0 (area)'
               if (insure and self.sco_level[crop] > Lvl.NONE and
                   self.unit[crop] == Unit.AREA) else
               'Cannot add ECO if base unit is 0 (area)'
               if (insure and self.eco_level[crop] > Lvl.NONE and
                   self.unit[crop] == Unit.AREA) else '')

        if len(msg) > 0:
            raise ValueError(f'Invalid setting(s) in text file: {msg}.')

    def get_all_premiums(self):
        """
        Construct a list of dicts, one for each Crop.
        Get back a dict of dicts with the outer dict keyed on Crop and the inner dicts
        with key in {'base', 'sco', 'eco'} and value premium per acre.
        This dict of results is currently cached, which we may want to rethink if we
        start changing settings between calls.
        """
        if self.premiums is not None:
            return self.premiums
        dicts = []
        for crop, insure in self.insure.items():
            if insure:
                d = {'crop': crop, 'unit': self.unit[crop],
                     'aphyield': self.aphyield[crop], 'appryield': self.appryield[crop],
                     'tayield': self.tayield[crop], 'acres': self.acres[crop],
                     'hailfire': self.hailfire[crop], 'prevplant': self.prevplant[crop],
                     'risk': self.risk[crop], 'tause': self.tause[crop],
                     'yieldexcl': self.yieldexcl[crop], 'county': self.county,
                     'practice': self.practice[crop], 'croptype': self.croptype[crop],
                     'level': self.level[crop], 'eco_level': self.eco_level[crop],
                     'sco_level': self.sco_level[crop],
                     'protection': self.protection[crop],
                     'prot_factor': self.prot_factor[crop]}
                dicts.append(d)
        self.premiums = self.prem.get_all_premiums(dicts)
        return self.premiums

    # -------
    # PREMIUM
    # -------
    @crop_in(*SEASON_CROPS)
    def premium_base_per_acre_crop(self, crop):
        """
        Crop insurance per-acre premium based on choices of
        'unit', 'protection' and 'level' for the crop
        Note: payment factor is used only for area unit as far as we know.
        """
        premiums = self.get_all_premiums()
        return (0 if crop not in premiums or 'base' not in premiums[crop] else
                premiums[crop]['base'])

    @crop_in(*SEASON_CROPS)
    def premium_base_crop(self, crop):
        """
        Crop insurance premium in dollars
        """
        return (self.premium_base_per_acre_crop(crop) *
                self.acres_crop(crop))

    @crop_in(*SEASON_CROPS)
    def premium_sco_per_acre_crop(self, crop):
        """
        If the crop is not insured, return zero, otherwise, get the
        sco premium to bring coverage from the specified sco_level to 86%.
        sco_level=DFLT specifies that the SCO coverage should begin at the base
        level.  This prevents a gap in the coverage.
        """
        premiums = self.get_all_premiums()
        return (0 if crop not in premiums or 'sco' not in premiums[crop] else
                premiums[crop]['sco'])

    @crop_in(*SEASON_CROPS)
    def premium_sco_crop(self, crop):
        """
        SCO premium in dollars
        """
        return (self.premium_sco_per_acre_crop(crop) *
                self.acres_crop(crop))

    @crop_in(*SEASON_CROPS)
    def premium_eco_per_acre_crop(self, crop):
        """
        If the crop is not insured or eco has not been added, return zero.
        Otherwise return premium for the specified eco level
        """
        premiums = self.get_all_premiums()
        return (0 if crop not in premiums or 'eco' not in premiums[crop]
                else premiums[crop]['eco'])

    @crop_in(*SEASON_CROPS)
    def premium_eco_crop(self, crop):
        """
        ECO premium in dollars
        """
        return (self.premium_eco_per_acre_crop(crop) *
                self.acres_crop(crop))

    def total_premium_per_acre_crop(self, crop):
        return (self.premium_base_per_acre_crop(crop) +
                self.premium_sco_per_acre_crop(crop) +
                self.premium_eco_per_acre_crop(crop))

    @crop_in(*SEASON_CROPS)
    def total_premium_crop(self, crop):
        """
        Return the premium for the crop insurance and option selection
        for the given crop
        """
        return (self.premium_base_crop(crop) +
                self.premium_sco_crop(crop) +
                self.premium_eco_crop(crop))

    def total_premium(self):
        """
        Return the premium for the crop insurance and selected options.
        """
        return sum([self.total_premium_crop(crop) for crop in SEASON_CROPS])

    # ---------
    # INDEMNITY
    # ---------
    def get_all_indemnities(self, pf=1, yf=1):
        """
        Construct a list of dicts, one for each Crop.
        Get back a dict of dicts with the outer dict keyed on Crop and the inner dicts
        with key in {'base', 'sco', 'eco'} and value premium per acre.
        This dict of results is currently cached, which we may want to rethink if we
        start changing settings between calls.
        """
        dicts = []
        for crop, insure in self.insure.items():
            if insure:
                d = {'crop': crop, 'unit': self.unit[crop],
                     'protection': self.protection[crop], 'level': self.level[crop],
                     'eco_level': self.eco_level[crop],
                     'sco_level': self.sco_level[crop],
                     'prot_factor': self.prot_factor[crop], }
                dicts.append(d)
        self.indemnities = self.indem.get_all_indemnities(dicts, pf, yf)
        return self.indemnities

    @crop_in(*SEASON_CROPS)
    def indemnity_base_per_acre_crop(self, crop, pf=1, yf=1):
        """
        Crop insurance per-acre indemnity based on choices of
        'unit', 'protection' and 'level' for the crop
        Note: payment factor is used only for area unit as far as we know.
        """
        indemnities = self.get_all_indemnities(pf, yf)
        return (0 if crop not in indemnities or 'base' not in indemnities[crop] else
                indemnities[crop]['base'])

    @crop_in(*SEASON_CROPS)
    def indemnity_base_crop(self, crop, pf=1, yf=1):
        """
        Crop insurance indemnity in dollars
        """
        return (self.indemnity_base_per_acre_crop(crop, pf, yf) *
                self.acres_crop(crop))

    @crop_in(*SEASON_CROPS)
    def indemnity_sco_per_acre_crop(self, crop, pf=1, yf=1):
        """
        If the crop is not insured, return zero, otherwise, get the
        sco indemnity to bring coverage from the specified sco_level to 86%.
        sco_level=DFLT specifies that the SCO coverage should begin at the base
        level.  This prevents a gap in the coverage.
        """
        indemnities = self.get_all_indemnities(pf, yf)
        return (0 if crop not in indemnities or 'sco' not in indemnities[crop] else
                indemnities[crop]['sco'])

    @crop_in(*SEASON_CROPS)
    def indemnity_sco_crop(self, crop, pf=1, yf=1):
        """
        SCO indemnity in dollars
        """
        return (self.indemnity_sco_per_acre_crop(crop, pf, yf) *
                self.acres_crop(crop))

    @crop_in(*SEASON_CROPS)
    def indemnity_eco_per_acre_crop(self, crop, pf=1, yf=1):
        """
        If the crop is not insured or eco has not been added, return zero.
        Otherwise return indemnity for the specified eco level
        """
        indemnities = self.get_all_indemnities(pf, yf)
        return (0 if crop not in indemnities or 'eco' not in indemnities[crop]
                else indemnities[crop]['eco'])

    @crop_in(*SEASON_CROPS)
    def indemnity_eco_crop(self, crop, pf=1, yf=1):
        """
        ECO indemnity in dollars
        """
        return (self.indemnity_eco_per_acre_crop(crop, pf, yf) *
                self.acres_crop(crop))

    @crop_in(*SEASON_CROPS)
    def total_indemnity_crop(self, crop, pf=1, yf=1):
        """
        Return the indemnity for the crop insurance and option selection
        for the given crop
        """
        return (self.indemnity_base_crop(crop, pf, yf) +
                self.indemnity_sco_crop(crop, pf, yf) +
                self.indemnity_eco_crop(crop, pf, yf))

    def total_indemnity(self, pf=1, yf=1):
        """
        Return the price/yield sensitized total indemnity.
        """
        return sum([self.total_indemnity_crop(crop, pf, yf)
                    for crop in SEASON_CROPS])

    @crop_in(*SEASON_CROPS)
    def net_indemnity_crop(self, crop, pf=1, yf=1):
        """
        Return the sensitized net crop insurance payment (subtracting premium)
        for the crop.
        """
        return (self.total_indemnity_crop(crop, pf, yf) -
                self.total_premium_crop(crop))

    def total_net_indemnity(self, pf=1, yf=1):
        """
        Return the sensiztized net crop insurance payment over all crops.
        """
        return (self.total_indemnity(pf, yf) - self.total_premium())
