"""
Module analysis

Defines class Analysis, the base class for all ifbt components
"""
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

CORN, SOY, WHEAT, FULL_SOY, DC_SOY = range(5)


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
        for k, v in overrides.items():
            if isinstance(v, dict):
                attr = getattr(self, k)
                attr.update(v)
                setattr(self, k, attr)
            else:
                vnum = (v if isinstance(v, (int, float)) else self._to_number(v))
                setattr(self, k, vnum)

    def _set_attrs_from_file_pairs(self):
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

        lines = contents.strip().split('\n')
        lines = filter(lambda line: len(line) > 0 and line[0] != '#',
                       [line.strip() for line in lines])
        pairs = [line.split() for line in lines]
        return [(k, self._to_number(v)) for k, v in pairs]

    def _group_values_crop(self, pairs):
        """
        Given a list of key/value pairs, find any that end with a crop name,
        and merge them into a new key/value pair with
          key: the original key with crop name removed,
          value: a dict with key crop and original value.
        Return a list of key/value pairs which merges the items of the outer dict
        with the without_crop pairs.
        """
        crops = 'corn soy wheat fullsoy dcsoy'.split()
        pat = f'^(.*)_({"|".join(crops)})$'
        with_crop = []
        simple = []
        for k, v in pairs:
            m = re.match(pat, k)
            if m:
                with_crop.append((m.groups(), v))
            else:
                simple.append((k, v))
        groups = {}
        for (name, crop), v in with_crop:
            groups.setdefault(name, {})[crops.index(crop)] = v
        with_crop = list(groups.items())
        return with_crop, simple

    def _group_values_ins_prem(self, pairs):
        """
        Given a list of key/value pairs, find any that match an insurance premium,
        and merge them into a new key/value pair with
          key: 'premium',
          value: a tuple with the values for the various crops ordered by crop name.
        """
        units = 'area ent'.split()
        prots = 'rp rphpe yo'.split()
        crops = 'corn soy'.split()
        pat = (f'^({"|".join(units)})_({"|".join(prots)})_({"|".join(crops)})' +
               f'_({"|".join(str(i) for i in range(50, 91, 5))})$')
        pat_sco = (f'^sco_({"|".join(prots)})_({"|".join(crops)})' +
                   f'_({"|".join(str(i) for i in range(50, 86, 5))})_86$')
        pat_eco = (f'^eco_({"|".join(prots)})_({"|".join(crops)})' +
                   '_86_(90|95)$')

        # premium
        simple1 = []
        premium = {}
        for k, v in pairs:
            m = re.match(pat, k)
            if m:
                u, p, c, lvl = m.groups()
                choice = (units.index(u), prots.index(p), crops.index(c), int(lvl))
                premium[choice] = v
            else:
                simple1.append((k, v))

        # sco
        simple2 = []
        sco_premium = {}
        for k, v in simple1:
            m = re.match(pat_sco, k)
            if m:
                p, c, lvl = m.groups()
                choice = (prots.index(p), crops.index(c), int(lvl))
                sco_premium[choice] = v
            else:
                simple2.append((k, v))

        # eco
        simple3 = []
        eco_premium = {}
        for k, v in simple2:
            m = re.match(pat_eco, k)
            if m:
                p, c, lvl = m.groups()
                choice = (prots.index(p), crops.index(c), int(lvl))
                eco_premium[choice] = v
            else:
                simple3.append((k, v))

        return ([('premium', premium), ('sco_premium', sco_premium),
                 ('eco_premium', eco_premium)], simple3)

    def _to_number(self, s):
        """
        Convert a number string to a float or int
        """
        return float(s) if '.' in s else int(s)

    def projected_bu_soy(self, yf=1):
        """
        Compute the projected, sensitized raw total soy bushels
        considering wheat/dc soy acres
        """
        return ((self.acres[DC_SOY] *
                 self.proj_yield_farm[DC_SOY] +
                 (self.acres[SOY] -
                  self.acres[DC_SOY]) *
                 self.proj_yield_farm[FULL_SOY]) * yf)

    @crop_in(CORN, SOY)
    def projected_bu_crop(self, crop, yf=1):
        """
        Compute the projected, sensitized total bushels for the given crop
        """
        return (self.projected_bu_soy(yf) if crop == SOY else
                self.proj_yield_farm[crop] * self.acres[crop] * yf)

    def projected_yield_soy(self, yf=1):
        """
        Compute the projected, sensitized overall soy yield
        """
        return self.projected_bu_soy(yf) / self.acres[SOY]

    @crop_in(CORN, SOY, FULL_SOY, DC_SOY, WHEAT)
    def projected_yield_crop(self, crop, yf=1):
        """
        Compute the projected, sensitized yield for any crop
        """
        return (self.projected_yield_soy(yf) if crop == SOY else
                self.proj_yield_farm[crop] * yf)
