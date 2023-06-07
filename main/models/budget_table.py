from .farm_year import FarmYear


class BudgetTable(object):
    """
    Generates the three or four detail budget tables, the first scaled in
    $1,000 or kilodollars (kd), the second scaled per acre (pa), the third scaled
    per bushel (pb), and if the farm has wheat/dc beans, a dc beans table in (kd)
    """

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

        # cache/apportion values for current settings
        self.farm_year.calc_gov_pmt()
        self.farm_crops = [fc for fc in
                           self.farm_year.farm_crops.all()
                           .order_by('farm_crop_type_id') if fc.has_budget()]

        for fc in self.farm_crops:
            fc.get_crop_ins_prems()

        # cached values in dollars
        self.crop_revenue = None
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
        self.bushels = [fc.sens_production_bu for fc in self.farm_crops]
        self.acres = [fc.planted_acres for fc in self.farm_crops]

    def make_thousands(self):
        """
        Make the ($000) budget table rows
        """
        return [(n, getattr(self, m)(scaling='kd')) for n, m in
                zip(self.__class__.ROW_LABELS, self.__class__.METHODS)]

    def make_peracre(self):
        """
        Make the per acre budget table rows
        """
        return [getattr(self, m)(scaling='pa') for m in self.__class__.METHODS]

    def make_perbushel(self):
        """
        Make the per bushel budget table rows
        """
        return [getattr(self, m)(scaling='pb') for m in self.__class__.METHODS]

    def make_wheatdc(self):
        """
        Make the wheat dc budget table if we have budgets for wheat and dc beans
        """

    def getitems(self, items, other, scaling, no_totcol):
        if scaling == 'kd':
            cols = [f'${val/1000:,.0f}' for val in items]
            cols.append('' if other is None else f'${other:,.0f}')
            cols.append(f'${sum(items):,.0f}' if False else '')
        elif scaling == 'pa':
            cols = [f'${val/ac:,.0f}' for val, ac in zip(self.crop_revenue, self.acres)]
        else:
            cols = [f'${val/bu:,.0f}'
                    for val, bu in zip(self.crop_revenue, self.bushels)]
        return cols

    def crop_revenue(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def avg_realized_price(self, scaling='kd'):
        if self.avg_realized_price is None:
            self.avg_realized_price = [fc.avg_realized_price()
                                       for fc in self.farm_crops]
        return self.getitems(self.avg_realized_price, None, scaling, True)

    def gov_pmt(self, scaling='kd'):
        if self.gov_pmt is None:
            self.gov_pmt = [fc.gov_pmt_portion for fc in self.farm_crops]
        return self.getitems(self.gov_pmt, None, scaling, False)

    def other_gov_pmt(self, scaling='kd'):
        if self.other_gov_pmt is None:
            self.other_gov_pmt = [fc.farm_budget_crop.other_gov_pmt
                                  for fc in self.farm_crops]
        return self.getitems(self.other_gov_pmt, None, scaling, False)

    def crop_ins_indems(self, scaling='kd'):
        if self.crop_ins_indems is None:
            self.crop_ins_indems = [fc.get_total_indemnities()
                                    for fc in self.farm_crops]
        return self.getitems(self.crop_ins_indems, None, scaling, False)

    def other_revenue(self, scaling='kd'):
        if self.other_revenue is None:
            self.other_revenue = [fc.farm_budget_crop.other_revenue
                                  for fc in self.farm_crops]
        return self.getitems(self.other_revenue, self.farm_year.other_revenue,
                             scaling, False)

    def gross_revenue(self, scaling='kd'):
        if self.gross_revenue is None:
            self.gross_revenue = [
                sum(items) for items in zip(self.crop_revenue, self.gov_pmt,
                                            self.crop_ins_indems, self.other_revenue)]
        return self.getitems(self.gross_revenue, None, scaling, False)

    def fertilizers(self, scaling='kd'):
        if self.fertilizers is None:
            self.fertilizers = [fc.farm_budget_crop.fertilizers
                                for fc in self.farm_crops]
        return self.getitems(self.fertilizers, None, scaling, False)

    def pesticides(self, scaling='kd'):
        if self.pesticides is None:
            self.pesticides = [fc.farm_budget_crop.pesticides for fc in self.farm_crops]
        return self.getitems(self.pesticides, None, scaling, False)

    def seed(self, scaling='kd'):
        if self.seed is None:
            self.seed = [fc.farm_budget_crop.seed for fc in self.farm_crops]
        return self.getitems(self.seed, None, scaling, False)

    def drying(self, scaling='kd'):
        if self.drying is None:
            self.drying = [fc.drying for fc in self.farm_crops]
        return self.getitems(self.drying, None, scaling, False)

    def storage(self, scaling='kd'):
        if self.storage is None:
            self.storage = [fc.farm_budget_crop.storage for fc in self.farm_crops]
        return self.getitems(self.storage, None, scaling, False)

    def crop_ins_prems(self, scaling='kd'):
        if self.crop_ins_prems is None:
            self.crop_ins_prems = [fc.get_total_premiums() for fc in self.farm_crops]
        return self.getitems(self.crop_ins_prems, None, scaling, False)

    def other_direct_costs(self, scaling='kd'):
        if self.other_direct_costs is None:
            self.other_direct_costs = [fc.farm_budget_crop.other_direct_costs
                                       for fc in self.farm_crops]
        return self.getitems(self.other_direct_costs, None, scaling, False)

    def total_direct_costs(self, scaling='kd'):
        if self.total_direct_costs is None:
            self.total_direct_costs = [
                sum(items) for items in zip(
                    self.fertilizers, self.pesticides, self.seed, self.drying,
                    self.storage, self.crop_ins_prems, self.other_direct_costs)]
        return self.getitems(self.total_direct_costs, None, scaling, False)

    def machine_hire_lease(self, scaling='kd'):
        if self.machine_hire_lease is None:
            self.machine_hire_lease = [fc.farm_budget_crop.machine_hire_lease
                                       for fc in self.farm_crops]
        return self.getitems(self.machine_hire_lease, None, scaling, False)

    def utilities(self, scaling='kd'):
        if self.utilities is None:
            self.utilities = [fc.farm_budget_crop.utilities
                              for fc in self.farm_crops]
        return self.getitems(self.utilities, None, scaling, False)

    def machine_repair(self, scaling='kd'):
        if self.machine_repair is None:
            self.machine_repair = [fc.farm_budget_crop.machine_repair
                                   for fc in self.farm_crops]
        return self.getitems(self.machine_repair, None, scaling, False)

    def fuel_and_oil(self, scaling='kd'):
        if self.fuel_and_oil is None:
            self.fuel_and_oil = [fc.farm_budget_crop.fuel_and_oil
                                 for fc in self.farm_crops]
        return self.getitems(self.fuel_and_oil, None, scaling, False)

    def light_vehicle(self, scaling='kd'):
        if self.light_vehicle is None:
            self.light_vehicle = [fc.farm_budget_crop.light_vehicle
                                  for fc in self.farm_crops]
        return self.getitems(self.light_vehicle, None, scaling, False)

    def machine_depreciation(self, scaling='kd'):
        if self.machine_depreciation is None:
            self.machine_depreciation = [fc.farm_budget_crop.machine_depreciation
                                         for fc in self.farm_crops]
        return self.getitems(self.machine_depreciation, None, scaling, False)

    def total_power_costs(self, scaling='kd'):
        if self.total_power_costs is None:
            self.total_power_costs = [
                sum(items) for items in zip(
                    self.machine_hire_lease, self.utilities, self.machine_repair,
                    self.fuel_and_oil, self.light_vehicle, self.machine_depreciation)]
        return self.getitems(self.total_power_costs, None, scaling, False)

    def hired_labor(self, scaling='kd'):
        if self.hired_labor is None:
            self.hired_labor = [fc.farm_budget_crop.hired_labor
                                for fc in self.farm_crops]
        return self.getitems(self.hired_labor, None, scaling, False)

    def building_repair_rent(self, scaling='kd'):
        if self.building_repair_rent is None:
            self.building_repair_rent = [fc.farm_budget_crop.building_repair_rent
                                         for fc in self.farm_crops]
        return self.getitems(self.building_repair_rent, None, scaling, False)

    def building_depreciation(self, scaling='kd'):
        if self.building_depreciation is None:
            self.building_depreciation = [fc.farm_budget_crop.building_depreciation
                                          for fc in self.farm_crops]
        return self.getitems(self.building_depreciation, None, scaling, False)

    def insurance(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def misc(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def interest_nonland(self, scaling='kd'):
        if self.interest_nonland is None:
            self.interest_nonland = [fc.farm_budget_crop.interest_nonland
                                     for fc in self.farm_crops]
        return self.getitems(self.interest_nonland, None, scaling, False)

    def other_costs(self, scaling='kd'):
        if self.other_costs is None:
            self.other_costs = [fc.farm_budget_crop.other_costs
                                for fc in self.farm_crops]
        return self.getitems(self.other_costs, self.farm_year.other_costs,
                             scaling, False)

    def total_overhead_costs(self, scaling='kd'):
        if self.total_overhead_costs is None:
            self.total_overhead_costs = [
                sum(items) for items in zip(
                    self.hired_labor, self.building_repair_rent,
                    self.building_depreciation, self.insurance, self.misc,
                    self.interest_nonland, self.other_costs)]
        return self.getitems(self.total_overhead_costs, None, scaling, False)

    def total_nonland_costs(self, scaling='kd'):
        if self.total_nonland_costs is None:
            self.total_nonland_costs = [
                sum(items) for items in zip(
                    self.total_direct_costs, self.total_power_costs,
                    self.total_overhead_costs)]
        return self.getitems(self.total_nonland_costs, None, scaling, False)

    def yield_adj_to_nonland_costs(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def total_adj_nonland_costs(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def operator_and_land_return(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def land_costs(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def revenue_based_adjustment_to_land_rent(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def adjusted_land_rent(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def owned_land_cost(self, is_cash_flow, scaling='kd'):
        """
        if cash flow, owned land cost includes principal payments
        """
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def total_land_cost(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def total_cost(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def pretax_amount(self, is_cashflow, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)
