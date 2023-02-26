"""
Module analysis

Defines class Analysis, the base class for all ifbt components
"""
from enum import IntEnum
from functools import wraps
from os import path
import re


def crop_in(*crops):
    """
    Decorator for simplifying validation of permitted crops
    """
    def decorator(f):
        @wraps(f)
        def new_f(*args, **kwds):
            if args[1] not in crops:
                crop_msg = ', '.join([f"'{c}'" for c in crops])
                raise ValueError(f'Crop must be one of: {crop_msg}')
            else:
                return f(*args, **kwds)
        return new_f
    return decorator


DATADIR = path.join(path.dirname(path.abspath(__file__)), 'data')

Crop = IntEnum('Crop', ['CORN', 'SOY', 'WHEAT', 'FULL_SOY', 'DC_SOY'], start=0)
Ins = IntEnum('Ins', ['NO', 'YES'], start=0)
Unit = IntEnum('Unit', ['AREA', 'ENT'], start=0)
Prot = IntEnum('Prot', ['RP', 'RPHPE', 'YO'], start=0)
Lvl = IntEnum('ScoLvl', ['NONE', 'DFLT'], start=0)
Prog = IntEnum('Prog', ['PLC', 'ARC_CO'], start=0)


def toLvl(v):
    """
    Helper to convert an int to a Lvl IntEnum in some cases
    """
    return (Lvl.NONE if v == 'NONE' else Lvl.DFLT if v == 'DFLT' else int(v))


