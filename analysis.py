def crop_in(*crops):
    def decorator(f):
        def new_f(*args, **kwds):
            if args[1] not in crops:
                crop_msg = ', '.join([f"'{c}'" for c in crops])
                raise ValueError(f'Crop must be one of: {crop_msg}')
            else:
                return f(*args, **kwds)
        return new_f
    return decorator


class Analysis(object):
    """
    Base class for all components of the integrated farm budget tool
    """
    def __init__(self, crop_year, overrides=None):
        """
        Get an instance for the given crop year, then get a list of
        key/value pairs from the text file and make object attributes from it.
        """
        self.crop_year = crop_year
        for k, v in self._load_required_data():
            setattr(self, k, float(v) if '.' in v else int(v))
        if overrides is not None:
            for k, v in overrides.items():
                vnum = (v if isinstance(v, (int, float)) else
                        float(v) if '.' in v else int(v))
                setattr(self, k, vnum)

    def _load_required_data(self):
        """
        Load individual revenue items from data file
        return a list with all the key/value pairs
        """
        data = []
        for name in self.__class__.DATA_FILES.split():
            data += self._load_textfile(f'{self.crop_year}_{name}.txt')
        return data

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
        return [line.split() for line in lines]

    def c(self, s, crop):
        """
        Helper to simplify syntax for reading crop-dependent attributes
        imported from textfile
        """
        return getattr(self, f'{s}_{crop}')

    def projected_bu_soy(self, yf=1):
        """
        F12:
        Compute estimated raw total soy bushels considering wheat/dc soy acres
        """
        return ((self.acres_dc_soy *
                 self.proj_yield_farm_dc_soy +
                 (self.acres_soy -
                  self.acres_dc_soy) *
                 self.proj_yield_farm_full_soy) * yf)

    @crop_in('corn', 'soy')
    def projected_bu_crop(self, crop, yf=1):
        """
        GVBudget E12, F12
        """
        return (self.projected_bu_soy(yf) if crop == 'soy' else
                self.c('proj_yield_farm', crop) * self.c('acres', crop) * yf)

    def projected_yield_soy(self, yf=1):
        """
        Convenience method providing estimated overall soy yield
        """
        return self.projected_bu_soy(yf) / self.acres_soy

    @crop_in('corn', 'soy', 'full_soy', 'dc_soy', 'wheat')
    def projected_yield_crop(self, crop, yf=1):
        """
        Projected and sensitized yield for any crop
        """
        return (self.projected_yield_soy(yf) if crop == 'soy' else
                self.c('proj_yield_farm', crop) * yf)
