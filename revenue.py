"""
Module revenue

Contains a single class, Revenue, which loads its data from a text file
for a given crop year when an instance is created.  Its main function
is to return total estimated revenue for the farm for the given crop year
corresponding to arbitrary sensitivity factors for price and yield.
"""


class Revenue(object):
    """
    Computes total estimated revenue for the farm crop year
    corresponding to arbitrary sensitivity factors for price and yield.

    Sample usage in a python or ipython console:
      from revenue import Revenue
      r = Revenue(2023)
      print(r.total_revenue()        # pf and yf default to 1
      print(r.total_revenue(.9, 1.1) # specifies both price and yield factors
      print(r.total_revenue(yf=1.2)  # uses default for pf
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
                setattr(self, k, float(v) if '.' in v else int(v))

    def _load_required_data(self):
        """
        Load individual revenue items from data file
        return a list with all the key/value pairs
        """
        data = []
        for name in 'farm_data revenue_data'.split():
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

    def deliverable_bu_corn(self, yf=1):
        """
        Estimated corn bushels with shrink and yield factor applied
        """
        return (self.acres_corn *
                self.proj_yield_farm_corn *
                (1 - self.est_shrink_corn/100.) * yf)

    def estimated_soy_bushels(self):
        """
        Compute estimated raw total soy bushels
        considering wheat/dc soy acres
        """
        return (self.acres_wheat_dc_soy *
                self.proj_yield_farm_dc_soy +
                (self.acres_soy -
                 self.acres_wheat_dc_soy) *
                self.proj_yield_farm_full_soy)

    def projected_yield_soy(self):
        """
        Convenience method providing estimated overall soy yield
        """
        return self.estimated_soy_bushels() / self.acres_soy

    def deliverable_bu_soy(self, yf=1):
        """
        Estimated soy bushels with shrink and yield factor applied
        """
        return (self.estimated_soy_bushels() *
                (1 - self.est_shrink_soy/100.) * yf)

    def revenue_uncontracted_crop(self, crop, pf=1, yf=1):
        """
        Estimated revenue of uncontracted corn or soy for specified
        pf and yf rounded to whole dollars
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return round(
            ((self.deliverable_bu_corn(yf) if crop == 'corn' else
              self.deliverable_bu_soy(yf)) -
             self.c('contract_bu', crop)) *
            (self.c('fall_futures_price', crop) * pf +
             self.c('est_basis', crop)) *
            (1 - self.c('est_deduct', crop)/100.))

    def revenue_uncontracted(self, pf=1, yf=1):
        """
        Estimated revenue of uncontracted grain for specified
        pf and yf in whole dollars
        """
        return sum(
            [self.revenue_uncontracted_crop(crop, pf, yf)
             for crop in ['corn', 'soy']])

    def revenue_contracted_crop(self, crop):
        """
        Expected revenue from contracted corn or soy rounded to whole dollars
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return round(
            self.c('contract_bu', crop) *
            self.c('avg_contract_price', crop) *
            (1 - self.c('est_deduct', crop)/100.))

    def revenue_contracted(self, pf=1):
        """
        Expected revenue from contracted grain in whole dollars
        """
        return sum([self.revenue_contracted_crop(crop)
                    for crop in ['corn', 'soy']])

    def total_revenue_crop(self, crop, pf=1, yf=1):
        """
        Convenience method providing total revenue for a given
        crop based on price and yield factors
        """
        if crop not in ['corn', 'soy', 'wheat']:
            raise ValueError("crop must be 'corn', 'soy' or 'wheat'")
        return (self.revenue_wheat if crop == 'wheat' else
                self.revenue_contracted_crop(crop) +
                self.revenue_uncontracted_crop(
                    crop, pf, yf))

    def total_revenue_grain(self, pf=1, yf=1):
        """
        Convenience method providing total grain revenue for the crop year
        based on price and yield factors
        """
        return sum([self.total_revenue_crop(crop, pf, yf)
                    for crop in ['corn', 'soy', 'wheat']])

    def total_revenue_other(self):
        """
        Total of other revenue *excluding* government program payments
        """
        return sum([self.c('ppp_loan_forgive', crop) +
                    self.c('mfp_cfap', crop) +
                    self.c('rental_revenue', crop) +
                    self.c('other_revenue', crop)
                    for crop in ['corn', 'soy']])

    def total_revenue(self, pf=1, yf=1):
        """
        Total revenue reflecting current estimates and price/yield factors
        """
        return sum([self.revenue_wheat,
                    self.revenue_uncontracted(pf, yf),
                    self.revenue_contracted(),
                    self.total_revenue_other()])
