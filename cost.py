"""
Module cost

Contains a single class, Cost, which loads its data from text files
for a given crop year when an instance is created.  Its main function
is to return total estimated cost for the farm for the given crop year
corresponding to an arbitrary sensitivity factor for yield.
"""
from analysis import Analysis


class Cost(Analysis):
    """
    Computes total estimated cost for the farm crop year
    corresponding to an arbitrary sensitivity factor for yield.

    Sample usage in a python or ipython console:
      from cost import Cost
      c = Cost(2023)
      print(c.total_cost()    # yield factor defaults to 1
      print(c.total_cost(yf=.7) # specifies yield factor
    """
    DATA_FILES = 'farm_data cost_data'

    def __init__(self, *args, **kwargs):
        super(Cost, self).__init__(*args, **kwargs)

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
        M16, N16: Total fertilizer cost for specified crop and optional yf
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return (self.yield_indep_repl_fert_crop(crop) +
                self.yield_dep_repl_fert_crop(crop, yf))

    def total_fert(self, yf=1):
        """
        O16: Total fertilizer cost with optional yf
        """
        return sum(
            [self.total_fert_crop(crop, yf)
             for crop in ['corn', 'soy']])

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
        M19, N19: The diesel cost for the specified crop with optional yf
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return (self.clear_diesel_cost_crop(crop, yf) +
                self.dyed_diesel_cost_crop(crop))

    def diesel_cost(self, yf=1):
        """
        O19: The total diesel cost with optional yf
        """
        return sum([self.diesel_cost_crop(crop, yf)
                    for crop in ['corn', 'soy']])

    # GAS AND ELECTRICITY
    # -------------------
    def gas_electric_cost_crop(self, crop, yf=1):
        """
        M20, N20: The gas and electric cost for the crop, scaled by yield
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return round(self.c('gas_electric', crop) * yf)

    def gas_electric_cost(self, yf=1):
        """
        O20: The overall gas and electric cost scaled by yield
        """
        return (sum([self.gas_electric_cost_crop(crop, yf)
                     for crop in ['corn', 'soy']]))

    # TOTALS
    # ------
    def total_variable_cost_crop(self, crop, yf=1):
        """
        M26, N26
        The total variable cost for the crop, excluding net crop insurance
        with some components scaled by yield.
        Note: wheat is considered a component of soy for revenue and cost
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return (
            (self.incremental_wheat_cost if crop == 'soy' else 0) +
            self.c('seed_plus_treatment', crop) +
            self.c('chemicals', crop) +
            self.c('wind_peril_premium', crop) +
            self.c('minus_wind_peril_indemnity', crop) +
            self.total_fert_crop(crop, yf) +
            self.diesel_cost_crop(crop, yf) +
            self.gas_electric_cost_crop(crop, yf))

    def total_variable_cost(self, yf=1):
        """
        O26: The total of variable costs, scaled by yield
        """
        return sum([self.total_variable_cost_crop(crop, yf)
                    for crop in ['corn', 'soy']])

    # OVERHEAD
    # --------

    # PAYROLL
    # -------
    def annual_payroll_crop(self, crop):
        """
        Payroll Allocation F12, G12
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return self.tot_annual_payroll * self.c('payroll_alloc', crop)

    def frac_projected_yield_crop(self, crop, yf=1):
        """
        Payroll Allocation F21, G21
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return (self.proj_yield_farm_crop(crop) * yf /
                self.c('budgetted_yield', crop))

    def overtime_at_budgetted_yield(self, crop):
        """
        Payroll Allocation F23, G23
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return self.annual_payroll_crop(crop) * self.payroll_frac_ot

    def overtime_at_actual_yield(self, crop, yf=1):
        """
        Payroll Allocation F25, G25
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return (self.overtime_at_budgetted_yield(crop) *
                self.frac_projected_yield_crop(crop, yf))

    def payroll_yield_adjusted_crop(self, crop, yf=1):
        """
        Payroll Allocation F27, G27
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return round(
            self.annual_payroll_crop(crop) +
            self.overtime_at_actual_yield(crop, yf) -
            self.overtime_at_budgetted_yield(crop))

    def total_payroll_yield_adjusted(self, yf=1):
        """
        O29: The total payroll cost, with overtime scaled by yield
        """
        return sum([self.payroll_yield_adjusted_crop(crop, yf)
                    for crop in ['corn', 'soy']])

    # TOTALS
    # ------
    def total_overhead_crop(self, crop, yf=1):
        """
        M37, N37
        The total of all overhead items for the given crop, scaled by yield
        """
        if crop not in ['corn', 'soy']:
            raise ValueError("crop must be 'corn' or 'soy'")

        return (
            self.payroll_yield_adjusted_crop(crop, yf) +
            self.c('replacement_capital', crop) +
            self.c('building_equip_repairs', crop) +
            self.c('shop_tools_supplies_parts', crop) +
            self.c('business_insurance', crop) +
            self.c('other_utilities', crop) +
            self.c('professional_fees', crop) +
            self.c('other_operating_expense', crop))

    def total_overhead(self, yf=1):
        """
        O37: The total overhead cost, scaled by yield
        """
        return sum([self.total_overhead_crop(crop, yf)
                    for crop in ['corn', 'soy']])

    def total_prod_costs_before_land_exp_crop(self, crop, yf=1):
        """
        M39, N39
        """
        return (self.total_variable_cost_crop(crop, yf) +
                self.total_overhead_crop(crop, yf))

    def total_prod_costs_before_land_exp(self, yf=1):
        """
        O39
        """
        return sum([self.total_prod_costs_before_land_exp_crop(crop, yf)
                    for crop in ['corn', 'soy']])

    def total_land_expenses(self, yf=1):
        """
        Helper for cash flow
        """
        return sum([self.c('total_land_expenses', crop)
                    for crop in ['corn', 'soy']])

    def total_cost_crop(self, crop, yf=1):
        """
        M48, N48
        """
        return (self.total_prod_costs_before_land_exp_crop(crop, yf) +
                self.c('total_land_expenses', crop))

    def total_cost(self, yf=1):
        """
        The total cost, scaled by yield
        """
        return sum([self.total_cost_crop(crop, yf)
                    for crop in ['corn', 'soy']])