class Analysis(object):
    """
    Base class for all components of the integrated farm budget tool
    """
    def __init__(self, crop_year, *args, overrides=None, **kwargs):
        """
        Get an instance for the given crop year, then get a list of
        key/value pairs from the text file and make object attributes from it.
        """
        self.crop_year = crop_year
        self._set_attrs_from_file_pairs()
        if overrides is not None:
            self._set_attrs_from_overrides(overrides)

    def _set_attrs_from_overrides(self, overrides):
        """
        Override the properties specified in the 'overrides' dict
        """
        for k, v in overrides.items():
            if isinstance(v, dict):
                attr = getattr(self, k)
                attr.update(v)
                setattr(self, k, attr)
            else:
                vnum = (v if isinstance(v, (int, float)) else self._to_number(v))
                setattr(self, k, vnum)

    def _set_attrs_from_file_pairs(self):
        """
        Set the current object's attributes to match values in the input files.
        Crop-specific items and insurance premiums have their values stored in dicts.
        This greatly reduces the number of attributes for the current object.
        """
        crop_pairs, simple = self._group_values_crop(self._load_key_value_pairs())
        prem_pairs, simple = self._group_values_ins_prem(simple)
        pairs = crop_pairs + prem_pairs + simple
        for k, v in pairs:
            setattr(self, k, v)

    def _load_key_value_pairs(self):
        """
        Load key/value pairs from all specified DATA_FILES
        return a list with all the key/value pairs
        """
        pairs = []
        for name in self.__class__.DATA_FILES.split():
            filepath = path.join(DATADIR, f'{self.crop_year}_{name}.txt')
            pairs += self._load_textfile(filepath)
        return pairs

    def _load_textfile(self, filename):
        """
        Load a textfile with the given name into a list of key/value pairs,
        ignoring blank lines and comment lines that begin with '#'
        """
        with open(filename) as f:
            contents = f.read()

        lines = [line.strip() for line in contents.strip().split('\n')
                 if len(line.strip()) > 0 and line[0] != '#']
        pairs = [line.split() for line in lines]
        return [(k, self._to_number(v)) for k, v in pairs]

    def _group_values_crop(self, pairs):
        """
        Given a list of key/value pairs, find any that end with a crop name,
        and merge them into a new key/value pair with
          key: the original key with crop name removed,
          value: a dict with key crop and original value.
        Return a list of key/value pairs and a list of simple pairs.
        """
        crops = 'corn soy wheat fullsoy dcsoy'.split()
        levels = 'level, sco_level, eco_level'.split()
        pat = f'^(.*)_({"|".join(crops)})$'
        with_crop = []
        simple = []
        for k, v in pairs:
            m = re.match(pat, k)
            if m:
                # Change crop insurance choice values to appropriate enum values
                tag = m.groups()[0]
                val = (Ins(v) if tag == 'insure' else Unit(v) if tag == 'unit' else
                       Prot(v) if tag == 'protection' else
                       toLvl(v) if tag in levels else self._to_number(v))
                with_crop.append((m.groups(), val))
            else:
                simple.append((k, v))
        groups = {}
        for (name, crop), v in with_crop:
            groups.setdefault(name, {})[Crop(crops.index(crop))] = v
        with_crop = list(groups.items())
        return with_crop, simple

    def _group_values_ins_prem(self, pairs):
        """
        Given a list of key/value pairs, find any that match an insurance premium,
        and merge them into new key/value pairs with
          key: 'premium', 'sco_premium' or 'eco_premium'
          value: a tuple with the values for the insurance parameters.
        """
        def group_matches(pairs, pat):
            simple = []
            prem = {}
            for k, v in pairs:
                m = re.match(pat, k)
                if m:
                    if len(m.groups()) == 4:
                        u, p, c, lvl = m.groups()
                        choice = (Unit(units.index(u)), Prot(prots.index(p)),
                                  Crop(crops.index(c)),
                                  toLvl(lvl))
                    else:
                        p, c, lvl = m.groups()
                        choice = (Prot(prots.index(p)), Crop(crops.index(c)),
                                  toLvl(lvl))
                    prem[choice] = v
                else:
                    simple.append((k, v))
            return prem, simple

        units = 'area ent'.split()
        prots = 'rp rphpe yo'.split()
        crops = 'corn soy'.split()

        pat_base = (f'^({"|".join(units)})_({"|".join(prots)})_({"|".join(crops)})' +
                    f'_({"|".join(str(i) for i in range(50, 91, 5))})$')
        pat_sco = (f'^sco_({"|".join(prots)})_({"|".join(crops)})' +
                   f'_({"|".join(str(i) for i in range(50, 86, 5))})_86$')
        pat_eco = (f'^eco_({"|".join(prots)})_({"|".join(crops)})' +
                   '_86_(90|95)$')

        dicts = []
        prem, simple = group_matches(pairs, pat_base)
        dicts.append(('premium', prem))
        prem, simple = group_matches(simple, pat_sco)
        dicts.append(('sco_premium', prem))
        prem, simple = group_matches(simple, pat_eco)
        dicts.append(('eco_premium', prem))

        return dicts, simple

    def _to_number(self, s):
        """
        Convert a number string to a float or int
        """
        return s if isinstance(s, (float, int)) else float(s) if '.' in s else int(s)

    def projected_bu_soy(self, yf=1):
        """
        Compute the projected, sensitized raw total soy bushels
        considering wheat/dc soy acres
        """
        return ((self.acres[Crop.DC_SOY] *
                 self.proj_yield_farm[Crop.DC_SOY] +
                 (self.acres[Crop.SOY] -
                  self.acres[Crop.DC_SOY]) *
                 self.proj_yield_farm[Crop.FULL_SOY]) * yf)

    @crop_in(Crop.CORN, Crop.SOY)
    def projected_bu_crop(self, crop, yf=1):
        """
        Compute the projected, sensitized total bushels for the given crop
        """
        return (self.projected_bu_soy(yf) if crop == Crop.SOY else
                self.proj_yield_farm[crop] * self.acres[crop] * yf)

    def projected_yield_soy(self, yf=1):
        """
        Compute the projected, sensitized overall soy yield
        """
        return self.projected_bu_soy(yf) / self.acres[Crop.SOY]

    @crop_in(Crop.CORN, Crop.SOY, Crop.FULL_SOY, Crop.DC_SOY, Crop.WHEAT)
    def projected_yield_crop(self, crop, yf=1):
        """
        Compute the projected, sensitized yield for any crop
        """
        return (self.projected_yield_soy(yf) if crop == Crop.SOY else
                self.proj_yield_farm[crop] * yf)
