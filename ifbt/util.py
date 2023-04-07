"""
Module util

Definitions used by many classes
"""

from enum import IntEnum
from functools import wraps

Crop = IntEnum('Crop', ['CORN', 'SOY', 'WHEAT', 'FULL_SOY', 'DC_SOY'], start=0)
Ins = IntEnum('Ins', ['NO', 'YES'], start=0)
Unit = IntEnum('Unit', ['AREA', 'ENT'], start=0)
Prot = IntEnum('Prot', ['RP', 'RPHPE', 'YO'], start=0)
Lvl = IntEnum('Lvl', ['NONE', 'DFLT'], start=0)
Prac = IntEnum('Prac', ['IRR', 'NONIRR', 'ALL'], start=1)

ALL_CROPS = [Crop.CORN, Crop.SOY, Crop.WHEAT, Crop.FULL_SOY, Crop.DC_SOY]
BASE_CROPS = [Crop.CORN, Crop.SOY, Crop.WHEAT]
SEASON_CROPS = [Crop.CORN, Crop.FULL_SOY, Crop.WHEAT, Crop.DC_SOY]


def crop_in(*crops):
    """
    Decorator for simplifying validation of permitted crops.
    Assumes it will be decorating a method (i.e. first positional argument 'self') and
    second positional argument 'crop'.  It would also be possible to use
    inspect.getArgSpec(f) to check for a parameter named 'crop'.
    """
    def decorator(f):
        @wraps(f)
        def new_f(*args, **kwds):
            if len(args) < 2 or args[1] not in ALL_CROPS:
                raise ValueError('The first argument must be a Crop')
            elif args[1] not in crops:
                crop_msg = ', '.join(str(c) for c in crops)
                raise ValueError(f'Crop must be one of: {crop_msg}')
            else:
                return f(*args, **kwds)
        return new_f
    return decorator
