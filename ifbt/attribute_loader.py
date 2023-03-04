"""
Module attribute_loader

Defines a base class AttributeLoader and concrete subclass TextfileAttributeLoader.
Subclasses are responsible for loading key value pairs into object attributes.
"""
from os import path
import re

from .util import Crop, Ins, Unit, Prot, Lvl, Prog


DATADIR = path.join(path.dirname(path.abspath(__file__)), 'data')


class AttributeLoader(object):
    """
    Base class AttributeLoader (should not be instantiated)
    Sets the attributes of a given instance based on data in textfiles
    or a database.

    The essential difference between these two is that for textfiles, the names of
    crops, units, prots, etc... are embedded in the key name, while database
    records will refer to crop_id's, unit, prot, etc... directly as integers.
    """
    def get_value_crop(self, tag, v):
        """
        Change crop insurance and gov pmt choice values to appropriate enum values
        if needed for choices like 'insure_corn'.
        Expects a tag name and an int or float value (v)
        """
        levels = 'level, sco_level, eco_level'.split()
        val = (Ins(v) if tag == 'insure' else Unit(v) if tag == 'unit' else
               Prot(v) if tag == 'protection' else
               to_lvl(v) if tag in levels else
               Prog(v) if tag == 'program' else v)
        return val


class DatabaseAttributeLoader(AttributeLoader):
    """
    Concrete class DatabaseAttributeLoader
    Handles loading attribute data from a database.
    """
    def set_attrs_from_pairs(self, inst):
        """
        Set the given object's attributes based on key/value pairs.
        Crop-specific and insurance premium attributes have dict values.
        This greatly reduces the number of attributes for the current object.
        """
        prem_pairs = self.group_values_ins_prem(
            self.load_crop_ins_premium_tuples(inst.crop_year))
        crop_pairs, simple = self.group_values_crop(
            self.load_model_and_user_tuples(inst.crop_year))
        pairs = crop_pairs + prem_pairs + simple
        for k, v in pairs:
            setattr(inst, k, v)

    def load_crop_ins_premium_tuples(self, attr):
        """
        Query the database to get detail records for crop insurance
        Generate a list of tuples from crop insurance premium details
        """
        # TODO:
        details = []
        self.group_values_ins_premium(details)

    def load_model_and_user_tuples(self, attr):
        """
        Generate a list of tuples from model and user data
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
        Given an iterable of crop-specific details, return a,
        shorter list of key/value pairs where each value is a dict with key Crop and
        crop-specific values.
        """
        groups = {}
        for det in with_crop:
            val = self.get_value_crop(det.name, det.value)
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


