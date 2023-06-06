from .farm_year import FarmYear


class BudgetTable(object):

    ROW_LABELS = [
        'Crop Revenue', 'Average Realized Price/Bushel', 'ARC/PLC',
        "Other Gov't Payments", 'Crop Insurance Proceeds', 'Other Revenue',
        'Gross Revenue', 'Fertilizers', 'Pesticides', 'Seed', 'Drying', 'Storage',
        'Crop Insurance', 'Other', 'Total Direct Costs', 'Machine hire/lease',
        'Utilities', 'Machine Repair', 'Fuel and Oil (Inc. Irrigation)',
        'Light vehicle', 'Mach. Depreciation', 'Total Power Costs', 'Hired Labor',
        'Building repair and rent', 'Building depreciation', 'Insurance', 'Misc.',
        'Interest (non-land)', 'Other Costs', 'Total Overhead Costs',
        'Total Non-Land Costs', 'Yield Based Adjustment to Non-Land Costs',
        'Total Adjusted Non-Land Costs', 'Operator and Land Return', 'Land costs',
        'Revenue Based Adjustment to Land Rent', 'Adjusted Land Rent',
        'Owned Land Cost (Including/excluding Principal Payments)', 'Total Land Costs',
        'Total Costs', 'PRE-TAX INCOME/CASH FLOW']

    METHODS = """
        crop_revenue avg_realized_price gov_pmt crop_ins_indems
        other_revenue gross_revenue fertilizers pesticides seed
        drying storage crop_ins_prems other_direct_costs total_direct_costs
        machine_hire_lease utilities machine_repair fuel_and_oil light_vehicle
        machine_depreciation total_power_costs hired_labor building_repair_rent
        building_depreciation insurance misc interest_nonland other_costs
        total_overhead_costs total_nonland_costs yield_adj_to_nonland_costs
        total_adj_nonland_costs operator_and_land_return land_costs
        revenue_based_adjustment_to_land_rent adjusted_land_rent owned_land_cost
        total_land_cost total_cost pretax_amount""".split()

    def __init__(self, farm_year_id):
        """
        Get the farm year record.
        Get a queryset of all farm crops with budgets for the farm year
          ordered by farm_crop_type.  If no farm crops have budgets, return None.
          The view should check for None, and show a message about adding budgets.
        """
        self.farm_year = FarmYear.objects.get(pk=farm_year_id)
        self.farm_year.calc_gov_pmt()
        self.farm_crops = [fc for fc in
                           self.farm_year.farm_crops.all()
                           .order_by('farm_crop_type_id') if fc.has_budget()]

        # cached values in dollars
        self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        self.avg_realized_price = None
        self.gov_pmt = None
        self.crop_ins_indems = None
        self.other_revenue = None
        self.gross_revenue = None
        self.fertilizers = None
        self.pesticides = None
        self.seed = None
        self.drying = None
        self.storage = None
        self.crop_ins_prems = None
        self.other_direct_costs = None
        self.total_direct_costs = None
        self.machine_hire_lease = None
        self.utilities = None
        self.machine_repair = None
        self.fuel_and_oil = None
        self.light_vehicle = None
        self.machine_depreciation = None
        self.total_power_costs = None
        self.hired_labor = None
        self.building_repair_rent = None
        self.building_depreciation = None
        self.insurance = None
        self.misc = None
        self.interest_nonland = None
        self.other_costs = None
        self.total_overhead_costs = None
        self.total_nonland_costs = None
        self.yield_adj_to_nonland_costs = None
        self.total_adj_nonland_costs = None
        self.operator_and_land_return = None
        self.land_costs = None
        self.revenue_based_adjustment_to_land_rent = None
        self.adjusted_land_rent = None
        self.owned_land_cost = None
        self.total_land_cost = None
        self.total_cost = None
        self.pretax_amount = None

    def make_thousands(self):
        """
        Make the ($000) budget table
        """
        return [(n, getattr(self, m)(scaling='kd')) for n, m in
                zip(self.__class__.ROW_LABELS, self.__class__.METHODS)]

    def make_peracre(self):
        """
        Make the per acre budget table
        """
        return [getattr(self, m)(scaling='pa') for m in self.__class__.METHODS]

    def make_perbushel(self):
        """
        Make the per bushel budget table
        """
        return [getattr(self, m)(scaling='pb') for m in self.__class__.METHODS]

    def make_wheatdc(self):
        """
        Make the wheat dc budget table if we have budgets for wheat and dc beans
        """

    # I think each of these functions returns a list of formatted strings
    # but first caches the dollar amouns as a list of floats in the instance
    # variable with the same name.
    def crop_revenue(self, scaling='kd'):
        pass

    def avg_realized_price(self, scaling='kd'):
        pass

    def gov_pmt(self, scaling='kd'):
        pass

    def crop_ins_indems(self, scaling='kd'):
        pass

    def other_revenue(self, scaling='kd'):
        pass

    def gross_revenue(self, scaling='kd'):
        pass

    def fertilizers(self, scaling='kd'):
        pass

    def pesticides(self, scaling='kd'):
        pass

    def seed(self, scaling='kd'):
        pass

    def drying(self, scaling='kd'):
        pass

    def storage(self, scaling='kd'):
        pass

    def crop_ins_prems(self, scaling='kd'):
        pass

    def other_direct_costs(self, scaling='kd'):
        pass

    def total_direct_costs(self, scaling='kd'):
        pass

    def machine_hire_lease(self, scaling='kd'):
        pass

    def utilities(self, scaling='kd'):
        pass

    def machine_repair(self, scaling='kd'):
        pass

    def fuel_and_oil(self, scaling='kd'):
        pass

    def light_vehicle(self, scaling='kd'):
        pass

    def machine_depreciation(self, scaling='kd'):
        pass

    def total_power_costs(self, scaling='kd'):
        pass

    def hired_labor(self, scaling='kd'):
        pass

    def building_repair_rent(self, scaling='kd'):
        pass

    def building_depreciation(self, scaling='kd'):
        pass

    def insurance(self, scaling='kd'):
        pass

    def misc(self, scaling='kd'):
        pass

    def interest_nonland(self, scaling='kd'):
        pass

    def other_costs(self, scaling='kd'):
        pass

    def total_overhead_costs(self, scaling='kd'):
        pass

    def total_nonland_costs(self, scaling='kd'):
        pass

    def yield_adj_to_nonland_costs(self, scaling='kd'):
        pass

    def total_adj_nonland_costs(self, scaling='kd'):
        pass

    def operator_and_land_return(self, scaling='kd'):
        pass

    def land_costs(self, scaling='kd'):
        pass

    def revenue_based_adjustment_to_land_rent(self, scaling='kd'):
        pass

    def adjusted_land_rent(self, scaling='kd'):
        pass

    def owned_land_cost(self, is_cash_flow, scaling='kd'):
        """
        if cash flow, owned land cost includes principal payments
        """

    def total_land_cost(self, scaling='kd'):
        pass

    def total_cost(self, scaling='kd'):
        pass

    def pretax_amount(self, is_cashflow, scaling='kd'):
        pass
