"""
Module attribute_loader

Defines classes DatabaseAttributeLoader and TextfileAttributeLoader.
Subclasses are responsible for loading key value pairs into object attributes.
"""
from os import path
import re

from .util import Crop, Ins, Unit, Prot, Lvl, Prog


DATADIR = path.join(path.dirname(path.abspath(__file__)), 'data')


class DatabaseAttributeLoader(object):
    """
    class DatabaseAttributeLoader
    Handles loading attribute data from a database.
    """
    def __init__(self):
        # TODO: Maybe gets list of queries instead of list of files?
        pass

    def set_attrs(self, inst):
        """
        Set the given object's attributes based on key/value pairs.
        Crop-specific and insurance premium attributes have dict values.
        This greatly reduces the number of attributes for the current object.
        """
        prem_pairs = self.group_values_ins_prem(
            self.load_crop_ins_premium_tuples(inst.crop_year))
        crop_pairs, simple_pairs = self.group_values_crop(
            self.load_model_and_user_tuples(inst.crop_year))
        pairs = crop_pairs + prem_pairs + simple_pairs
        for k, v in pairs:
            setattr(inst, k, v)

    def load_crop_ins_premium_tuples(self, attr):
        """
        Query the database to get detail records for crop insurance.
        Generate a list of tuples from crop insurance premium details.
        """
        # TODO:
        details = []
        self.group_values_ins_premium(details)

    def load_model_and_user_tuples(self, attr):
        """
        Generate a list of tuples from model and user data.
        """
        # TODO:
        details = []
        self.group_values_crop(details)

    def group_values_crop(self, details):
        """
        Given an iterable of detail records, with name, (possibly null) crop_name,
        and value, create a list of name/dict pairs for detail items with non-null
        crop, (with_crop), and a list of name/value pairs with the rest (simple).
        """
        with_crop = self.group_crop([det for det in details if det.crop is not None])
        simple = [(det.name, det.value) for det in details if det.crop is None]
        return with_crop, simple

    def group_crop(self, with_crop):
        """
        Given an iterable of crop-specific details, return a shorter list of key/value
        pairs where each value is a dict with key Crop and crop-specific values.
        """
        groups = {}
        for det in with_crop:
            val = get_value_crop(det.name, det.value)
            groups.setdefault(det.name, {})[Crop(det.crop)] = val
        return list(groups.items())

    def group_values_ins_prem(self, details):
        """
        Given crop insurance premium details, get a list with three dicts, one for each
        kind: 0=base, 1=sco, 2=eco
        """
        dicts = []
        for kind in range(3):
            dets = [det for det in details if det.kind == kind]
            self.group_matches_ins_prem(dets)
        return dicts

    def group_matches_ins_prem(self, details):
        """
        Given an iterable of crop insurance detail records,
        return a dict (prem) with premiums for the crop ins type constructed from pairs
        whose keys match the given pattern.  Also return a list (simple)
        with the unmatched pairs.
        """
        prem = {}
        for det in details:
            prem[self.make_prem_choice(det)] = det.value
        return prem

    def make_prem_choice(self, det):
        """
        Given a crop ins premium detail record, return a tuple representing a crop
        insurance choice
        """
        if det.unit is not None:
            choice = (Unit(det.unit), Prot(det.prot), Crop(det.crop), to_lvl(det.lvl))
        else:
            choice = (Prot(det.prot), Crop(det.crop), to_lvl(det.lvl))
        return choice


