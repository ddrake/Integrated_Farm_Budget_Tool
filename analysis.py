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
