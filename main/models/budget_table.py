from .farm_year import FarmYear


class BudgetTable(object):
    """
    Generates the three or four detail budget tables, the first scaled in
    $1,000 or kilodollars (kd), the second scaled per acre (pa), the third scaled
    per bushel (pb), and if the farm has wheat/dc beans, a dc beans table in (kd)
    """

    ROW_LABELS = [
        'Crop Revenue', 'ARC/PLC',
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
        get_crop_revenue get_gov_pmt get_other_gov_pmts get_crop_ins_indems
        get_other_revenue get_gross_revenue get_fertilizers get_pesticides get_seed
        get_drying get_storage get_crop_ins_prems get_other_direct_costs
        get_total_direct_costs get_machine_hire_lease get_utilities get_machine_repair
        get_fuel_and_oil get_light_vehicle get_machine_depreciation
        get_total_power_costs get_hired_labor get_building_repair_rent
        get_building_depreciation get_insurance get_misc get_interest_nonland
        get_other_costs get_total_overhead_costs get_total_nonland_costs
        get_yield_adj_to_nonland_costs get_total_adj_nonland_costs
        get_operator_and_land_return get_land_costs
        get_revenue_based_adjustment_to_land_rent
        get_adjusted_land_rent get_owned_land_cost
        get_total_land_cost get_total_cost get_pretax_amount""".split()

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
        self.other_gov_pmts = None
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
        self.bushels = [fc.sens_production_bu() for fc in self.farm_crops]
        self.acres = [fc.planted_acres for fc in self.farm_crops]

    def make_thousands(self):
        """
        Make the ($000) budget table rows
        """
        results = []
        for n, m in zip(self.__class__.ROW_LABELS, self.__class__.METHODS):
            print(n, m)
            results.append((n, getattr(self, m)(scaling='kd')))
        # return [(n, getattr(self, m)(scaling='kd')) for n, m in
        #         zip(self.__class__.ROW_LABELS, self.__class__.METHODS)]

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
        elif scaling == 'pb':
            cols = [f'${val/bu:,.0f}'
                    for val, bu in zip(self.crop_revenue, self.bushels)]
        else:  # no scaling
            cols = [f'${val:,.0f}' for val in items]
        return cols

    def get_crop_revenue(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.grain_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    # not sure we need this -- same as crop revenue scaled pb
    # def get_avg_realized_price(self, scaling='kd'):
    #     if self.avg_realized_price is None:
    #         self.avg_realized_price = [fc.avg_realized_price()
    #                                    for fc in self.farm_crops]
    #     return self.getitems(self.avg_realized_price, None, None, True)

    def get_gov_pmt(self, scaling='kd'):
        if self.gov_pmt is None:
            self.gov_pmt = [fc.gov_pmt_portion for fc in self.farm_crops]
        return self.getitems(self.gov_pmt, None, scaling, False)

    def get_other_gov_pmts(self, scaling='kd'):
        if self.other_gov_pmts is None:
            self.other_gov_pmts = [fc.farmbudgetcrop.other_gov_pmts
                                   for fc in self.farm_crops]
        return self.getitems(self.other_gov_pmts, None, scaling, False)

    def get_crop_ins_indems(self, scaling='kd'):
        if self.crop_ins_indems is None:
            self.crop_ins_indems = [fc.get_total_indemnities()
                                    for fc in self.farm_crops]
        return self.getitems(self.crop_ins_indems, None, scaling, False)

    def get_other_revenue(self, scaling='kd'):
        if self.other_revenue is None:
            self.other_revenue = [fc.farmbudgetcrop.other_revenue
                                  for fc in self.farm_crops]
        return self.getitems(self.other_revenue, self.farm_year.other_nongrain_income,
                             scaling, False)

    def get_gross_revenue(self, scaling='kd'):
        if self.gross_revenue is None:
            self.gross_revenue = [
                sum(items) for items in zip(self.crop_revenue, self.gov_pmt,
                                            self.crop_ins_indems, self.other_revenue)]
        return self.getitems(self.gross_revenue, None, scaling, False)

    def get_fertilizers(self, scaling='kd'):
        if self.fertilizers is None:
            self.fertilizers = [fc.farmbudgetcrop.fertilizers
                                for fc in self.farm_crops]
        return self.getitems(self.fertilizers, None, scaling, False)

    def get_pesticides(self, scaling='kd'):
        if self.pesticides is None:
            self.pesticides = [fc.farmbudgetcrop.pesticides for fc in self.farm_crops]
        return self.getitems(self.pesticides, None, scaling, False)

    def get_seed(self, scaling='kd'):
        if self.seed is None:
            self.seed = [fc.farmbudgetcrop.seed for fc in self.farm_crops]
        return self.getitems(self.seed, None, scaling, False)

    def get_drying(self, scaling='kd'):
        if self.drying is None:
            self.drying = [fc.farmbudgetcrop.drying for fc in self.farm_crops]
        return self.getitems(self.drying, None, scaling, False)

    def get_storage(self, scaling='kd'):
        if self.storage is None:
            self.storage = [fc.farmbudgetcrop.storage for fc in self.farm_crops]
        return self.getitems(self.storage, None, scaling, False)

    def get_crop_ins_prems(self, scaling='kd'):
        if self.crop_ins_prems is None:
            self.crop_ins_prems = [fc.get_total_premiums() for fc in self.farm_crops]
        return self.getitems(self.crop_ins_prems, None, scaling, False)

    def get_other_direct_costs(self, scaling='kd'):
        if self.other_direct_costs is None:
            self.other_direct_costs = [fc.farmbudgetcrop.other_direct_costs
                                       for fc in self.farm_crops]
        return self.getitems(self.other_direct_costs, None, scaling, False)

    def get_total_direct_costs(self, scaling='kd'):
        if self.total_direct_costs is None:
            self.total_direct_costs = [
                sum(items) for items in zip(
                    self.fertilizers, self.pesticides, self.seed, self.drying,
                    self.storage, self.crop_ins_prems, self.other_direct_costs)]
        return self.getitems(self.total_direct_costs, None, scaling, False)

    def get_machine_hire_lease(self, scaling='kd'):
        if self.machine_hire_lease is None:
            self.machine_hire_lease = [fc.farmbudgetcrop.machine_hire_lease
                                       for fc in self.farm_crops]
        return self.getitems(self.machine_hire_lease, None, scaling, False)

    def get_utilities(self, scaling='kd'):
        if self.utilities is None:
            self.utilities = [fc.farmbudgetcrop.utilities
                              for fc in self.farm_crops]
        return self.getitems(self.utilities, None, scaling, False)

    def get_machine_repair(self, scaling='kd'):
        if self.machine_repair is None:
            self.machine_repair = [fc.farmbudgetcrop.machine_repair
                                   for fc in self.farm_crops]
        return self.getitems(self.machine_repair, None, scaling, False)

    def get_fuel_and_oil(self, scaling='kd'):
        if self.fuel_and_oil is None:
            self.fuel_and_oil = [fc.farmbudgetcrop.fuel_and_oil
                                 for fc in self.farm_crops]
        return self.getitems(self.fuel_and_oil, None, scaling, False)

    def get_light_vehicle(self, scaling='kd'):
        if self.light_vehicle is None:
            self.light_vehicle = [fc.farmbudgetcrop.light_vehicle
                                  for fc in self.farm_crops]
        return self.getitems(self.light_vehicle, None, scaling, False)

    def get_machine_depreciation(self, scaling='kd'):
        if self.machine_depreciation is None:
            self.machine_depreciation = [fc.farmbudgetcrop.machine_depr
                                         for fc in self.farm_crops]
        return self.getitems(self.machine_depreciation, None, scaling, False)

    def get_total_power_costs(self, scaling='kd'):
        if self.total_power_costs is None:
            self.total_power_costs = [
                sum(items) for items in zip(
                    self.machine_hire_lease, self.utilities, self.machine_repair,
                    self.fuel_and_oil, self.light_vehicle, self.machine_depreciation)]
        return self.getitems(self.total_power_costs, None, scaling, False)

    def get_hired_labor(self, scaling='kd'):
        if self.hired_labor is None:
            self.hired_labor = [fc.farmbudgetcrop.labor_and_mgmt
                                for fc in self.farm_crops]
        return self.getitems(self.hired_labor, None, scaling, False)

    def get_building_repair_rent(self, scaling='kd'):
        if self.building_repair_rent is None:
            self.building_repair_rent = [fc.farmbudgetcrop.building_repair_and_rent
                                         for fc in self.farm_crops]
        return self.getitems(self.building_repair_rent, None, scaling, False)

    def get_building_depreciation(self, scaling='kd'):
        if self.building_depreciation is None:
            self.building_depreciation = [fc.farmbudgetcrop.building_depr
                                          for fc in self.farm_crops]
        return self.getitems(self.building_depreciation, None, scaling, False)

    def get_insurance(self, scaling='kd'):
        if self.insurance is None:
            self.insurance = [fc.farmbudgetcrop.insurance for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def get_misc(self, scaling='kd'):
        if self.misc is None:
            self.misc = [fc.farmbudgetcrop.crop_revenue for fc in self.farm_crops]
        return self.getitems(self.misc, None, scaling, False)

    def get_interest_nonland(self, scaling='kd'):
        if self.interest_nonland is None:
            self.interest_nonland = [fc.farmbudgetcrop.interest_nonland
                                     for fc in self.farm_crops]
        return self.getitems(self.interest_nonland, None, scaling, False)

    def get_other_costs(self, scaling='kd'):
        if self.other_costs is None:
            self.other_costs = [fc.farmbudgetcrop.other_overhead_costs
                                for fc in self.farm_crops]
        return self.getitems(self.other_costs, self.farm_year.other_nongrain_expense,
                             scaling, False)

    def get_total_overhead_costs(self, scaling='kd'):
        if self.total_overhead_costs is None:
            self.total_overhead_costs = [
                sum(items) for items in zip(
                    self.hired_labor, self.building_repair_rent,
                    self.building_depreciation, self.insurance, self.misc,
                    self.interest_nonland, self.other_costs)]
        return self.getitems(self.total_overhead_costs, None, scaling, False)

    def get_total_nonland_costs(self, scaling='kd'):
        if self.total_nonland_costs is None:
            self.total_nonland_costs = [
                sum(items) for items in zip(
                    self.total_direct_costs, self.total_power_costs,
                    self.total_overhead_costs)]
        return self.getitems(self.total_nonland_costs, None, scaling, False)

    def get_yield_adj_to_nonland_costs(self, scaling='kd'):
        if self.yield_adj_to_nonland_costs is None:
            self.yield_adj_to_nonland_costs = [
                var * nlc * (1 - self.crop_year.yield_factor) for var, nlc in
                zip((fc.farmbudgetcrop.yield_variability for fc in self.farm_crops),
                    self.total_nonland_costs)]
        return self.getitems(self.yield_adj_to_nonland_costs, None, scaling, False)

    def get_total_adj_nonland_costs(self, scaling='kd'):
        if self.total_adj_nonland_costs is None:
            self.total_adj_nonland_costs = [
                tnc + ya for tnc, ya in
                zip(self.total_nonland_costs, self.yield_adj_to_nonland_costs)]
        return self.getitems(self.total_adj_nonland_costs, None, scaling, False)

    def get_operator_and_land_return(self, scaling='kd'):
        if self.operator_and_land_return is None:
            self.operator_and_land_return = [
                gr - tnc for gr, tnc in
                zip(self.gross_revenue, self.total_adj_nonland_costs)]
        return self.getitems(self.operator_and_land_return, None, scaling, False)

    def get_land_costs(self, scaling='kd'):
        if self.land_costs is None:
            self.land_costs = [fc.farmbudgetcrop.land_costs for fc in self.farm_crops]
        return self.getitems(self.land_costs, None, scaling, False)

    def get_revenue_based_adjustment_to_land_rent(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def get_adjusted_land_rent(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def get_owned_land_cost(self, is_cash_flow, scaling='kd'):
        """
        if cash flow, owned land cost includes principal payments
        """
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def get_total_land_cost(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def get_total_cost(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def get_pretax_amount(self, is_cashflow, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.crop_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)
