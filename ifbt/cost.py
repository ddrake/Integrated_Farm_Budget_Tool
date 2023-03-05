"""
Module cost

Contains a single class, Cost, which loads its data from text files
for a given crop year when an instance is created.  Its main function
is to return total estimated cost for the farm for the given crop year
corresponding to an arbitrary sensitivity factor for yield.
"""
from .analysis import Analysis
from .util import Crop, crop_in


class Cost(Analysis):
    """
    Computes total estimated cost for the farm crop year
    corresponding to an arbitrary sensitivity factor for yield.

    Sample usage in a python or ipython console:
      from ifbt import Cost
      c = Cost(2023)
      c.total_cost()         # yield factor defaults to 1
      c.total_cost(yf=.7)    # specifies yield factor
    """
    DATA_FILES = 'farm_data cost_data'

    def __init__(self, *args, **kwargs):
        """
        Just initialize the base class
        """
        super().__init__(*args, **kwargs)

    # VARIABLE COSTS
    # --------------

    # FERTILIZER
    # ----------
    @crop_in(Crop.CORN, Crop.SOY)
    def yield_dep_repl_fert_crop(self, crop, yf=1):
        """
        Yield-dependent, sensitized replacement fertilizer for the crop.
        """
        return round(
            (self.dap[crop] +
             self.repl_potash[crop]) * yf)

    def yield_dep_repl_fert(self, yf=1):
        """
        Yield-dependent, sensitized replacement fertilizer for crops.
        """
        return sum([self.yield_dep_repl_fert_crop(crop, yf)
                    for crop in [Crop.CORN, Crop.SOY]])

    @crop_in(Crop.CORN, Crop.SOY)
    def yield_indep_repl_fert_crop(self, crop, yf=1):
        """
        Yield-dependent, sensitized replacement fertilizer for the crop.
        """
        return round(
            self.cur_est_fertiilizer_cost[crop] -
            self.yield_dep_repl_fert_crop(crop, yf))

    def yield_indep_repl_fert(self):
        """
        Yield-dependent replacement fertilizer for crops
        """
        return sum([self.yield_indep_repl_fert_crop(crop)
                    for crop in [Crop.CORN, Crop.SOY]])

    @crop_in(Crop.CORN, Crop.SOY)
    def total_fert_crop(self, crop, yf=1):
        """
        M16, N16: Yield-sensitized total fertilizer cost for specified crop.
        """
        return (self.yield_indep_repl_fert_crop(crop) +
                self.yield_dep_repl_fert_crop(crop, yf))

    def total_fert(self, yf=1):
        """
        O16: Yield-sensitized total fertilizer cost over both crops.
        """
        return sum(
            [self.total_fert_crop(crop, yf)
             for crop in [Crop.CORN, Crop.SOY]])

    # DIESEL FUEL
    # -----------
    @crop_in(Crop.CORN, Crop.SOY)
    def clear_diesel_base_cost_crop(self, crop):
        """
        Base cost of clear diesel for the specified crop
        used to compute the clear diesel cost for the crop
        """
        return (
            self.clear_gpa_2018 * self.acres[crop] *
            self.clear_diesel_price * self.fuel_alloc[crop])

    @crop_in(Crop.CORN, Crop.SOY)
    def clear_diesel_cost_crop(self, crop, yf=1):
        """
        Clear diesel cost for the specified crop.  Only the part
        of clear diesel allocated to hauling is yield-sensitized.
        """
        return round(
            self.clear_diesel_base_cost_crop(crop) *
            ((1 - self.est_haul_alloc) +
             self.est_haul_alloc * self.projected_yield_crop(crop, yf) /
             self.yield_2018[crop]))

    @crop_in(Crop.CORN, Crop.SOY)
    def dyed_diesel_cost_crop(self, crop):
        """
        Dyed diesel cost for the specified crop.
        """
        return round(
            self.dyed_gpa_2018 * self.acres[crop] *
            self.dyed_diesel_price * self.fuel_alloc[crop])

    @crop_in(Crop.CORN, Crop.SOY)
    def diesel_cost_crop(self, crop, yf=1):
        """
        M19, N19: Yield-sensitized diesel cost for the specified crop
        """
        return (self.clear_diesel_cost_crop(crop, yf) +
                self.dyed_diesel_cost_crop(crop))

    def diesel_cost(self, yf=1):
        """
        O19: Yield-sensitized total diesel cost.
        """
        return sum([self.diesel_cost_crop(crop, yf)
                    for crop in [Crop.CORN, Crop.SOY]])

    # GAS AND ELECTRICITY
    # -------------------
    @crop_in(Crop.CORN, Crop.SOY)
    def gas_electric_cost_crop(self, crop, yf=1):
        """
        M20, N20: Yield-sensitized gas and electric cost for the crop.
        """
        return round(self.gas_electric[crop] * yf)

    def gas_electric_cost(self, yf=1):
        """
        O20: Yield-sensitized overall gas and electric cost.
        """
        return (sum([self.gas_electric_cost_crop(crop, yf)
                     for crop in [Crop.CORN, Crop.SOY]]))

    # TOTALS
    # ------
    @crop_in(Crop.CORN, Crop.SOY)
    def total_variable_cost_crop(self, crop, yf=1):
        """
        M26, N26: Yield-sensitized total variable cost for the crop, excluding
        net crop insurance.
        Note: wheat is considered a component of soy for revenue and cost
        """
        return (
            (self.incremental_wheat_cost if crop == Crop.SOY else 0) +
            self.seed_plus_treatment[crop] +
            self.chemicals[crop] +
            self.wind_peril_premium[crop] +
            self.minus_wind_peril_indemnity[crop] +
            self.total_fert_crop(crop, yf) +
            self.diesel_cost_crop(crop, yf) +
            self.gas_electric_cost_crop(crop, yf))

    def total_variable_cost(self, yf=1):
        """
        O26: Yield-sensitized total of variable costs.
        """
        return sum([self.total_variable_cost_crop(crop, yf)
                    for crop in [Crop.CORN, Crop.SOY]])

    # OVERHEAD
    # --------

    # PAYROLL
    # -------
    @crop_in(Crop.CORN, Crop.SOY)
    def annual_payroll_crop(self, crop):
        """
        Payroll Allocation F12, G12: Allocate historical payroll between the crops.
        """
        return self.total_annual_payroll * self.payroll_alloc[crop]

    @crop_in(Crop.CORN, Crop.SOY)
    def frac_projected_yield_crop(self, crop, yf=1):
        """
        Payroll Allocation F21, G21: Compute the ratio of sensitized, projected yield
        to budgetted yield for the given crop.
        """
        return (self.projected_yield_crop(crop, yf) /
                self.budgetted_yield[crop])

    @crop_in(Crop.CORN, Crop.SOY)
    def overtime_at_budgetted_yield(self, crop):
        """
        Payroll Allocation F23, G23: Get the overtime cost for historical payroll.
        """
        return self.annual_payroll_crop(crop) * self.payroll_frac_ot

    @crop_in(Crop.CORN, Crop.SOY)
    def overtime_at_actual_yield(self, crop, yf=1):
        """
        Payroll Allocation F25, G25: Get the overtime cost corresponding
        to actual sensitized, projected yield.
        """
        return (self.overtime_at_budgetted_yield(crop) *
                self.frac_projected_yield_crop(crop, yf))

    @crop_in(Crop.CORN, Crop.SOY)
    def payroll_yield_adjusted_crop(self, crop, yf=1):
        """
        Payroll Allocation F27, G27: Get the sensitized, projected payroll cost
        for the given crop.
        """
        return round(
            self.annual_payroll_crop(crop) +
            self.overtime_at_actual_yield(crop, yf) -
            self.overtime_at_budgetted_yield(crop))

    def total_payroll_yield_adjusted(self, yf=1):
        """
        Payroll Allocation O29: The yield-sensitized total payroll cost.
        """
        return sum([self.payroll_yield_adjusted_crop(crop, yf)
                    for crop in [Crop.CORN, Crop.SOY]])

    # TOTALS
    # ------
    @crop_in(Crop.CORN, Crop.SOY)
    def total_overhead_crop(self, crop, yf=1):
        """
        FullyBurdenedEstimate M37, N37:
        The yield-sensitized total of all overhead items for the given crop.
        """
        return (
            self.payroll_yield_adjusted_crop(crop, yf) +
            self.replacement_capital[crop] +
            self.building_equip_repairs[crop] +
            self.shop_tools_supplies_parts[crop] +
            self.business_insurance[crop] +
            self.other_utilities[crop] +
            self.professional_fees[crop] +
            self.other_operating_expense[crop])

    def total_overhead(self, yf=1):
        """
        FullyBurdenedEstimate O37: The yield-sensitized total overhead cost.
        """
        return sum([self.total_overhead_crop(crop, yf)
                    for crop in [Crop.CORN, Crop.SOY]])

    @crop_in(Crop.CORN, Crop.SOY)
    def total_prod_costs_before_land_exp_crop(self, crop, yf=1):
        """
        FullyBurdenedEstimate M39, N39: Yield-sensitized total production cost
        for the given crop, excluding land expenses.
        """
        return (self.total_variable_cost_crop(crop, yf) +
                self.total_overhead_crop(crop, yf))

    def total_prod_costs_before_land_exp(self, yf=1):
        """
        FullyBurdenedEstimate O39: Yield-sensitized total production cost over
        both crops before land expenses.
        """
        return sum([self.total_prod_costs_before_land_exp_crop(crop, yf)
                    for crop in [Crop.CORN, Crop.SOY]])

    def total_land_expenses_over_crops(self, yf=1):
        """
        FullyBurdenedEstimate O46: Yield-sensitized total land expenses
        used by cash flow module
        """
        return sum([self.total_land_expenses[crop]
                    for crop in [Crop.CORN, Crop.SOY]])

    @crop_in(Crop.CORN, Crop.SOY)
    def total_cost_crop(self, crop, yf=1):
        """
        FullyBurdenedEstimate M48, N48: Yield-sensitized total cost for the
        specified crop.
        """
        return (self.total_prod_costs_before_land_exp_crop(crop, yf) +
                self.total_land_expenses[crop])

    def total_cost(self, yf=1):
        """
        FullyBurdenedEstimate O48: Yield-sensitized total cost of both crops.
        """
        return sum([self.total_cost_crop(crop, yf)
                    for crop in [Crop.CORN, Crop.SOY]])
