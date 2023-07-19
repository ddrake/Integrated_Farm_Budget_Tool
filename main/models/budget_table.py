from collections import defaultdict
from .farm_year import FarmYear
from .market_crop import MarketCrop


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
        self.revenue_details = RevenueDetails(farm_year_id=farm_year_id)
        self.revenue_details.set_data()

        self.farm_crops = [fc for fc in
                           self.farm_year.farm_crops.all()
                           .order_by('farm_crop_type_id')
                           if fc.has_budget() and fc.planted_acres > 0]

        for fc in self.farm_crops:
            fc.get_crop_ins_prems()

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
            'Total Adjusted Non-Land Costs', 'Operator and Land Return',
            'Rented Land Costs', 'Revenue Based Adjustment to Land Rent',
            'Adjusted Land Rent', 'Owned Land Cost (incl. principal payments)',
            'Total Land Costs', 'Total Costs', 'PRE-TAX CASH FLOW', ]

        for fc in self.farm_crops:
            fc.get_crop_ins_prems()

        self.farmyear_gov_pmt = None
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
        self.farm_crop_types = [fc.farm_crop_type for fc in self.farm_crops]

        self.acres = [fc.planted_acres for fc in self.farm_crops]
        self.fsacres = [0 if fc.farm_crop_type.is_fac else fc.planted_acres
                        for fc in self.farm_crops]
        self.total_planted_acres = sum(self.acres)
        self.total_rented_acres = self.farm_year.total_rented_acres()
        self.total_owned_acres = self.farm_year.cropland_acres_owned
        self.total_farm_acres = self.total_rented_acres + self.total_owned_acres
        self.rented_acres = [(0 if fc.farm_crop_type.is_fac else fc.planted_acres) *
                             self.total_rented_acres / self.total_farm_acres
                             for fc in self.farm_crops]
        self.owned_acres = [(0 if fc.farm_crop_type.is_fac else fc.planted_acres) *
                            self.total_owned_acres / self.total_farm_acres
                            for fc in self.farm_crops]
        self.blank_before_rows = [1, 2, 7, 15, 22, 30, 33, 34, 37, 39, 40, 41]

    def get_info(self):
        return {'farmyear': self.farm_year.pk,
                'bh': [0, 2, 8, 17, 25, 34, 36, 37, 38, 40, 42, 43, 44, 45, 47, 49, 51],
                'bd': [2, 6, 8, 15, 17, 25, 34, 38, 40, 44, 47, 49, 51],
                'ol': [8, 17, 25, 34, 38, 44],
                }

    def get_tables(self):
        if len(self.farm_crops) == 0:
            return None
        # cache/apportion values for current settings
        self.farmyear_gov_pmt = self.farm_year.calc_gov_pmt()
        results = {'kd': self.make_thousands(),
                   'pa': self.make_peracre(),
                   'pb': self.make_perbushel(), }
        wheatdc = self.make_wheatdc()
        if wheatdc is not None:
            results['wheatdc'] = wheatdc
        return results

    def make_thousands(self):
        """
        Make the ($000) budget table rows
        """
        results = []
        header = ('PRE-TAX CASH FLOW BUDGET',
                  [str(fct).replace('Winter', 'W').replace('Spring', 'S')
                   for fct in self.farm_crop_types] +
                  'Other Total'.split())
        results.append(header)
        results += [(n, getattr(self, m)(scaling='kd')) for n, m in
                    zip(self.row_labels, self.__class__.METHODS)]
        footer = []

        label = 'Adj. Land Rent / Rented Ac.'
        coldata = [(0 if ra == 0 else alr / ra) for alr, ra in
                   zip(self.adjusted_land_rent, self.rented_acres)]
        totac = sum(self.rented_acres)
        totdata = 0 if totac == 0 else sum(self.adjusted_land_rent)/totac
        fmtdata = ['${:,.0f}'.format(cd) for cd in (coldata + [totdata])]
        fmtdata.insert(-1, '')
        footer.append((label, fmtdata))

        label = 'Owned Land Cost / Owned Ac.'
        coldata = [(0 if oa == 0 else olc / oa) for olc, oa in
                   zip(self.owned_land_cost, self.owned_acres)]
        totac = sum(self.owned_acres)
        totdata = 0 if totac == 0 else sum(self.owned_land_cost)/totac
        fmtdata = ['${:,.0f}'.format(cd) for cd in (coldata + [totdata])]
        fmtdata.insert(-1, '')
        footer.append((label, fmtdata))

        results += footer

        for b in self.blank_before_rows[-1::-1]:
            results.insert(b, ('', ['']*(len(header)-1)))
        return results

    def make_peracre(self):
        """
        Make the per acre budget table rows
        """
        results = []
        header = [str(fct).replace('Winter', 'W') for fct in self.farm_crop_types]
        results.append(header)
        results += [getattr(self, m)(scaling='pa') for m in self.__class__.METHODS]
        footer = [[''] * len(header) for i in range(2)]
        results += footer
        for b in self.blank_before_rows[-1::-1]:
            results.insert(b, ['']*len(header))
        return results

    def make_perbushel(self):
        """
        Make the per bushel budget table rows
        """
        results = []
        header = [str(fct).replace('Winter', 'W') for fct in self.farm_crop_types]
        results.append(header)
        results += [getattr(self, m)(scaling='pb') for m in self.__class__.METHODS]
        footer = [[''] * len(header) for i in range(2)]
        results += footer
        for b in self.blank_before_rows[-1::-1]:
            results.insert(b, ['']*len(header))
        return results

    def make_wheatdc(self):
        """
        Make the wheat dc budget table if we have budgets for wheat and dc beans
        """
        results = []
        fcts = [fct.pk for fct in self.farm_crop_types]
        if 5 not in fcts or 3 not in fcts:
            return None
        ixs = [fcts.index(pk) for pk in [3, 5]]
        vals = [[getattr(self, m)(scaling='raw')[i] for i in ixs]
                for m in self.__class__.METHODS]
        acres = [self.acres[i] for i in ixs]
        header = [['$(000)', '$/acre']]
        results += header
        results += [[f'${sum(pair)/1000:,.0f}',
                     f'${sum((v/a for v, a in zip(pair, acres))):,.0f}']
                    for pair in vals]
        footer = [[''] * len(header) for i in range(2)]
        results += footer
        for b in self.blank_before_rows[-1::-1]:
            results.insert(b, ['']*len(header))
        return results

    def getitems(self, items, other, scaling, no_totcol, dollarsign):
        """
        Get 'items', a cached list of numbers, peform totaling and scaling
        as specified
        """
        ds = '$' if dollarsign else ''
        if scaling == 'kd':
            cols = [ds + f'{val/1000:,.0f}' for val in items]
            cols.append('' if other is None else ds + f'{other/1000:,.0f}')
            cols.append(
                '' if no_totcol else
                ds + f'{(sum(items) + (0 if other is None else other))/1000:,.0f}')
        elif scaling == 'pa':
            cols = [ds + f'{val/ac:,.0f}' for val, ac in zip(items, self.acres)]
        elif scaling == 'pb':
            cols = [ds + f'{val/bu:,.2f}'
                    for val, bu in zip(items, self.bushels)]
        else:  # get raw numbers
            cols = items[:]
        return cols

    def get_crop_revenue(self, scaling='kd'):
        if self.crop_revenue is None:
            self.crop_revenue = [rev*1000 for rev
                                 in self.revenue_details.total_crop_revenue]
            # self.crop_revenue = [fc.grain_revenue() for fc in self.farm_crops]
        return self.getitems(self.crop_revenue, None, scaling, False, True)

    def get_gov_pmt(self, scaling='kd'):
        if self.gov_pmt is None:
            self.gov_pmt = [self.farmyear_gov_pmt * fc.planted_acres /
                            self.total_planted_acres
                            for fc in self.farm_crops]
        return self.getitems(self.gov_pmt, None, scaling, False, False)

    def gov_pmt_portion(self, pf=None, yf=None, is_per_acre=False,
                        farmyear_gov_pmt=None):
        if farmyear_gov_pmt is None:
            farmyear_gov_pmt = self.farm_year.calc_gov_pmt(pf, yf, is_per_acre=True)
        return farmyear_gov_pmt * (1 if is_per_acre else self.planted_acres)

    def get_other_gov_pmts(self, scaling='kd'):
        if self.other_gov_pmts is None:
            self.other_gov_pmts = [gp * ac for gp, ac in
                                   zip((fc.farmbudgetcrop.other_gov_pmts
                                        for fc in self.farm_crops), self.acres)]
        return self.getitems(self.other_gov_pmts, None, scaling, False, False)

    def get_crop_ins_indems(self, scaling='kd'):
        if self.crop_ins_indems is None:
            self.crop_ins_indems = [ind * ac for ind, ac in
                                    zip((fc.get_total_indemnities()
                                         for fc in self.farm_crops), self.acres)]
        return self.getitems(self.crop_ins_indems, None, scaling, False, False)

    def get_other_revenue(self, scaling='kd'):
        if self.other_revenue is None:
            self.other_revenue = [orv * ac for orv, ac in
                                  zip((fc.farmbudgetcrop.other_revenue
                                       for fc in self.farm_crops), self.acres)]
        return self.getitems(self.other_revenue,
                             self.farm_year.other_nongrain_income, scaling,
                             False, False)

    def get_gross_revenue(self, scaling='kd'):
        if self.gross_revenue is None:
            self.gross_revenue = [
                sum(items) for items in zip(self.crop_revenue, self.gov_pmt,
                                            self.crop_ins_indems, self.other_revenue)]
        return self.getitems(self.gross_revenue, self.farm_year.other_nongrain_income,
                             scaling, False, True)

    def get_fertilizers(self, scaling='kd'):
        if self.fertilizers is None:
            self.fertilizers = [f * ac for f, ac in
                                zip((fc.farmbudgetcrop.fertilizers
                                     for fc in self.farm_crops), self.acres)]
        return self.getitems(self.fertilizers, None, scaling, False, False)

    def get_pesticides(self, scaling='kd'):
        if self.pesticides is None:
            self.pesticides = [p * ac for p, ac in
                               zip((fc.farmbudgetcrop.pesticides
                                    for fc in self.farm_crops), self.acres)]
        return self.getitems(self.pesticides, None, scaling, False, False)

    def get_seed(self, scaling='kd'):
        if self.seed is None:
            self.seed = [s * ac for s, ac in
                         zip((fc.farmbudgetcrop.seed
                              for fc in self.farm_crops), self.acres)]
        return self.getitems(self.seed, None, scaling, False, False)

    def get_drying(self, scaling='kd'):
        if self.drying is None:
            self.drying = [d * ac for d, ac in
                           zip((fc.farmbudgetcrop.drying
                                for fc in self.farm_crops), self.acres)]
        return self.getitems(self.drying, None, scaling, False, False)

    def get_storage(self, scaling='kd'):
        if self.storage is None:
            self.storage = [s * ac for s, ac in
                            zip((fc.farmbudgetcrop.storage
                                 for fc in self.farm_crops), self.acres)]
        return self.getitems(self.storage, None, scaling, False, False)

    def get_crop_ins_prems(self, scaling='kd'):
        if self.crop_ins_prems is None:
            self.crop_ins_prems = [(0 if p is None else p * ac) for p, ac in
                                   zip((fc.get_total_premiums()
                                        for fc in self.farm_crops), self.acres)]
        return self.getitems(self.crop_ins_prems, None, scaling, False, False)

    def get_other_direct_costs(self, scaling='kd'):
        if self.other_direct_costs is None:
            self.other_direct_costs = [odc * ac for odc, ac in
                                       zip((fc.farmbudgetcrop.other_direct_costs
                                            for fc in self.farm_crops), self.acres)]
        return self.getitems(self.other_direct_costs, None, scaling, False, False)

    def get_total_direct_costs(self, scaling='kd'):
        if self.total_direct_costs is None:
            self.total_direct_costs = [
                sum(items) for items in zip(
                    self.fertilizers, self.pesticides, self.seed, self.drying,
                    self.storage, self.crop_ins_prems, self.other_direct_costs)]
        return self.getitems(self.total_direct_costs, None, scaling, False, True)

    def get_machine_hire_lease(self, scaling='kd'):
        if self.machine_hire_lease is None:
            self.machine_hire_lease = [mhl * ac for mhl, ac in
                                       zip((fc.farmbudgetcrop.machine_hire_lease
                                            for fc in self.farm_crops), self.acres)]
        return self.getitems(self.machine_hire_lease, None, scaling, False, False)

    def get_utilities(self, scaling='kd'):
        if self.utilities is None:
            self.utilities = [u * ac for u, ac in
                              zip((fc.farmbudgetcrop.utilities
                                   for fc in self.farm_crops), self.acres)]
        return self.getitems(self.utilities, None, scaling, False, False)

    def get_machine_repair(self, scaling='kd'):
        if self.machine_repair is None:
            self.machine_repair = [mr * ac for mr, ac in
                                   zip((fc.farmbudgetcrop.machine_repair
                                        for fc in self.farm_crops), self.acres)]
        return self.getitems(self.machine_repair, None, scaling, False, False)

    def get_fuel_and_oil(self, scaling='kd'):
        if self.fuel_and_oil is None:
            self.fuel_and_oil = [fo * ac for fo, ac in
                                 zip((fc.farmbudgetcrop.fuel_and_oil
                                      for fc in self.farm_crops), self.acres)]
        return self.getitems(self.fuel_and_oil, None, scaling, False, False)

    def get_light_vehicle(self, scaling='kd'):
        if self.light_vehicle is None:
            self.light_vehicle = [lv * ac for lv, ac in
                                  zip((fc.farmbudgetcrop.light_vehicle
                                       for fc in self.farm_crops), self.acres)]
        return self.getitems(self.light_vehicle, None, scaling, False, False)

    def get_machine_depreciation(self, scaling='kd'):
        if self.machine_depreciation is None:
            self.machine_depreciation = [md * ac for md, ac in
                                         zip((fc.farmbudgetcrop.machine_depr
                                              for fc in self.farm_crops), self.acres)]
        return self.getitems(self.machine_depreciation, None, scaling, False, False)

    def get_total_power_costs(self, scaling='kd'):
        if self.total_power_costs is None:
            self.total_power_costs = [
                sum(items) for items in zip(
                    self.machine_hire_lease, self.utilities, self.machine_repair,
                    self.fuel_and_oil, self.light_vehicle, self.machine_depreciation)]
        return self.getitems(self.total_power_costs, None, scaling, False, True)

    def get_hired_labor(self, scaling='kd'):
        if self.hired_labor is None:
            self.hired_labor = [lm * ac for lm, ac in
                                zip((fc.farmbudgetcrop.labor_and_mgmt
                                     for fc in self.farm_crops), self.acres)]
        return self.getitems(self.hired_labor, None, scaling, False, False)

    def get_building_repair_rent(self, scaling='kd'):
        if self.building_repair_rent is None:
            self.building_repair_rent = [br * ac for br, ac in
                                         zip((fc.farmbudgetcrop.building_repair_and_rent
                                              for fc in self.farm_crops), self.acres)]
        return self.getitems(self.building_repair_rent, None, scaling, False, False)

    def get_building_depreciation(self, scaling='kd'):
        if self.building_depreciation is None:
            self.building_depreciation = [bd * ac for bd, ac in
                                          zip((fc.farmbudgetcrop.building_depr
                                               for fc in self.farm_crops), self.acres)]
        return self.getitems(self.building_depreciation, None, scaling, False, False)

    def get_insurance(self, scaling='kd'):
        if self.insurance is None:
            self.insurance = [ins * ac for ins, ac in
                              zip((fc.farmbudgetcrop.insurance
                                   for fc in self.farm_crops), self.acres)]
        return self.getitems(self.insurance, None, scaling, False, False)

    def get_misc(self, scaling='kd'):
        if self.misc is None:
            self.misc = [mc * ac for mc, ac in
                         zip((fc.farmbudgetcrop.misc_overhead_costs
                              for fc in self.farm_crops), self.acres)]
        return self.getitems(self.misc, None, scaling, False, False)

    def get_interest_nonland(self, scaling='kd'):
        if self.interest_nonland is None:
            self.interest_nonland = [inl * ac for inl, ac in
                                     zip((fc.farmbudgetcrop.interest_nonland
                                          for fc in self.farm_crops), self.acres)]
        return self.getitems(self.interest_nonland, None, scaling, False, False)

    def get_other_costs(self, scaling='kd'):
        if self.other_costs is None:
            self.other_costs = [oc * ac for oc, ac in
                                zip((fc.farmbudgetcrop.other_overhead_costs
                                     for fc in self.farm_crops), self.acres)]
        return self.getitems(self.other_costs, self.farm_year.other_nongrain_expense,
                             scaling, False, False)

    def get_total_overhead_costs(self, scaling='kd'):
        if self.total_overhead_costs is None:
            self.total_overhead_costs = [
                sum(items) for items in zip(
                    self.hired_labor, self.building_repair_rent,
                    self.building_depreciation, self.insurance, self.misc,
                    self.interest_nonland, self.other_costs)]
        return self.getitems(self.total_overhead_costs,
                             self.farm_year.other_nongrain_expense, scaling,
                             False, True)

    def get_total_nonland_costs(self, scaling='kd'):
        if self.total_nonland_costs is None:
            self.total_nonland_costs = [
                sum(items) for items in zip(
                    self.total_direct_costs, self.total_power_costs,
                    self.total_overhead_costs)]
        return self.getitems(self.total_nonland_costs,
                             self.farm_year.other_nongrain_expense, scaling,
                             False, True)

    def get_yield_adj_to_nonland_costs(self, scaling='kd'):
        if self.yield_adj_to_nonland_costs is None:
            self.yield_adj_to_nonland_costs = [
                var * nlc for var, nlc in
                zip((fc.yield_adj_to_nonland_costs()
                     for fc in self.farm_crops),
                    self.total_nonland_costs)]
        return self.getitems(self.yield_adj_to_nonland_costs, None, scaling,
                             False, False)

    def get_total_adj_nonland_costs(self, scaling='kd'):
        if self.total_adj_nonland_costs is None:
            self.total_adj_nonland_costs = [
                tnc + ya for tnc, ya in
                zip(self.total_nonland_costs, self.yield_adj_to_nonland_costs)]
        return self.getitems(self.total_adj_nonland_costs,
                             self.farm_year.other_nongrain_expense, scaling,
                             False, True)

    def get_operator_and_land_return(self, scaling='kd'):
        if self.operator_and_land_return is None:
            self.operator_and_land_return = [
                gr - tnc for gr, tnc in
                zip(self.gross_revenue, self.total_adj_nonland_costs)]
        return self.getitems(self.operator_and_land_return,
                             (self.farm_year.other_nongrain_income -
                              self.farm_year.other_nongrain_expense), scaling,
                             False, True)

    def get_land_costs(self, scaling='kd'):
        if self.land_costs is None:
            self.land_costs = [ra * lc for ra, lc in
                               zip(self.rented_acres,
                                   (fc.farmbudgetcrop.rented_land_costs
                                    for fc in self.farm_crops))]
        return self.getitems(self.land_costs, None, scaling, False, False)

    def get_revenue_based_adjustment_to_land_rent(self, scaling='kd'):
        if self.revenue_based_adjustment_to_land_rent is None:
            adjs = [fc.revenue_based_adj_to_land_rent() for fc in self.farm_crops]
            self.revenue_based_adjustment_to_land_rent = [
                adj * lc for adj, lc in zip(adjs, self.land_costs)]
        return self.getitems(self.revenue_based_adjustment_to_land_rent,
                             None, scaling, False, False)

    def get_adjusted_land_rent(self, scaling='kd'):
        if self.adjusted_land_rent is None:
            self.adjusted_land_rent = [
                lc + ra for lc, ra in
                zip(self.land_costs, self.revenue_based_adjustment_to_land_rent)]
        return self.getitems(self.adjusted_land_rent, None, scaling, False, True)

    def get_owned_land_cost(self, scaling='kd'):
        land_cost = self.farm_year.total_owned_land_expense()
        farm_acres = self.total_farm_acres
        if self.owned_land_cost is None:
            self.owned_land_cost = [land_cost / farm_acres * ac
                                    for ac in self.fsacres]
        return self.getitems(self.owned_land_cost, None, scaling, False, False)

    def get_total_land_cost(self, scaling='kd'):
        if self.total_land_cost is None:
            self.total_land_cost = [rent + lc for rent, lc in
                                    zip(self.adjusted_land_rent, self.owned_land_cost)]
        return self.getitems(self.total_land_cost, None, scaling, False, True)

    def get_total_cost(self, scaling='kd'):
        if self.total_cost is None:
            self.total_cost = [nlc + lc for nlc, lc in
                               zip(self.total_adj_nonland_costs, self.total_land_cost)]
        return self.getitems(self.total_cost,
                             self.farm_year.other_nongrain_expense, scaling,
                             False, True)

    def get_pretax_amount(self, scaling='kd'):
        if self.pretax_amount is None:
            self.pretax_amount = [gr - tc for gr, tc in
                                  zip(self.gross_revenue, self.total_cost)]
        return self.getitems(self.pretax_amount,
                             (self.farm_year.other_nongrain_income -
                              self.farm_year.other_nongrain_expense), scaling,
                             False, True)