class TextfileAttributeLoader(AttributeLoader):
    """
    Concrete class TextfileAttributeLoader
    Handles loading attribute data from textfiles.
    """
    def __init__(self, filenames):
        self.filenames = filenames.split()

    def set_attrs_from_pairs(self, inst):
        """
        Set the given object's attributes based on key/value pairs.
        Crop-specific and insurance premium attributes have dict values.
        This greatly reduces the number of attributes for the current object.
        """
        prem_filenames = [fname for fname in self.filenames
                          if fname.find('crop_ins_premiums') >= 0]
        std_filenames = [fname for fname in self.filenames
                         if fname.find('crop_ins_premiums') < 0]
        prem_pairs = self.group_values_ins_prem(
            self.load_key_value_pairs(inst.crop_year, prem_filenames))
        crop_pairs, simple = self.group_values_crop(
            self.load_key_value_pairs(inst.crop_year, std_filenames))
        pairs = prem_pairs + crop_pairs + simple
        for k, v in pairs:
            setattr(inst, k, v)

    def load_key_value_pairs(self, crop_year, filenames):
        """
        Load key/value pairs from all specified DATA_FILES
        return a list with all the key/value pairs
        """
        pairs = []
        for name in filenames:
            filepath = path.join(DATADIR, f'{crop_year}_{name}.txt')
            pairs += self.load_textfile(filepath)
        return pairs

    def load_textfile(self, filename):
        """
        Load a textfile with the given name into a list of key/value pairs,
        ignoring blank lines and comment lines that begin with '#'
        """
        with open(filename) as f:
            contents = f.read()

        lines = [line.strip() for line in contents.strip().split('\n')
                 if len(line.strip()) > 0 and line[0] != '#']
        pairs = [line.split() for line in lines]
        return [(k, to_number(v)) for k, v in pairs]

    def group_values_crop(self, pairs):
        """
        Given an iterable of key/value pairs, with string keys and Number values,
        create two lists, one with keys ending in a crop name, (with_crop),
        and one with the rest (simple).
        Return both lists after mapping with_crop to a new list with dict values.
        and merge them into a new key/value pair with
          key: the original key with crop name removed,
          value: a dict with key crop and original value.
        Return a list of key/dict-valued pairs and a list of simple pairs.
        """
        crops = 'corn soy wheat fullsoy dcsoy'.split()
        pat = f'^(.*)_({"|".join(crops)})$'
        with_crop = []
        simple = []
        for k, v in pairs:
            m = re.match(pat, k)
            if m:
                with_crop.append((m.groups(), self.get_value_crop(m.groups()[0], v)))
            else:
                simple.append((k, v))
        return self.group_crop(with_crop, crops), simple

    def group_crop(self, with_crop, crops):
        """
        Given a list of crop-specific ungrouped key/value pairs, return a new, shorter
        list of key/value pairs where each value is a dict with key Crop and
        crop-specific values.
        """
        groups = {}
        for (name, crop), v in with_crop:
            groups.setdefault(name, {})[Crop(crops.index(crop))] = v
        return list(groups.items())

    def group_values_ins_prem(self, pairs):
        """
        Given a list of key/value pairs, reorganize them into two lists by filtering
        and processing base premiums, sco premiums and eco premiums in three
          filter steps.  The resulting lists are:
        dicts - a list containing three dicts, containing premiums for different
          crop insurance choices.
        simple - a list of key/value pairs which don't represent premiums.
        """
        units = 'area ent'.split()
        prots = 'rp rphpe yo'.split()
        crops = 'corn soy'.split()
        names = 'premium sco_premium eco_premium'.split()
        pats = [
            (f'^({"|".join(units)})_({"|".join(prots)})_({"|".join(crops)})' +
             f'_({"|".join(str(i) for i in range(50, 91, 5))})$'),
            (f'^sco_({"|".join(prots)})_({"|".join(crops)})' +
             f'_({"|".join(str(i) for i in range(50, 86, 5))})_86$'),
            (f'^eco_({"|".join(prots)})_({"|".join(crops)})_86_(90|95)$'), ]
        return self.build_dicts(pairs, pats, names, units, prots, crops)

    def build_dicts(self, pairs, pats, names, units, prots, crops):
        """
        Build up a list of pairs (name, dict) from pairs with crop ins premiums,
        and return this list along with the remaining simple pairs.
        """
        dicts = []
        for pat, name in zip(pats, names):
            prem, pairs = self.group_matches_ins_prem(pairs, pat, units, prots, crops)
            dicts.append((name, prem))
        if pairs:
            raise ValueError("Expected file contents to include only crop ins premiums")
        return dicts

    def group_matches_ins_prem(self, pairs, pat, units, prots, crops):
        """
        Given a list of key/value pairs, a pattern to match and some name lists,
        return a dict (prem) with premiums for the crop ins type constructed from pairs
        whose keys match the given pattern.  Also return a list (simple)
        with the unmatched pairs.
        """
        simple = []
        prem = {}
        for k, v in pairs:
            m = re.match(pat, k)
            if m:
                prem[self.make_prem_choice(m, units, prots, crops)] = v
            else:
                simple.append((k, v))
        return prem, simple

    def make_prem_choice(self, m, units, prots, crops):
        """
        Given a match object and some name lists, return a tuple representing a crop
        insurance choice
        """
        if len(m.groups()) == 4:
            u, p, c, lvl = m.groups()
            choice = (Unit(units.index(u)), Prot(prots.index(p)), Crop(crops.index(c)),
                      to_lvl(lvl))
        else:
            p, c, lvl = m.groups()
            choice = (Prot(prots.index(p)), Crop(crops.index(c)), to_lvl(lvl))
        return choice


def to_number(s):
    """
    Convert a number string to a float or int
    """
    return float(s) if '.' in s else int(s)


def to_lvl(v):
    """
    Helper to convert an int to a Lvl IntEnum in some cases
    """
    return (Lvl.NONE if v == 'NONE' else Lvl.DFLT if v == 'DFLT' else int(v))
