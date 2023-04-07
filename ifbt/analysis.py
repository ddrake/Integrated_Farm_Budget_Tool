"""
Module analysis

Defines class Analysis, the base class for all ifbt components
"""
from collections import abc

from .attribute_loader import TextfileAttributeLoader, DatabaseAttributeLoader
from .util import Crop, crop_in, ALL_CROPS, BASE_CROPS, SEASON_CROPS


class Analysis(object):
    """
    Base class for all components of the integrated farm budget tool
    """
    def __init__(self, crop_year, *args, overrides=None, **kwargs):
        """
        Get an instance for the given crop year, then load its attributes
        from text files or database querysets.  If overrides are provided,
        override the specified attributes.
        """
        self.crop_year = crop_year
        klass = self.__class__
        attrloader = (TextfileAttributeLoader(klass.DATA_FILES)
                      if hasattr(klass, 'DATA_FILES') else
                      DatabaseAttributeLoader())
        attrloader.set_attrs(self)

        if overrides is not None:
            self._update_attrs_from_overrides(overrides)

    def __repr__(self):
        class_name = type(self).__name__
        return '{}({!r})'.format(class_name, self.crop_year)

    def _update_attrs_from_overrides(self, overrides):
        """
        Override attributes specified in the 'overrides' mapping
        """
        for k, v in overrides.items():
            if isinstance(v, abc.Mapping):
                attr = getattr(self, k)
                attr.update(v)
                setattr(self, k, attr)
            else:
                setattr(self, k, v)

    def base_crop(self, crop=None):
        """
        Get the Base Crop for the provided crop or the instance's crop if not given.
        """
        if crop is None:
            crop = self.crop
        return Crop.SOY if crop in (Crop.FULL_SOY, Crop.DC_SOY) else crop

    def acres_soy(self):
        """
        Compute the total soy acres
        """
        return self.acres[Crop.DC_SOY] + self.acres[Crop.FULL_SOY]

    @crop_in(*ALL_CROPS)
    def acres_crop(self, crop):
        return self.acres_soy() if crop == Crop.SOY else self.acres[crop]

    def projected_bu_soy(self, yf=1):
        """
        Compute the projected, sensitized raw total soy bushels
        considering wheat/dc soy acres
        """
        return ((self.acres[Crop.DC_SOY] * self.proj_yield_farm[Crop.DC_SOY] +
                 self.acres[Crop.FULL_SOY] * self.proj_yield_farm[Crop.FULL_SOY]) * yf)

    @crop_in(*SEASON_CROPS)
    def projected_bu_scrop(self, crop, yf=1):
        """
        Compute the projected, sensitized total bushels for the given season crop
        """
        return self.acres[crop] * self.proj_yield_farm[crop] * yf

    @crop_in(*BASE_CROPS)
    def projected_bu_crop(self, crop, yf=1):
        """
        Compute the projected, sensitized total bushels for the given base crop
        """
        return (self.projected_bu_soy(yf) if crop == Crop.SOY else
                self.proj_yield_farm[crop] * self.acres[crop] * yf)

    @crop_in(*ALL_CROPS)
    def projected_yield_crop(self, crop, yf=1):
        """
        Compute the projected, sensitized yield for any crop
        """
        return (self.projected_bu_soy(yf)/self.acres_soy() if crop == Crop.SOY else
                self.proj_yield_farm[crop] * yf)

    # TOTALS
    # ------
    def total_planted_acres(self):
        return sum((self.acres[crop] for crop in SEASON_CROPS))

    def total_production_bushels(self, yf=1):
        return sum((self.projected_bu_scrop(crop, yf) for crop in SEASON_CROPS))