class TextfileAttributeLoader(object):
    """
    class TextfileAttributeLoader
    Handles loading attribute data from textfiles.
    """
    CROPS = 'corn soy wheat fullsoy dcsoy'.split()
    UNITS = 'area ent'.split()
    PROTS = 'rp rphpe yo'.split()
    INS_CROPS = 'corn soy'.split()
    PREM_KINDS = 'premium sco_premium eco_premium'.split()
    CROP_PAT = f'^(.*)_({"|".join(CROPS)})$'
    PREM_PATS = [
            (f'^({"|".join(UNITS)})_({"|".join(PROTS)})_({"|".join(INS_CROPS)})' +
             f'_({"|".join(str(i) for i in range(50, 91, 5))})$'),
            (f'^sco_({"|".join(PROTS)})_({"|".join(INS_CROPS)})' +
             f'_({"|".join(str(i) for i in range(50, 86, 5))})_86$'),
            (f'^eco_({"|".join(PROTS)})_({"|".join(INS_CROPS)})_86_(90|95)$'), ]

    def __init__(self, filenames):
        self.filenames = filenames.split()

    def set_attrs(self, inst):
        """
        Set the given object's attributes based on key/value pairs.
        Crop-specific and insurance premium attributes have dict values.
        This greatly reduces the number of attributes for the current object.
        """
        prem_filenames = (fname for fname in self.filenames
                          if fname.find('crop_ins_premiums') >= 0)
        std_filenames = (fname for fname in self.filenames
                         if fname.find('crop_ins_premiums') < 0)
        prem_pairs = self.group_values_ins_prem(
            load_key_value_pairs(inst.crop_year, prem_filenames))
        crop_pairs, simple_pairs = self.group_values_crop(
            load_key_value_pairs(inst.crop_year, std_filenames))
        pairs = prem_pairs + crop_pairs + simple_pairs
        for k, v in pairs:
            setattr(inst, k, v)

    def group_values_crop(self, pairs):
        """
        Given an iterable of key/value pairs, with string keys and Number values,
        return two lists of key/value pairs, one with dict values with dict key crop,
        the other with the original number values.
        """
        with_crop = []
        simple = []
        for k, v in pairs:
            m = re.match(self.CROP_PAT, k)
            if m:
                with_crop.append((m.groups(), get_value_crop(m.groups()[0], v)))
            else:
                simple.append((k, v))
        return self.group_crop(with_crop), simple

    def group_crop(self, with_crop):
        """
        Given a list of crop-specific, ungrouped key/value pairs, use a temporary dict
        (groups) to generate a new, shorter list of key/value pairs where each key
        is the original key with crop name removed, and the corresponding value
        is a dict with key Crop and crop-specific values.
        """
        groups = {}
        for (name, crop), v in with_crop:
            groups.setdefault(name, {})[Crop(self.CROPS.index(crop))] = v
        return list(groups.items())

    def group_values_ins_prem(self, pairs):
        """
        Return a list of three (name, dict) pairs, one for each kind of premium,
        from simple pairs with crop ins premiums.
        """
        dicts = []
        unmatched = list(pairs)
        for pat, name in zip(self.PREM_PATS, self.PREM_KINDS):
            prem, unmatched = self.extract_dict_ins_prem(unmatched, pat)
            dicts.append((name, prem))
        if unmatched:
            raise ValueError("Expected file to contain only crop ins premiums.")
        return dicts

    def extract_dict_ins_prem(self, pairs, pat):
        """
        Given a list of key/value pairs and a pattern to match on keys,
        return a dict (prem) with premiums for the crop ins type.
        Also return a list (simple) with the unmatched pairs.
        """
        simple = []
        prem = {}
        for k, v in pairs:
            m = re.match(pat, k)
            if m:
                prem[self.make_choice_prem(m)] = v
            else:
                simple.append((k, v))
        return prem, simple

    def make_choice_prem(self, m):
        """
        Given a match object, return a tuple of IntEnum values
        representing a crop insurance choice.
        """
        if len(m.groups()) == 4:
            u, p, c, lvl = m.groups()
            choice = (Unit(self.UNITS.index(u)), Prot(self.PROTS.index(p)),
                      Crop(self.INS_CROPS.index(c)), to_lvl(lvl))
        else:
            p, c, lvl = m.groups()
            choice = (Prot(self.PROTS.index(p)), Crop(self.INS_CROPS.index(c)),
                      to_lvl(lvl))
        return choice


# ----------------------------
# Helpers used by both classes
# ----------------------------
def to_lvl(v):
    """
    Helper to convert a 'level' to a Lvl IntEnum
    """
    return (Lvl.NONE if v == 'NONE' else Lvl.DFLT if v == 'DFLT' else int(v))


def get_value_crop(tag, v):
    """
    Change crop insurance and gov pmt choice values to appropriate IntEnum values
    for choices like 'insure_corn'.
    Expects a tag name and an int or float value (v)
    """
    levels = 'level, sco_level, eco_level'.split()
    val = (Ins(v) if tag == 'insure' else Unit(v) if tag == 'unit' else
           Prot(v) if tag == 'protection' else
           to_lvl(v) if tag in levels else
           Prog(v) if tag == 'program' else v)
    return val


# ---------------------------------------------
# Helpers used by TextfileAttributeLoader class
# ---------------------------------------------
def load_key_value_pairs(crop_year, filenames):
    """
    Load key/value pairs from all specified DATA_FILES
    return a list with all the key/value pairs
    """
    pairs = []
    for name in filenames:
        filepath = path.join(DATADIR, f'{crop_year}_{name}.txt')
        pairs += load_textfile(filepath)
    return pairs


def load_textfile(filename):
    """
    Load a textfile with the given name into a list of key/value pairs,
    ignoring blank lines and comment lines that begin with '#'
    """
    with open(filename) as f:
        contents = f.read()

    lines = (line.strip() for line in contents.strip().split('\n')
             if len(line.strip()) > 0 and line[0] != '#')
    pairs = (line.split() for line in lines)
    return [(k, to_number(v)) for k, v in pairs]


def to_number(s):
    """
    Convert a number string to a float or int
    """
    return float(s) if '.' in s else int(s)
