"""
Module analysis

Defines class Analysis, the base class for all ifbt components
"""
from collections import abc

from .attribute_loader import TextfileAttributeLoader, DatabaseAttributeLoader
from .util import Crop, crop_in


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

    def projected_bu_soy(self, yf=1):
        """
        Compute the projected, sensitized raw total soy bushels
        considering wheat/dc soy acres
        """
        return ((self.acres[Crop.DC_SOY] * self.proj_yield_farm[Crop.DC_SOY] +
                 (self.acres[Crop.SOY] - self.acres[Crop.DC_SOY]) *
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
