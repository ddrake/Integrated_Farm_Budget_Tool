"""
Module cost

Contains a single class, Cost, which loads its data from text files
for a given crop year when an instance is created.  Its main function
is to return total estimated cost for the farm for the given crop year
corresponding to an arbitrary sensitivity factor for yield.
"""


class Cost(object):
    """
    Computes total estimated cost for the farm crop year
    corresponding to an arbitrary sensitivity factor for yield.

    Sample usage in a python or ipython console:
      from cost import Cost
      c = Cost(2023)
      print(c.total_cost()    # yield factor defaults to 1
      print(c.total_cost(yf=.7) # specifies yield factor
    """
    def __init__(self, crop_year, overrides=None):
        """
        Get an instance for the given crop year and set attributes from
        key/value pairs read from text files.
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
        for name in 'farm_data cost_data'.split():
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

    def proj_yield_farm_crop(self, crop):
        """
        Helper method providing projected yields for all crops
        used in calculating fuel and payroll costs
        """
        if crop not in ['corn', 'soy', 'wheat']:
            raise ValueError("crop must be 'corn', 'soy' or 'wheat'")

        return (
            ((self.acres_wheat_dc_soy *
              self.proj_yield_farm_dc_soy +
              (self.acres_soy -
               self.acres_wheat_dc_soy) *
              self.proj_yield_farm_full_soy) / self.acres_soy)
            if crop == 'soy' else self.proj_yield_farm_corn
            if crop == 'corn' else self.proj_yield_farm_wheat)

    # VARIABLE COSTS
    # --------------

    # FERTILIZER
    # ----------
    def yield_dep_repl_fert_crop(self, crop, yf=1):
        """
        Yield-dependent replacement fertilizer for corn or soy
        scaled by yf
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return round(
            (self.c('dap', crop) +
             self.c('repl_potash', crop)) * yf)

    def yield_dep_repl_fert(self, yf=1):
        """
        Yield-dependent replacement fertilizer for crops
        """
        return sum([self.yield_dep_repl_fert_crop(crop, yf)
                    for crop in ['corn', 'soy']])

    def yield_indep_repl_fert_crop(self, crop):
        """
        Yield-dependent replacement fertilizer for corn or soy
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return round(
            self.c('cur_est_fertiilizer_cost', crop) -
            self.yield_dep_repl_fert_crop(crop, yf=1))

    def yield_indep_repl_fert(self):
        """
        Yield-dependent replacement fertilizer for crops
        """
        return sum([self.yield_indep_repl_fert_crop(crop)
                    for crop in ['corn', 'soy']])

    def total_fert_crop(self, crop, yf=1):
        """
        Total fertilizer cost for specified crop and optional yf
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return (self.yield_indep_repl_fert_crop(crop) +
                self.yield_dep_repl_fert_crop(crop, yf))

    def total_fert(self, yf=1):
        """
        Total fertilizer cost with optional yf
        """
        return sum(
            [self.total_fert_crop(crop, yf)
             for crop in ['corn', 'soy']])

    # INCREMENTAL WHEAT
    # -----------------

    def incremental_wheat_cost(self, yf=1):
        """
        Only the shipping component of incremental wheat
        is sensitized to yield
        """
        return round(
            self.incremental_wheat_cost_base +
            self.wheat_hauling_base * (yf - 1))

    # DIESEL FUEL
    # -----------
    def clear_diesel_base_cost_crop(self, crop):
        """
        The base cost of clear diesel for the specified crop
        used to compute the clear diesel cost for the crop
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return (
            self.clear_gpa_2018 * self.c('acres', crop) *
            self.clear_diesel_price * self.c('fuel_alloc', crop))

    def clear_diesel_cost_crop(self, crop, yf=1):
        """
        The clear diesel cost for the specified crop.  Only the part
        of clear diesel allocated to hauling is scaled by yield.
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return round(
            self.clear_diesel_base_cost_crop(crop) *
            ((1 - self.est_haul_alloc) +
             self.est_haul_alloc * self.proj_yield_farm_crop(crop) /
             self.c('yield_2018', crop) * yf))

    def dyed_diesel_cost_crop(self, crop):
        """
        The dyed diesel cost for the specified crop
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return round(
            self.dyed_gpa_2018 * self.c('acres', crop) *
            self.dyed_diesel_price * self.c('fuel_alloc', crop))

    def diesel_cost_crop(self, crop, yf=1):
        """
        The diesel cost for the specified crop with optional yf
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return (self.clear_diesel_cost_crop(crop, yf) +
                self.dyed_diesel_cost_crop(crop))

    def diesel_cost(self, yf=1):
        """
        The total diesel cost with optional yf
        """
        return sum([self.diesel_cost_crop(crop, yf)
                    for crop in ['corn', 'soy']])

    # GAS AND ELECTRICITY
    # -------------------
    def gas_electric_cost_crop(self, crop, yf=1):
        """
        The gas and electric cost for the crop, scaled by yield
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return round(self.c('gas_electric', crop) * yf)

    def gas_electric_cost(self, yf=1):
        """
        The overall gas and electric cost scaled by yield
        """
        return (sum([self.gas_electric_cost_crop(crop, yf)
                     for crop in ['corn', 'soy']]))

    # TOTALS
    # ------
    def total_variable_cost_crop(self, crop, yf=1):
        """
        The total variable cost for the crop, scaled by yield.
        """
        if crop not in ['corn', 'soy', 'wheat']:
            raise ValueError("crop must be 'corn', 'soy' or 'wheat'")

        return (
            self.incremental_wheat_cost(yf) if crop == 'wheat'
            else (
                self.c('seed_plus_treatment', crop) +
                self.c('chemicals', crop) +
                self.c('wind_peril_premium', crop) +
                self.c('minus_wind_peril_indemnity', crop) +
                self.total_fert_crop(crop, yf) +
                self.diesel_cost_crop(crop, yf) +
                self.gas_electric_cost_crop(crop, yf)))

    def total_variable_cost(self, yf=1):
        """
        The total of variable costs, scaled by yield
        """
        return sum([self.total_variable_cost_crop(crop, yf)
                    for crop in ['corn', 'soy', 'wheat']])

    # OVERHEAD
    # --------

    # PAYROLL
    # -------
    def payroll_crop(self, crop, yf=1):
        """
        The overtime portion of the payroll is scaled by the ratio of
        estimated yield (including yf) to 2018 yield.
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return round(
            self.est_payroll * self.c('payroll_alloc', crop) *
            (1 + self.payroll_frac_ot *
             (self.proj_yield_farm_crop(crop) * yf /
              self.c('yield_2018', crop) - 1)))

    def total_payroll(self, yf=1):
        """
        The total payroll cost, with overtime scaled by yield
        """
        return sum([self.payroll_crop(crop, yf)
                    for crop in ['corn', 'soy']])

    # TOTALS
    # ------
    def total_overhead_crop(self, crop, yf=1):
        """
        The total of all overhead items for the given crop, scaled by yield
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return (
            self.payroll_crop(crop, yf) +
            self.c('replacement_capital', crop) +
            self.c('building_equip_repairs', crop) +
            self.c('shop_tools_supplies_parts', crop) +
            self.c('business_insurance', crop) +
            self.c('other_utilities', crop) +
            self.c('professional_fees', crop) +
            self.c('other_operating_expense', crop) +
            self.c('total_land_expenses', crop))

    def total_overhead(self, yf=1):
        """
        The total overhead cost, scaled by yield
        """
        return sum([self.total_overhead_crop(crop, yf)
                    for crop in ['corn', 'soy']])

    def total_cost(self, yf=1):
        """
        The total cost, scaled by yield
        """
        return (self.total_variable_cost(yf) +
                self.total_overhead(yf))