class RevenueDetails:
    """
    Generates data and a nested list structure (table rows) for a Grain Revenue
    buildup table to be placed above the Detailed Budget
    """
    def __init__(self, farm_year_id):
        self.farm_year = FarmYear.objects.get(pk=farm_year_id)

        self.farm_crops = [
            fc for fc in self.farm_year.farm_crops.all()
            if fc.planted_acres > 0 and fc.has_budget()]

        # Blank column before total is for alignment with budget
        self.colheads = [
            str(fc.farm_crop_type).replace('Winter', 'W').replace('Spring', 'S')
            for fc in self.farm_crops] + [''] + ['Total']

        self.farm_yields = None                     # bpa
        self.harvest_futures_prices = None          # $
        self.planted_acres = None                   # ac
        self.production_bushels = None              # (000s)
        self.contracted_futures = None              # (000s bu)
        self.uncontracted_futures = None            # (000s bu)
        self.contracted_basis_qty = None            # (000s bu)
        self.uncontracted_basis_qty = None          # (000s bu)
        self.avg_fut_contract_prices = None         # $
        self.avg_basis_contract_prices = None       # $
        self.assumed_basis_on_remaining = None      # $
        self.contracted_futures_revenue = None      # $(000)
        self.contracted_basis_revenue = None        # $(000)
        self.total_contracted_revenue = None        # $(000)
        self.uncontracted_futures_revenue = None    # $(000)
        self.uncontracted_basis_revenue = None      # $(000)
        self.total_uncontracted_revenue = None      # $(000)
        self.total_crop_revenue = None              # $(000)
        self.realized_price_per_bushel = None       # $
        self.market_crop_dict = None
        self.market_crops = None
        self.market_crop_production_dict = None
        self.market_crop_production = None
        self.market_fut_contracted_bu = None
        self.market_basis_contracted_bu = None
        self.frac_mkt_crop_production = None

        self.METHODS = """get_market_crop_dict get_market_crops
        get_market_crop_production_dict get_market_crop_production
        get_market_fut_contracted_bu get_market_basis_contracted_bu
        get_farm_yields get_harvest_futures_prices
        get_planted_acres get_production_bushels get_frac_mkt_crop_production
        get_contracted_futures get_uncontracted_futures get_contracted_basis_qty
        get_uncontracted_basis_qty get_avg_fut_contract_prices
        get_avg_basis_contract_prices get_assumed_basis_on_remaining
        get_contracted_futures_revenue
        get_contracted_basis_revenue get_total_contracted_revenue
        get_uncontracted_futures_revenue get_uncontracted_basis_revenue
        get_total_uncontracted_revenue get_total_crop_revenue
        get_realized_price_per_bushel""".split()

        # (title, datavar, total, round, $)
        self.ROWS = [
            ('Farm Yield per acre', 'farm_yields',
             False, 1, False),
            ('Planted Acres', 'planted_acres',
             True, 0, False),
            ('Production bushels (000s)', 'production_bushels',
             True, 1, False),
            ('Contracted Futures (000s bu)', 'contracted_futures',
             True, 1, False),
            ('Uncontracted (Oversold) Futures (000s bu)', 'uncontracted_futures',
             True, 1, False),
            ('Total Sensitized Production (000s)', 'production_bushels',
             True, 1, False),
            ('Contracted Basis (000s bu)', 'contracted_basis_qty',
             True, 1, False),
            ('Uncontracted (Oversold) Basis (000s bu)', 'uncontracted_basis_qty',
             True, 1, False),
            ('Total Sensitized Production (000s)', 'production_bushels',
             True, 1, False),
            ('Average Futures Contract Price', 'avg_fut_contract_prices',
             False, 2, True),
            ('Current Harvest Futures Price', 'harvest_futures_prices',
             False, 2, True),
            ('Average Basis Contract Price', 'avg_basis_contract_prices',
             False, 2, True),
            ('Assumed Basis on Remaining Basis Contracts', 'assumed_basis_on_remaining',
             False, 2, True),
            ('Futures', 'contracted_futures_revenue',
             True, 0, True),
            ('Basis', 'contracted_basis_revenue',
             True, 0, True),
            ('Total', 'total_contracted_revenue',
             True, 0, True),
            ('Futures', 'uncontracted_futures_revenue',
             True, 0, True),
            ('Basis', 'uncontracted_basis_revenue',
             True, 0, True),
            ('Total', 'total_uncontracted_revenue',
             True, 0, True),
            ('Total Crop Revenue ($000)', 'total_crop_revenue',
             True, 0, True),
            ('Realized Price per Bushel ($/bu)', 'realized_price_per_bushel',
             False, 2, True),
        ]

        self.SECTION_TITLES = [
            ('Contracted Revenue ($000)', 13),
            ('Uncontracted (Oversold) Revenue ($000)', 16),
        ]

        self.BLANK_ROWS = [0, 3, 6, 9, 11, 13, 17, 21]

    def get_rows(self):
        """
        Main Method (returns table rows as nested list of strings)
        """
        ncrp = len(self.farm_crops)
        blank = ('', [''] * (ncrp + 2))
        titles = [((title, [''] * (ncrp + 2)), insrow)
                  for title, insrow in self.SECTION_TITLES]
        self.set_data()
        rows = []
        for title, data, tot, rd, ds in self.ROWS:
            fmt = '{:,.' + str(rd) + 'f}'
            dss = '$' if ds else ''
            nums = []
            nums[:] = getattr(self, data)
            row = [dss + fmt.format(num) for num in nums]
            row.append('')  # spacer to align with budget
            row.append((dss + fmt.format(sum(nums))) if tot else '')
            rows.append((title, row))
        for t, ir in titles[-1::-1]:
            rows.insert(ir, t)
        for ix in self.BLANK_ROWS[-1::-1]:
            rows.insert(ix, blank)
        header = [('', self.colheads)]
        return header + rows

    def get_formats(self):
        """
        Bold headers and bold data columns
        """
        return {'bh': [20, 25, 30, 31],
                'bd': [0, 14, 15, 30, 31],
                'ol': [8, 12, 23, 28],
                'ul': [0],
                'blank': len(self.farm_crops), }

    def set_data(self):
        self.data = [(m, getattr(self, m)()) for m in self.METHODS]

    # TODO: I think most of this can be eliminated now that apportioning by
    # production fraction is being done correctly in farm_crop / market_crop
    def get_market_crop_dict(self):
        if self.market_crop_dict is None:
            self.market_crop_dict = defaultdict(list)
            for fc in self.farm_crops:
                self.market_crop_dict[fc.market_crop_id].append(fc)
        return self.market_crop_dict

    def get_market_crops(self):
        if self.market_crops is None:
            self.market_crops = [MarketCrop.objects.get(pk=pk)
                                 for pk in self.market_crop_dict.keys()]
        return self.market_crops

    def get_market_crop_production_dict(self):
        if self.market_crop_production_dict is None:
            self.market_crop_production_dict = {
                mcid: sum((fc.planted_acres * fc.sens_farm_expected_yield() / 1000
                          for fc in fcs))
                for mcid, fcs in self.market_crop_dict.items()}
        return self.market_crop_production_dict

    def get_market_crop_production(self):
        if self.market_crop_production is None:
            self.market_crop_production = [
                self.market_crop_production_dict[fc.market_crop_id]
                for fc in self.farm_crops]
        return self.market_crop_production

    def get_market_fut_contracted_bu(self):
        if self.market_fut_contracted_bu is None:
            self.market_fut_contracted_bu = [
                fc.market_crop.contracted_bu / 1000 for fc in self.farm_crops]
        return self.market_fut_contracted_bu

    def get_market_basis_contracted_bu(self):
        if self.market_basis_contracted_bu is None:
            self.market_basis_contracted_bu = [
                fc.market_crop.basis_bu_locked / 1000 for fc in self.farm_crops]
        return self.market_basis_contracted_bu

    def get_farm_yields(self):
        if self.farm_yields is None:
            self.farm_yields = [fc.sens_farm_expected_yield()
                                for fc in self.farm_crops]
        return self.farm_yields

    def get_harvest_futures_prices(self):
        if self.harvest_futures_prices is None:
            self.harvest_futures_prices = [fc.sens_harvest_price()
                                           for fc in self.farm_crops]
        return self.harvest_futures_prices

    def get_planted_acres(self):
        if self.planted_acres is None:
            self.planted_acres = [fc.planted_acres for fc in self.farm_crops]
        return self.planted_acres

    def get_production_bushels(self):
        if self.production_bushels is None:
            self.production_bushels = [ac * yld / 1000 for (ac, yld) in
                                       zip(self.planted_acres, self.farm_yields)]
        return self.production_bushels

    def get_frac_mkt_crop_production(self):
        if self.frac_mkt_crop_production is None:
            self.frac_mkt_crop_production = [
                pb / mpb for pb, mpb
                in zip(self.production_bushels, self.market_crop_production)]
        return self.frac_mkt_crop_production

    def get_contracted_futures(self):
        if self.contracted_futures is None:
            self.contracted_futures = [
                mcf * frac for mcf, frac
                in zip(self.market_fut_contracted_bu, self.frac_mkt_crop_production)]
        return self.contracted_futures

    def get_uncontracted_futures(self):
        if self.uncontracted_futures is None:
            self.uncontracted_futures = [pb - cf for pb, cf in
                                         zip(self.production_bushels,
                                             self.contracted_futures)]
        return self.uncontracted_futures

    def get_contracted_basis_qty(self):
        if self.contracted_basis_qty is None:
            self.contracted_basis_qty = [
                mcb * frac for mcb, frac
                in zip(self.market_basis_contracted_bu, self.frac_mkt_crop_production)]
        return self.contracted_basis_qty

    def get_uncontracted_basis_qty(self):
        if self.uncontracted_basis_qty is None:
            self.uncontracted_basis_qty = [pb - cb for pb, cb in
                                           zip(self.production_bushels,
                                               self.contracted_basis_qty)]
        return self.uncontracted_basis_qty

    def get_avg_fut_contract_prices(self):
        if self.avg_fut_contract_prices is None:
            self.avg_fut_contract_prices = [fc.avg_contract_price()
                                            for fc in self.farm_crops]
        return self.avg_fut_contract_prices

    def get_avg_basis_contract_prices(self):
        if self.avg_basis_contract_prices is None:
            self.avg_basis_contract_prices = [fc.avg_locked_basis()
                                              for fc in self.farm_crops]
        return self.avg_basis_contract_prices

    def get_assumed_basis_on_remaining(self):
        if self.assumed_basis_on_remaining is None:
            self.assumed_basis_on_remaining = [fc.assumed_basis_for_new()
                                               for fc in self.farm_crops]
        return self.assumed_basis_on_remaining

    def get_contracted_futures_revenue(self):
        if self.contracted_futures_revenue is None:
            self.contracted_futures_revenue = [fb * fp for fb, fp in
                                               zip(self.contracted_futures,
                                                   self.avg_fut_contract_prices)]
        return self.contracted_futures_revenue

    def get_contracted_basis_revenue(self):
        if self.contracted_basis_revenue is None:
            self.contracted_basis_revenue = [bb * bp for bb, bp in
                                             zip(self.contracted_basis_qty,
                                                 self.avg_basis_contract_prices)]
        return self.contracted_basis_revenue

    def get_total_contracted_revenue(self):
        if self.total_contracted_revenue is None:
            self.total_contracted_revenue = [fr + br for fr, br in
                                             zip(self.contracted_futures_revenue,
                                                 self.contracted_basis_revenue)]
        return self.total_contracted_revenue

    def get_uncontracted_futures_revenue(self):
        if self.uncontracted_futures_revenue is None:
            self.uncontracted_futures_revenue = [p * uf for p, uf in
                                                 zip(self.harvest_futures_prices,
                                                     self.uncontracted_futures)]
        return self.uncontracted_futures_revenue

    def get_uncontracted_basis_revenue(self):
        if self.uncontracted_basis_revenue is None:
            self.uncontracted_basis_revenue = [ab * ub for ab, ub in
                                               zip(self.assumed_basis_on_remaining,
                                                   self.uncontracted_basis_qty)]
        return self.uncontracted_basis_revenue

    def get_total_uncontracted_revenue(self):
        if self.total_uncontracted_revenue is None:
            self.total_uncontracted_revenue = [uf + ub for uf, ub in
                                               zip(self.uncontracted_futures_revenue,
                                                   self.uncontracted_basis_revenue)]
        return self.total_uncontracted_revenue

    def get_total_crop_revenue(self):
        if self.total_crop_revenue is None:
            self.total_crop_revenue = [cr + ur for cr, ur in
                                       zip(self.total_contracted_revenue,
                                           self.total_uncontracted_revenue)]
        return self.total_crop_revenue

    def get_realized_price_per_bushel(self):
        if self.realized_price_per_bushel is None:
            self.realized_price_per_bushel = [tcr / pb for tcr, pb in
                                              zip(self.total_crop_revenue,
                                                  self.production_bushels)]
        return self.realized_price_per_bushel
