import math

from .farm_year import FarmYear


class BudgetTable(object):
    """
    Generates the three or four detail budget tables, the first scaled in
    $1,000 or kilodollars (kd), the second scaled per acre (pa), the third scaled
    per bushel (pb), and if the farm has wheat/dc beans, a dc beans table in (kd)
    """

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
                           .order_by('farm_crop_type_id')
                           if fc.has_budget() and fc.planted_acres > 0]

        for fc in self.farm_crops:
            fc.get_crop_ins_prems()

        self.is_cash_flow = (self.farm_year.report_type == 1)

        inclexcl = "incl." if self.is_cash_flow else "excl."
        self.row_labels = [
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
            f'Owned Land Cost ({inclexcl} principal payments)',
            'Total Land Costs', 'Total Costs',
            f'PRE-TAX {"CASH FLOW" if self.is_cash_flow else "INCOME"}', ]

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
        self.farm_crop_types = [fc.farm_crop_type for fc in self.farm_crops]

    def get_tables(self):
        if len(self.farm_crops) == 0:
            return None
        results = {'kd': self.make_thousands(),
                   'kdbold': [0, 1, 6, 14, 21, 29, 32, 33, 36, 38, 39, 40],
                   'pa': self.make_peracre(),
                   'pabold': [0, 1, 6, 14, 21, 29, 32, 33, 36, 38, 39, 40],
                   'pb': self.make_perbushel(),
                   'pbbold': [0, 1, 6, 14, 21, 29, 32, 33, 36, 38, 39, 40], }
        wheatdc = self.make_wheatdc()
        if wheatdc is not None:
            results['wheatdc'] = wheatdc
            results['wheatdcbold'] = [0, 1, 6, 14, 21, 29, 32, 33, 36, 38, 39, 40]
        return results

    def make_thousands(self):
        """
        Make the ($000) budget table rows
        """
        results = [(f'PRE-TAX {"CASH FLOW" if self.is_cash_flow else "INCOME"} BUDGET',
                   [str(fct).replace('Winter', 'W').replace('Spring', 'S')
                    for fct in self.farm_crop_types] +
                   'Other Total'.split())]
        return results + [(n, getattr(self, m)(scaling='kd')) for n, m in
                          zip(self.row_labels, self.__class__.METHODS)]

    def make_peracre(self):
        """
        Make the per acre budget table rows
        """
        results = [[str(fct).replace('Winter', 'W') for fct in self.farm_crop_types]]
        return results + [getattr(self, m)(scaling='pa')
                          for m in self.__class__.METHODS]

    def make_perbushel(self):
        """
        Make the per bushel budget table rows
        """
        results = [[str(fct).replace('Winter', 'W') for fct in self.farm_crop_types]]
        return results + [getattr(self, m)(scaling='pb')
                          for m in self.__class__.METHODS]

    def make_wheatdc(self):
        """
        Make the wheat dc budget table if we have budgets for wheat and dc beans
        """
        fcts = [fct.pk for fct in self.farm_crop_types]
        if 5 not in fcts or 3 not in fcts:
            return None
        ixs = [fcts.index(pk) for pk in [3, 5]]
        vals = [[getattr(self, m)(scaling='raw')[i] for i in ixs]
                for m in self.__class__.METHODS]
        acres = [self.acres[i] for i in ixs]
        results = [['$(000)', '$/acre']]
        return (results +
                [[f'${sum(pair)/1000:,.0f}',
                  f'${sum((v/a for v, a in zip(pair, acres))):,.0f}'] for pair in vals])

    def getitems(self, items, other, scaling, no_totcol):
        """
        Get 'items', a cached list of numbers, peform totaling and scaling
        as specified
        """
        if scaling == 'kd':
            cols = [f'${val/1000:,.0f}' for val in items]
            cols.append('' if other is None else f'${other/1000:,.0f}')
            cols.append('' if no_totcol else
                        f'${(sum(items) + (0 if other is None else other))/1000:,.0f}')
        elif scaling == 'pa':
            cols = [f'${val/ac:,.0f}' for val, ac in zip(items, self.acres)]
        elif scaling == 'pb':
            cols = [f'${val/bu:,.2f}'
                    for val, bu in zip(items, self.bushels)]
        else:  # get raw numbers
            cols = items[:]
        return cols

    def get_crop_revenue(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [fc.grain_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False)

    def get_gov_pmt(self, scaling='kd'):
        if self.gov_pmt is None:
            self.gov_pmt = [fc.gov_pmt_portion() for fc in self.farm_crops]
        return self.getitems(self.gov_pmt, None, scaling, False)

    def get_other_gov_pmts(self, scaling='kd'):
        if self.other_gov_pmts is None:
            self.other_gov_pmts = [gp * ac for gp, ac in
                                   zip((fc.farmbudgetcrop.other_gov_pmts
                                        for fc in self.farm_crops), self.acres)]
        return self.getitems(self.other_gov_pmts, None, scaling, False)

    def get_crop_ins_indems(self, scaling='kd'):
        if self.crop_ins_indems is None:
            self.crop_ins_indems = [ind * ac for ind, ac in
                                    zip((fc.get_total_indemnities()
                                         for fc in self.farm_crops), self.acres)]
        return self.getitems(self.crop_ins_indems, None, scaling, False)

    def get_other_revenue(self, scaling='kd'):
        if self.other_revenue is None:
            self.other_revenue = [orv * ac for orv, ac in
                                  zip((fc.farmbudgetcrop.other_revenue
                                       for fc in self.farm_crops), self.acres)]
        return self.getitems(self.other_revenue,
                             self.farm_year.other_nongrain_income, scaling, False)

    def get_gross_revenue(self, scaling='kd'):
        if self.gross_revenue is None:
            self.gross_revenue = [
                sum(items) for items in zip(self.crop_revenue, self.gov_pmt,
                                            self.crop_ins_indems, self.other_revenue)]
        return self.getitems(self.gross_revenue, self.farm_year.other_nongrain_income,
                             scaling, False)

    def get_fertilizers(self, scaling='kd'):
        if self.fertilizers is None:
            self.fertilizers = [f * ac for f, ac in
                                zip((fc.farmbudgetcrop.fertilizers
                                     for fc in self.farm_crops), self.acres)]
        return self.getitems(self.fertilizers, None, scaling, False)

    def get_pesticides(self, scaling='kd'):
        if self.pesticides is None:
            self.pesticides = [p * ac for p, ac in
                               zip((fc.farmbudgetcrop.pesticides
                                    for fc in self.farm_crops), self.acres)]
        return self.getitems(self.pesticides, None, scaling, False)

    def get_seed(self, scaling='kd'):
        if self.seed is None:
            self.seed = [s * ac for s, ac in
                         zip((fc.farmbudgetcrop.seed
                              for fc in self.farm_crops), self.acres)]
        return self.getitems(self.seed, None, scaling, False)

    def get_drying(self, scaling='kd'):
        if self.drying is None:
            self.drying = [d * ac for d, ac in
                           zip((fc.farmbudgetcrop.drying
                                for fc in self.farm_crops), self.acres)]
        return self.getitems(self.drying, None, scaling, False)

    def get_storage(self, scaling='kd'):
        if self.storage is None:
            self.storage = [s * ac for s, ac in
                            zip((fc.farmbudgetcrop.storage
                                 for fc in self.farm_crops), self.acres)]
        return self.getitems(self.storage, None, scaling, False)

    def get_crop_ins_prems(self, scaling='kd'):
        if self.crop_ins_prems is None:
            self.crop_ins_prems = [(0 if p is None else p * ac) for p, ac in
                                   zip((fc.get_total_premiums()
                                        for fc in self.farm_crops), self.acres)]
        return self.getitems(self.crop_ins_prems, None, scaling, False)

    def get_other_direct_costs(self, scaling='kd'):
        if self.other_direct_costs is None:
            self.other_direct_costs = [odc * ac for odc, ac in
                                       zip((fc.farmbudgetcrop.other_direct_costs
                                            for fc in self.farm_crops), self.acres)]
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
            self.machine_hire_lease = [mhl * ac for mhl, ac in
                                       zip((fc.farmbudgetcrop.machine_hire_lease
                                            for fc in self.farm_crops), self.acres)]
        return self.getitems(self.machine_hire_lease, None, scaling, False)

    def get_utilities(self, scaling='kd'):
        if self.utilities is None:
            self.utilities = [u * ac for u, ac in
                              zip((fc.farmbudgetcrop.utilities
                                   for fc in self.farm_crops), self.acres)]
        return self.getitems(self.utilities, None, scaling, False)

    def get_machine_repair(self, scaling='kd'):
        if self.machine_repair is None:
            self.machine_repair = [mr * ac for mr, ac in
                                   zip((fc.farmbudgetcrop.machine_repair
                                        for fc in self.farm_crops), self.acres)]
        return self.getitems(self.machine_repair, None, scaling, False)

    def get_fuel_and_oil(self, scaling='kd'):
        if self.fuel_and_oil is None:
            self.fuel_and_oil = [fo * ac for fo, ac in
                                 zip((fc.farmbudgetcrop.fuel_and_oil
                                      for fc in self.farm_crops), self.acres)]
        return self.getitems(self.fuel_and_oil, None, scaling, False)

    def get_light_vehicle(self, scaling='kd'):
        if self.light_vehicle is None:
            self.light_vehicle = [lv * ac for lv, ac in
                                  zip((fc.farmbudgetcrop.light_vehicle
                                       for fc in self.farm_crops), self.acres)]
        return self.getitems(self.light_vehicle, None, scaling, False)

    def get_machine_depreciation(self, scaling='kd'):
        if self.machine_depreciation is None:
            self.machine_depreciation = [md * ac for md, ac in
                                         zip((fc.farmbudgetcrop.machine_depr
                                              for fc in self.farm_crops), self.acres)]
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
            self.hired_labor = [lm * ac for lm, ac in
                                zip((fc.farmbudgetcrop.labor_and_mgmt
                                     for fc in self.farm_crops), self.acres)]
        return self.getitems(self.hired_labor, None, scaling, False)

    def get_building_repair_rent(self, scaling='kd'):
        if self.building_repair_rent is None:
            self.building_repair_rent = [br * ac for br, ac in
                                         zip((fc.farmbudgetcrop.building_repair_and_rent
                                              for fc in self.farm_crops), self.acres)]
        return self.getitems(self.building_repair_rent, None, scaling, False)

    def get_building_depreciation(self, scaling='kd'):
        if self.building_depreciation is None:
            self.building_depreciation = [bd * ac for bd, ac in
                                          zip((fc.farmbudgetcrop.building_depr
                                               for fc in self.farm_crops), self.acres)]
        return self.getitems(self.building_depreciation, None, scaling, False)

    def get_insurance(self, scaling='kd'):
        if self.insurance is None:
            self.insurance = [ins * ac for ins, ac in
                              zip((fc.farmbudgetcrop.insurance
                                   for fc in self.farm_crops), self.acres)]
        return self.getitems(self.insurance, None, scaling, False)

    def get_misc(self, scaling='kd'):
        if self.misc is None:
            self.misc = [mc * ac for mc, ac in
                         zip((fc.farmbudgetcrop.misc_overhead_costs
                              for fc in self.farm_crops), self.acres)]
        return self.getitems(self.misc, None, scaling, False)

    def get_interest_nonland(self, scaling='kd'):
        if self.interest_nonland is None:
            self.interest_nonland = [inl * ac for inl, ac in
                                     zip((fc.farmbudgetcrop.interest_nonland
                                          for fc in self.farm_crops), self.acres)]
        return self.getitems(self.interest_nonland, None, scaling, False)

    def get_other_costs(self, scaling='kd'):
        if self.other_costs is None:
            self.other_costs = [oc * ac for oc, ac in
                                zip((fc.farmbudgetcrop.other_overhead_costs
                                     for fc in self.farm_crops), self.acres)]
        return self.getitems(self.other_costs, self.farm_year.other_nongrain_expense,
                             scaling, False)

    def get_total_overhead_costs(self, scaling='kd'):
        if self.total_overhead_costs is None:
            self.total_overhead_costs = [
                sum(items) for items in zip(
                    self.hired_labor, self.building_repair_rent,
                    self.building_depreciation, self.insurance, self.misc,
                    self.interest_nonland, self.other_costs)]
        return self.getitems(self.total_overhead_costs,
                             self.farm_year.other_nongrain_expense, scaling, False)

    def get_total_nonland_costs(self, scaling='kd'):
        if self.total_nonland_costs is None:
            self.total_nonland_costs = [
                sum(items) for items in zip(
                    self.total_direct_costs, self.total_power_costs,
                    self.total_overhead_costs)]
        return self.getitems(self.total_nonland_costs,
                             self.farm_year.other_nongrain_expense, scaling, False)

    def get_yield_adj_to_nonland_costs(self, scaling='kd'):
        if self.yield_adj_to_nonland_costs is None:
            self.yield_adj_to_nonland_costs = [
                var * nlc for var, nlc in
                zip((fc.farmbudgetcrop.yield_variability * (fc.yield_factor - 1)
                     for fc in self.farm_crops),
                    self.total_nonland_costs)]
        return self.getitems(self.yield_adj_to_nonland_costs, None, scaling, False)

    def get_total_adj_nonland_costs(self, scaling='kd'):
        if self.total_adj_nonland_costs is None:
            self.total_adj_nonland_costs = [
                tnc + ya for tnc, ya in
                zip(self.total_nonland_costs, self.yield_adj_to_nonland_costs)]
        return self.getitems(self.total_adj_nonland_costs,
                             self.farm_year.other_nongrain_expense, scaling, False)

    def get_operator_and_land_return(self, scaling='kd'):
        if self.operator_and_land_return is None:
            self.operator_and_land_return = [
                gr - tnc for gr, tnc in
                zip(self.gross_revenue, self.total_adj_nonland_costs)]
        return self.getitems(self.operator_and_land_return,
                             (self.farm_year.other_nongrain_income -
                              self.farm_year.other_nongrain_expense), scaling, False)

    def get_land_costs(self, scaling='kd'):
        if self.land_costs is None:
            self.land_costs = [lc * ac for lc, ac in
                               zip((fc.farmbudgetcrop.rented_land_costs
                                    for fc in self.farm_crops), self.acres)]
        return self.getitems(self.land_costs, None, scaling, False)

    def get_revenue_based_adjustment_to_land_rent(self, scaling='kd'):
        if self.revenue_based_adjustment_to_land_rent is None:
            cf = self.farm_year.var_rent_cap_floor_frac
            fv = self.farm_year.frac_var_rent()
            self.revenue_based_adjustment_to_land_rent = [
                fv * lc * (math.copysign(cf, fre) if abs(fre) > cf else fre) for lc, fre
                in zip(self.land_costs,
                       (fc.frac_rev_excess() for fc in self.farm_crops))]
        return self.getitems(self.revenue_based_adjustment_to_land_rent,
                             None, scaling, False)

    def get_adjusted_land_rent(self, scaling='kd'):
        if self.adjusted_land_rent is None:
            self.adjusted_land_rent = [
                lc + ra for lc, ra in
                zip(self.land_costs, self.revenue_based_adjustment_to_land_rent)]
        return self.getitems(self.adjusted_land_rent, None, scaling, False)

    def get_owned_land_cost(self, scaling='kd'):
        land_cost = self.farm_year.total_owned_land_expense(
            include_principal=self.is_cash_flow)
        acres = sum(self.acres)
        if self.owned_land_cost is None:
            self.owned_land_cost = [land_cost*ac/acres for ac in self.acres]
        return self.getitems(self.owned_land_cost, None, scaling, False)

    def get_total_land_cost(self, scaling='kd'):
        if self.total_land_cost is None:
            self.total_land_cost = [rent + lc for rent, lc in
                                    zip(self.adjusted_land_rent, self.owned_land_cost)]
        return self.getitems(self.total_land_cost, None, scaling, False)

    def get_total_cost(self, scaling='kd'):
        if self.total_cost is None:
            self.total_cost = [nlc + lc for nlc, lc in
                               zip(self.total_adj_nonland_costs, self.total_land_cost)]
        return self.getitems(self.total_cost,
                             self.farm_year.other_nongrain_expense, scaling, False)

    def get_pretax_amount(self, scaling='kd'):
        if self.pretax_amount is None:
            self.pretax_amount = [gr - tc for gr, tc in
                                  zip(self.gross_revenue, self.total_cost)]
        return self.getitems(self.pretax_amount,
                             (self.farm_year.other_nongrain_income -
                              self.farm_year.other_nongrain_expense), scaling, False)
