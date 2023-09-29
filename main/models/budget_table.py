class BudgetManager(object):
    """
    1. Manages caching and retrieval of numerical data for baseline budget.
    2. Tries to compute variance if baseline is set.
    3. Constructs a text dict of dicts, with entries for current budget and
       possibly one for baseline and one for variance (if baseline is set).
       Each dict contains all text and formatting data needed
       to render a "budget" (including revenue and key data) in HTML or PDF.
    4. Manages caching and retrieval of this dict of dicts.  The caching speeds up
       PDF generation and holds on to the baseline info.
       the PDF generation for a budget is triggered by a button click on the
       detailed budget.  The idea is that a user could display the current budget,
       print it, display the variance or baseline and print that without having to
       recompute anything.
    """
    def __init__(self, farm_year):
        self.farm_year = farm_year
        self.budget_table = None
        self.key_data = None

        # data common to at least two of budget, revenue, keydata
        self.farm_crops = [fc for fc in self.farm_year.farm_crops.all()
                           if fc.has_budget() and fc.planted_acres > 0]

    def update_budget_text(self):
        """
        Modify the dict of dicts, 'cur' for current budget,
        and possibly 'var' for variance, save it and return it to the view.
        'base' for baseline remains unchanged
        """
        if self.farm_year.budget_text is None:
            self.farm_year.budget_text = {}

        cur_budget = self.build_current_budget()
        self.farm_year.budget_text['cur'] = (None if cur_budget['tables'] is None
                                             else cur_budget)

        if self.farm_year.baseline_budget_data is not None:
            var_budget = self.build_variance_budget()
            self.farm_year.budget_text['var'] = (
                None if var_budget is None or var_budget['tables'] is None else
                var_budget)
            if self.farm_year.budget_text['var'] is None:
                # baseline budget must be invalid
                self.farm_year.budget_text['base'] = None
                self.farm_year.baseline_budget_data = None
        else:
            self.farm_year.budget_text['var'] = None
            self.farm_year.budget_text['base'] = None
        self.farm_year.save()
        return self.farm_year.budget_text

    def build_current_budget(self):
        """
        Collect all text and format data needed for the current budget
        Also construct the values dict and save in farmyear.current_budget_data
        """
        cur_budget = {}
        bt = BudgetTable(self.farm_year, self)
        rd = bt.revenue_details
        kd = KeyData(self.farm_year, self)

        cur_budget['rev'] = rd.get_rows()
        cur_budget['revfmt'] = rd.get_formats()
        cur_budget['info'] = bt.get_info()
        cur_budget['tables'] = bt.get_tables()
        cur_budget['keydata'] = kd.get_tables()

        # Set current data for possible use as baseline data later
        self.farm_year.current_budget_data = {'revenue': rd.data, 'budget': bt.data}
        return cur_budget

    def build_variance_budget(self):
        """
        Compare the number of main budget tables.  If they don't match, the baseline
        is invalid and we return None.  If they do match, compute the differences of
        corresponding values and generate the text and formats
        """
        def getvar(baseline, current):
            """ Given baseline and current dicts, compute variance dict """
            variance = {}
            try:
                for k, b in baseline.items():
                    c = current[k]
                    variance[k] = [cc - bb for cc, bb in zip(c, b)]
                return variance
            except KeyError:
                return None

        # compare text headers to ensure that the crops match
        bt = self.farm_year.budget_text
        try:
            cur_headers = bt['cur']['tables']['pa'][0]
            cur_headers = set(zip(*cur_headers))
            base_headers = bt['base']['tables']['pa'][0]
            base_headers = set(zip(*base_headers))
            if (cur_headers != base_headers):
                return None
        except Exception:
            return None

        # Now use
        baseline = self.farm_year.baseline_budget_data
        br = baseline['revenue']
        bb = baseline['budget']
        cur = self.farm_year.current_budget_data
        cr = cur['revenue']
        cb = cur['budget']
        # Generate variance budget
        var_rev = getvar(br, cr)
        var_bud = getvar(bb, cb)
        if var_rev is None or var_bud is None:
            return None
        varbt = BudgetTable(self.farm_year, self,
                            revenue_data=var_rev, budget_data=var_bud)
        rd = varbt.revenue_details
        kd = KeyData(self.farm_year, self)

        var_budget = {}
        var_budget['rev'] = rd.get_rows()
        var_budget['revfmt'] = rd.get_formats()
        var_budget['info'] = varbt.get_info()
        var_budget['tables'] = varbt.get_tables()
        var_budget['keydata'] = kd.get_tables()
        return var_budget


class BudgetTable(object):
    """
    Generates the three or four detail budget tables, the first scaled in
    $1,000 or kilodollars (kd), the second scaled per acre (pa), the third scaled
    per bushel (pb), and if the farm has wheat/dc beans, a dc beans table in (kd)
    """

    def __init__(self, farm_year, mgr, revenue_data=None, budget_data=None):
        """
        Optional revenue_data and budget_data for computing variance
        Get a queryset of all farm crops with budgets for the farm year
          ordered by farm_crop_type.  If no farm crops have budgets, return None.
          The view should check for None, and show a message about adding budgets.
        """
        self.farm_year = farm_year
        self.revenue_details = RevenueDetails(farm_year, mgr, data=revenue_data)
        # numerical data used in budgets (dict of lists)
        self.data = budget_data
        # Some budget values are computed using revenue detail data
        if revenue_data is None:
            self.revenue_details.set_data()

        self.farm_crops = mgr.farm_crops

        self.row_labels = [
            'Crop Revenue', 'ARC/PLC',
            "Other Gov't Payments", 'Crop Insurance Proceeds', 'Other Revenue',
            'Gross Revenue', 'Fertilizers', 'Pesticides', 'Seed', 'Drying', 'Storage',
            'Crop Insurance', 'Other', 'Total Direct Costs', 'Machine hire/lease',
            'Utilities', 'Machine Repair', 'Fuel and Oil (Inc. Irrigation)',
            'Light vehicle', 'Mach. Depreciation', 'Total Power Costs', 'Hired Labor',
            'Building repair and rent', 'Building depreciation', 'Insurance', 'Misc.',
            'Interest (non-land)', 'Other Costs', 'Total Overhead Costs',
            'Non-Land Costs', 'Yield Based Adj. to Non-Land Costs',
            'Total Adjusted Non-Land Costs', 'Operator and Land Return',
            'Rented Land Costs', 'Revenue Based Adj. to Land Rent',
            'Adjusted Land Rent', 'Owned Land Cost (incl. princ. pmts.)',
            'Total Land Costs', 'Total Costs', 'PRE-TAX CASH FLOW',
            'Adj. Land Rent / Rented Ac.', 'Owned Land Cost / Owned Ac.'
        ]

        self.ROWS = [
            # data key, other, no_total, dollarsign
            ('crop_revenue', 0, False, True),
            ('gov_pmt', 0, False, False),
            ('other_gov_pmts', 0, False, False),
            ('crop_ins_indems', 0, False, False),
            ('other_revenue', self.farm_year.other_nongrain_income, False, False),
            ('gross_revenue', self.farm_year.other_nongrain_income, False, True),
            ('fertilizers', 0, False, False),
            ('pesticides', 0, False, False),
            ('seed', 0, False, False),
            ('drying', 0, False, False),
            ('storage', 0, False, False),
            ('crop_ins_prems', 0, False, False),
            ('other_direct_costs', 0, False, False),
            ('total_direct_costs', 0, False, True),
            ('machine_hire_lease', 0, False, False),
            ('utilities', 0, False, False),
            ('machine_repair', 0, False, False),
            ('fuel_and_oil', 0, False, False),
            ('light_vehicle', 0, False, False),
            ('machine_depreciation', 0, False, False),
            ('total_power_costs', 0, False, True),
            ('hired_labor', 0, False, False),
            ('building_repair_rent', 0, False, False),
            ('building_depreciation', 0, False, False),
            ('insurance', 0, False, False),
            ('misc', 0, False, False),
            ('interest_nonland', 0, False, False),
            ('other_costs', self.farm_year.other_nongrain_expense, False, False),
            ('total_overhead_costs', self.farm_year.other_nongrain_expense,
             False, True),
            ('total_nonland_costs', self.farm_year.other_nongrain_expense,
             False, False),
            ('yield_adj_to_nonland_costs', 0, False, False),
            ('total_adj_nonland_costs', self.farm_year.other_nongrain_expense,
             False, True),
            ('operator_and_land_return', (self.farm_year.other_nongrain_income -
                                          self.farm_year.other_nongrain_expense),
             False, True),
            ('land_costs', 0, False, False),
            ('revenue_based_adjustment_to_land_rent', 0, False, False),
            ('adjusted_land_rent', 0, False, True),
            ('owned_land_cost', 0, False, False),
            ('total_land_cost', 0, False, True),
            ('total_cost', self.farm_year.other_nongrain_expense, False, True),
            ('cash_flow', (self.farm_year.other_nongrain_income -
                           self.farm_year.other_nongrain_expense), False, True),
            ('adj_land_rent_per_rented_ac', 0, False, True),
            ('owned_land_cost_per_owned_ac', 0, False, True),
        ]
        self.rowdict = {r[0]: r[1] for r in self.ROWS}

        for fc in self.farm_crops:
            fc.get_crop_ins_prems()

        self.bushels = [fc.sens_production_bu() for fc in self.farm_crops]
        self.acres = [fc.planted_acres for fc in self.farm_crops]
        self.farm_crop_types = [fc.farm_crop_type for fc in self.farm_crops]
        self.fsacres = [0 if fc.farm_crop_type.is_fac else fc.planted_acres
                        for fc in self.farm_crops]
        self.total_planted_acres = sum(self.acres)
        self.total_rented_acres = self.farm_year.total_rented_acres()
        self.total_owned_acres = self.farm_year.cropland_acres_owned
        self.total_farm_acres = self.total_rented_acres + self.total_owned_acres
        self.rented_acres = [
            (0 if (fc.farm_crop_type.is_fac or self.total_farm_acres == 0) else
             fc.planted_acres * self.total_rented_acres / self.total_farm_acres)
            for fc in self.farm_crops]
        self.owned_acres = [
            (0 if (fc.farm_crop_type.is_fac or self.total_farm_acres == 0) else
             fc.planted_acres * self.total_owned_acres / self.total_farm_acres)
            for fc in self.farm_crops]
        self.blank_before_rows = [0, 1, 6, 14, 21, 29, 32, 33, 36, 38, 39, 40]

    def get_info(self):
        return {'farmyear': self.farm_year.pk,
                'bh': [1, 7, 16, 24, 33, 35, 36, 37, 39, 41, 42, 43, 44, 46, 48, 50],
                'bd': [1, 5, 7, 14, 16, 24, 33, 37, 39, 43, 46, 48, 50],
                'ol': [7, 16, 24, 33, 37, 43],
                }

    def get_tables(self):
        if len(self.farm_crops) == 0:
            return None
        # Calculate overall gov pmt
        self.farmyear_gov_pmt = self.farm_year.calc_gov_pmt()
        if self.data is None:
            self.set_data()
        results = {'kd': self.make_thousands(),
                   'pa': self.make_peracre(),
                   'pb': self.make_perbushel(), }
        wheatdc = self.make_wheatdc()
        if wheatdc is not None:
            results['wheatdc'] = wheatdc
        return results

    def get_headers(self, kd=False):
        # split crop names into two rows
        colheads = [str(fct).split() for fct in self.farm_crop_types]
        if kd:
            colheads += [['Other'], ['Total']]
        ncols = len(colheads)
        colheads = [['']+name if len(name) == 1 else name for name in colheads]
        return [(('', [name[i] for name in colheads]) if kd else
                [name[i] for name in colheads]) for i in range(2)], ncols

    def make_thousands(self):
        """
        Make the ($000) budget table rows
        """
        self.ROWS
        headers, ncols = self.get_headers(kd=True)
        results = [(n, self.getrow(row, 'kd')) for n, row in
                   zip(self.row_labels[:-2], self.ROWS[:-2])]
        # Last two rows have special totals (weighted averages)
        rows = self.ROWS[-2:]
        ns = self.row_labels[-2:]
        totdata = []
        totac = self.total_rented_acres
        totdata.append(0 if totac == 0 else
                       1000 * sum(self.data['adjusted_land_rent'])/totac)
        totac = self.total_owned_acres
        totdata.append(0 if totac == 0 else
                       1000 * sum(self.data['owned_land_cost'])/totac)
        results += [(n, self.getrow(row, 'kd', specialtot=tot))
                    for n, row, tot in zip(ns, rows, totdata)]
        for b in self.blank_before_rows[-1::-1]:
            results.insert(b, ('', ['']*ncols))
        return headers, results

    def make_peracre(self):
        """
        Make the per acre budget table rows
        """
        headers, ncols = self.get_headers()
        results = [self.getrow(row, 'pa') for row in self.ROWS[:-2]]
        results += [[''] * ncols for i in range(2)]
        for b in self.blank_before_rows[-1::-1]:
            results.insert(b, ['']*ncols)
        return headers, results

    def make_perbushel(self):
        """
        Make the per bushel budget table rows
        """
        headers, ncols = self.get_headers()
        results = [self.getrow(row, 'pb') for row in self.ROWS[:-2]]
        results += [[''] * ncols for i in range(2)]
        for b in self.blank_before_rows[-1::-1]:
            results.insert(b, ['']*ncols)
        return headers, results

    def make_wheatdc(self):
        """
        Make the wheat dc budget table if we have budgets for wheat and dc beans
        """
        fcts = [fct.pk for fct in self.farm_crop_types]
        if 5 not in fcts or 3 not in fcts:
            return None
        ixs = [fcts.index(pk) for pk in [3, 5]]
        vals = [[self.data[row[0]][i] for i in ixs]
                for row in self.ROWS[:-2]]
        acres = [self.acres[i] for i in ixs]
        dss = [row[3] for row in self.ROWS[:-2]]
        headers = [['', ''], ['$(000)', '$/acre']]
        results = [[add_ds(f'{sum(pair)/1000:,.0f}', no_ds=not ds),
                    add_ds(f'{sum((v/a for v, a in zip(pair, acres))):,.0f}',
                           no_ds=not ds)]
                   for pair, ds in zip(vals, dss)]
        footer = [['']*2 for i in range(2)]
        results += footer
        for b in self.blank_before_rows[-1::-1]:
            results.insert(b, ['']*2)
        return headers, results

    def getrow(self, props, scaling, specialtot=None):
        """
        Perform totalling scaling and text formatting for a table row
        """
        name, _, no_totcol, dollarsign = props
        items = self.data[name]
        if scaling == 'kd':
            cols = [add_ds(f'{val/1000:,.0f}', no_ds=not dollarsign)
                    for val in items[:-1]]
            cols.append('' if items[-1] == 0 else
                        add_ds(f'{items[-1]/1000:,.0f}', no_ds=not dollarsign))
            totval = sum(items[:-1]) if specialtot is None else specialtot
            cols.append(
                '' if no_totcol else
                add_ds(f'{(totval + items[-1])/1000:,.0f}', no_ds=not dollarsign))
        elif scaling == 'pa':
            cols = [add_ds(f'{val/ac:,.0f}', no_ds=not dollarsign)
                    for val, ac in zip(items, self.acres)]
        elif scaling == 'pb':
            cols = [add_ds(f'{val/bu:,.2f}', no_ds=not dollarsign)
                    for val, bu in zip(items, self.bushels)]
        else:  # get raw numbers
            cols = items[:]
        return cols

    def set_data(self):
        """
        Set data dict values in dollars.
        Some values depend on revenue_details data being set.
        """
        self.data = {}
        self.data['crop_revenue'] = [
            rev*1000 for rev
            in self.revenue_details.data['total_crop_revenue']]
        self.data['gov_pmt'] = [
            self.farmyear_gov_pmt * fc.planted_acres / self.total_planted_acres
            for fc in self.farm_crops]
        self.data['other_gov_pmts'] = [
            gp * ac for gp, ac in zip((fc.farmbudgetcrop.other_gov_pmts
                                       for fc in self.farm_crops), self.acres)]
        self.data['crop_ins_indems'] = [
            ind * ac for ind, ac in zip((fc.get_total_indemnities()
                                        for fc in self.farm_crops), self.acres)]
        self.data['other_revenue'] = [
            orv * ac for orv, ac in zip((fc.farmbudgetcrop.other_revenue
                                         for fc in self.farm_crops), self.acres)]
        self.data['gross_revenue'] = [
            sum(items) for items in zip(
                self.data['crop_revenue'], self.data['gov_pmt'],
                self.data['crop_ins_indems'], self.data['other_revenue'])]
        self.data['fertilizers'] = [
            f * ac for f, ac in zip((fc.farmbudgetcrop.fertilizers
                                     for fc in self.farm_crops), self.acres)]
        self.data['pesticides'] = [
            p * ac for p, ac in zip((fc.farmbudgetcrop.pesticides
                                     for fc in self.farm_crops), self.acres)]
        self.data['seed'] = [
            s * ac for s, ac in zip((fc.farmbudgetcrop.seed
                                     for fc in self.farm_crops), self.acres)]
        self.data['drying'] = [
            d * ac for d, ac in zip((fc.farmbudgetcrop.drying
                                     for fc in self.farm_crops), self.acres)]
        self.data['storage'] = [
            s * ac for s, ac in zip((fc.farmbudgetcrop.storage
                                     for fc in self.farm_crops), self.acres)]
        self.data['crop_ins_prems'] = [
            (0 if p is None else p * ac)
            for p, ac in zip((fc.get_total_premiums()
                              for fc in self.farm_crops), self.acres)]
        self.data['other_direct_costs'] = [
            odc * ac for odc, ac in zip((fc.farmbudgetcrop.other_direct_costs
                                         for fc in self.farm_crops), self.acres)]
        self.data['total_direct_costs'] = [
            sum(items) for items in zip(
                self.data['fertilizers'], self.data['pesticides'],
                self.data['seed'], self.data['drying'], self.data['storage'],
                self.data['crop_ins_prems'], self.data['other_direct_costs'])]
        self.data['machine_hire_lease'] = [
            mhl * ac for mhl, ac in zip((fc.farmbudgetcrop.machine_hire_lease
                                         for fc in self.farm_crops), self.acres)]
        self.data['utilities'] = [
            u * ac for u, ac in zip((fc.farmbudgetcrop.utilities
                                     for fc in self.farm_crops), self.acres)]
        self.data['machine_repair'] = [
            mr * ac for mr, ac in zip((fc.farmbudgetcrop.machine_repair
                                       for fc in self.farm_crops), self.acres)]
        self.data['fuel_and_oil'] = [
            fo * ac for fo, ac in zip((fc.farmbudgetcrop.fuel_and_oil
                                       for fc in self.farm_crops), self.acres)]
        self.data['light_vehicle'] = [
            lv * ac for lv, ac in zip((fc.farmbudgetcrop.light_vehicle
                                       for fc in self.farm_crops), self.acres)]
        self.data['machine_depreciation'] = [
            md * ac for md, ac in zip((fc.farmbudgetcrop.machine_depr
                                       for fc in self.farm_crops), self.acres)]
        self.data['total_power_costs'] = [
            sum(items) for items in zip(
                self.data['machine_hire_lease'], self.data['utilities'],
                self.data['machine_repair'], self.data['fuel_and_oil'],
                self.data['light_vehicle'], self.data['machine_depreciation'])]
        self.data['hired_labor'] = [
            lm * ac for lm, ac in zip((fc.farmbudgetcrop.labor_and_mgmt
                                       for fc in self.farm_crops), self.acres)]
        self.data['building_repair_rent'] = [
            br * ac for br, ac in zip((fc.farmbudgetcrop.building_repair_and_rent
                                       for fc in self.farm_crops), self.acres)]
        self.data['building_depreciation'] = [
            bd * ac for bd, ac in zip((fc.farmbudgetcrop.building_depr
                                       for fc in self.farm_crops), self.acres)]
        self.data['insurance'] = [
            ins * ac for ins, ac in zip((fc.farmbudgetcrop.insurance
                                         for fc in self.farm_crops), self.acres)]
        self.data['misc'] = [
            mc * ac for mc, ac in zip((fc.farmbudgetcrop.misc_overhead_costs
                                       for fc in self.farm_crops), self.acres)]
        self.data['interest_nonland'] = [
            inl * ac for inl, ac in zip((fc.farmbudgetcrop.interest_nonland
                                         for fc in self.farm_crops), self.acres)]
        self.data['other_costs'] = [
            oc * ac for oc, ac in zip((fc.farmbudgetcrop.other_overhead_costs
                                       for fc in self.farm_crops), self.acres)]
        self.data['total_overhead_costs'] = [
            sum(items) for items in zip(
                self.data['hired_labor'], self.data['building_repair_rent'],
                self.data['building_depreciation'], self.data['insurance'],
                self.data['misc'], self.data['interest_nonland'],
                self.data['other_costs'])]
        self.data['total_nonland_costs'] = [
            sum(items) for items in zip(
                self.data['total_direct_costs'], self.data['total_power_costs'],
                self.data['total_overhead_costs'])]
        self.data['yield_adj_to_nonland_costs'] = [
            var * nlc for var, nlc in
            zip((fc.yield_adj_to_nonland_costs()
                 for fc in self.farm_crops),
                self.data['total_nonland_costs'])]
        self.data['total_adj_nonland_costs'] = [
            tnc + ya for tnc, ya in
            zip(self.data['total_nonland_costs'],
                self.data['yield_adj_to_nonland_costs'])]
        self.data['operator_and_land_return'] = [
            gr - tnc for gr, tnc in
            zip(self.data['gross_revenue'], self.data['total_adj_nonland_costs'])]
        self.data['land_costs'] = [
            ra * lc for ra, lc in zip(self.rented_acres,
                                      (fc.farmbudgetcrop.rented_land_costs
                                       for fc in self.farm_crops))]
        self.data['revenue_based_adjustment_to_land_rent'] = [
            adj * lc for adj, lc in zip(
                [fc.revenue_based_adj_to_land_rent() for fc in self.farm_crops],
                self.data['land_costs'])]
        self.data['adjusted_land_rent'] = [
            lc + ra for lc, ra in
            zip(self.data['land_costs'],
                self.data['revenue_based_adjustment_to_land_rent'])]

        land_cost = self.farm_year.total_owned_land_expense()
        farm_acres = self.total_farm_acres
        self.data['owned_land_cost'] = [
            (0 if farm_acres == 0 else land_cost / farm_acres * ac)
            for ac in self.fsacres]

        self.data['total_land_cost'] = [rent + lc for rent, lc in
                                        zip(self.data['adjusted_land_rent'],
                                            self.data['owned_land_cost'])]
        self.data['total_cost'] = [
            nlc + lc for nlc, lc in
            zip(self.data['total_adj_nonland_costs'], self.data['total_land_cost'])]
        self.data['cash_flow'] = [gr - tc for gr, tc in zip(self.data['gross_revenue'],
                                                            self.data['total_cost'])]
        self.data['adj_land_rent_per_rented_ac'] = [
            (0 if ra == 0 else alr * 1000 / ra) for alr, ra in
            zip(self.data['adjusted_land_rent'], self.rented_acres)]
        self.data['owned_land_cost_per_owned_ac'] = [
            (0 if oa == 0 else olc * 1000 / oa) for olc, oa in
            zip(self.data['owned_land_cost'], self.owned_acres)]

        # append 'other' value
        for k, v in self.data.items():
            v.append(self.rowdict[k])


class RevenueDetails:
    """
    Generates data and a nested list structure (table rows) for a Grain Revenue
    buildup table to be included with the Detailed Budget
    """
    def __init__(self, farm_year, mgr, data=None):
        """ optional data argument for variance budget computation """

        self.farm_year = farm_year

        self.data = data

        self.farm_crops = mgr.farm_crops

        # Blank column before total is for alignment with budget
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
            ('Uncontracted Futures (000s bu)', 'uncontracted_futures',
             True, 1, False),
            ('Total Sensitized Production (000s)', 'production_bushels',
             True, 1, False),
            ('Contracted Basis (000s bu)', 'contracted_basis_qty',
             True, 1, False),
            ('Uncontracted Basis (000s bu)', 'uncontracted_basis_qty',
             True, 1, False),
            ('Total Sensitized Production (000s)', 'production_bushels',
             True, 1, False),
            ('Average Futures Contract Price', 'avg_fut_contract_prices',
             False, 2, True),
            ('Current Harvest Futures Price', 'harvest_futures_prices',
             False, 2, True),
            ('Average Basis Contract Price', 'avg_basis_contract_prices',
             False, 2, True),
            ('Assumed Basis on Remaining', 'assumed_basis_on_remaining',
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
            ('Uncontracted Revenue ($000)', 16),
        ]

        self.BLANK_ROWS = [0, 3, 6, 9, 11, 13, 17, 21]

    def get_headers(self):
        # split crop names into two rows
        colheads = ([str(fc.farm_crop_type).split() for fc in self.farm_crops] +
                    [[''], ['Total']])
        colheads = [['']+name if len(name) == 1 else name for name in colheads]
        return [('', [name[i] for name in colheads])
                for i in range(2)]

    def get_rows(self):
        """
        Main Method (returns table rows as nested list of strings)
        """
        ncrp = len(self.farm_crops)
        blank = ('', [''] * (ncrp + 2))
        titles = [((title, [''] * (ncrp + 2)), insrow)
                  for title, insrow in self.SECTION_TITLES]
        if self.data is None:
            self.set_data()
        rows = []
        for title, var, tot, rd, ds in self.ROWS:
            fmt = '{:,.' + str(rd) + 'f}'
            nums = []
            nums[:] = self.data[var]
            row = [add_ds(fmt.format(num), no_ds=not ds) for num in nums]
            row.append('')  # spacer to align with budget
            row.append(add_ds(fmt.format(sum(nums)), no_ds=not ds)
                       if tot else '')
            rows.append((title, row))
        for t, ir in titles[-1::-1]:
            rows.insert(ir, t)
        for ix in self.BLANK_ROWS[-1::-1]:
            rows.insert(ix, blank)
        return self.get_headers(), rows

    def get_formats(self):
        """
        Bold headers and bold data columns
        """
        return {'bh': [19, 24, 29, 30],
                'bd': [13, 14, 29, 30],
                'ol': [7, 11, 22, 27],
                'blank': len(self.farm_crops), }

    def set_data(self):
        self.data = {}
        self.data['farm_yields'] = [fc.sens_farm_expected_yield()
                                    for fc in self.farm_crops]
        self.data['planted_acres'] = [fc.planted_acres for fc in self.farm_crops]
        self.data['production_bushels'] = [
            ac * yld / 1000 for (ac, yld) in
            zip(self.data['planted_acres'], self.data['farm_yields'])]
        self.data['contracted_futures'] = [fc.fut_contracted_bu() / 1000
                                           for fc in self.farm_crops]
        self.data['uncontracted_futures'] = [
            pb - cf for pb, cf in zip(self.data['production_bushels'],
                                      self.data['contracted_futures'])]
        self.data['contracted_basis_qty'] = [fc.basis_bu_locked() / 1000
                                             for fc in self.farm_crops]
        self.data['uncontracted_basis_qty'] = [
            pb - cb for pb, cb in zip(self.data['production_bushels'],
                                      self.data['contracted_basis_qty'])]
        self.data['avg_fut_contract_prices'] = [fc.avg_contract_price()
                                                for fc in self.farm_crops]
        self.data['harvest_futures_prices'] = [fc.sens_harvest_price()
                                               for fc in self.farm_crops]
        self.data['avg_basis_contract_prices'] = [fc.avg_locked_basis()
                                                  for fc in self.farm_crops]
        self.data['assumed_basis_on_remaining'] = [fc.assumed_basis_for_new()
                                                   for fc in self.farm_crops]
        self.data['contracted_futures_revenue'] = [
            fb * fp for fb, fp in zip(self.data['contracted_futures'],
                                      self.data['avg_fut_contract_prices'])]
        self.data['contracted_basis_revenue'] = [
            bb * bp for bb, bp in zip(self.data['contracted_basis_qty'],
                                      self.data['avg_basis_contract_prices'])]
        self.data['total_contracted_revenue'] = [
            fr + br for fr, br in zip(self.data['contracted_futures_revenue'],
                                      self.data['contracted_basis_revenue'])]
        self.data['uncontracted_futures_revenue'] = [
            p * uf for p, uf in zip(self.data['harvest_futures_prices'],
                                    self.data['uncontracted_futures'])]
        self.data['uncontracted_basis_revenue'] = [
            ab * ub for ab, ub in zip(self.data['assumed_basis_on_remaining'],
                                      self.data['uncontracted_basis_qty'])]
        self.data['total_uncontracted_revenue'] = [
            uf + ub for uf, ub in zip(self.data['uncontracted_futures_revenue'],
                                      self.data['uncontracted_basis_revenue'])]
        self.data['total_crop_revenue'] = [
            cr + ur for cr, ur in zip(self.data['total_contracted_revenue'],
                                      self.data['total_uncontracted_revenue'])]
        self.data['realized_price_per_bushel'] = [
            tcr / pb for tcr, pb in zip(self.data['total_crop_revenue'],
                                        self.data['production_bushels'])]


class KeyData(object):
    """
    Generates Key Data tables associated with current budget
    """
    def __init__(self, farm_year, mgr):
        self.farm_year = farm_year
        self.model_run = self.farm_year.get_model_run_date()
        self.farm_crops = mgr.farm_crops
        self.market_crops_all = [mc for mc in self.farm_year.market_crops.all()]
        self.market_crops = [mc for mc in self.market_crops_all if mc.pk in
                             [fc.market_crop_id for fc in self.farm_crops]]
        self.fsa_crops = [fsc for fsc in self.farm_year.fsa_crops.all()]
        self.farm_crop_names = [
            str(fc.farm_crop_type).replace('Winter', 'W').replace('Spring', 'S')
            for fc in self.farm_crops]
        self.market_crop_names = [
            str(mc.market_crop_type).replace('Winter', 'W').replace('Spring', 'S')
            for mc in self.market_crops]
        self.market_crop_names_all = [
            str(mc.market_crop_type).replace('Winter', 'W').replace('Spring', 'S')
            for mc in self.market_crops_all]

    def get_yield_headers(self):
        colheads = ([str(fc.farm_crop_type).split() for fc in self.farm_crops])
        colheads = [['']+name if len(name) == 1 else name for name in colheads]
        return [('', [name[i] for name in colheads])
                for i in range(2)]

    def get_market_price_headers(self):
        colheads = ([str(mc.market_crop_type).split() for mc in self.market_crops_all])
        colheads = [['']+name if len(name) == 1 else name for name in colheads]
        return [('', [name[i] for name in colheads])
                for i in range(2)]

    def get_fut_contract_headers(self):
        colheads = ([str(mc.market_crop_type).split() for mc in self.market_crops])
        colheads = [['']+name if len(name) == 1 else name for name in colheads]
        return [('', [name[i] for name in colheads])
                for i in range(2)]

    def get_crop_ins_headers(self):
        colheads = ([str(fc.farm_crop_type).split() for fc in self.farm_crops] +
                    [['$000']])
        colheads = [['']+name if len(name) == 1 else name for name in colheads]
        return [('', [name[i] for name in colheads])
                for i in range(2)]

    def get_tables(self):
        if len(self.farm_crops) == 0:
            return {}
        return {
            'modelrun': self.model_run_table(),
            'yield': self.yield_table(),
            'price': self.market_price_table(),
            'futctr': self.fut_contract_table(),
            'cropins': self.crop_ins_table(),
            'title': self.title_table(),
        }

    def model_run_table(self):
        """
        Show model run date
        """
        mrd = self.farm_year.get_model_run_date().strftime("%m/%d/%Y")
        rows = []
        rows.append(('Model Run Date', [f'{mrd}']))
        return {'rows': rows}

    def yield_table(self):
        """
        Show yield factor, actual yields
        """
        info = [(fc.farmbudgetcrop.yield_factor, fc.farm_expected_yield(),
                 fc.sens_farm_expected_yield(), fc.sens_cty_expected_yield())
                for fc in self.farm_crops]

        yfs, yields, sensyields, senscty = zip(*info)
        rows = []
        rows.append(('Yields', []))
        rows += self.get_yield_headers()
        rows.append(('Assumed Farm Yields', [f'{yld:.0f}' for yld in yields]))
        rows.append(('Yield Sensitivity Factor', [f'{yf:.0%}' for yf in yfs]))
        rows.append(('Sensitized Farm Yields',
                     [f'{syld:.0f}' for syld in sensyields]))
        rows.append(('Sensitized County Yields',
                     [f'{scty:.0f}' for scty in senscty]))
        colspan = len(yields) + 1
        return {'rows': rows, 'colspan': colspan}

    def market_price_table(self):
        """
        Show current harvest futures, price factor, sensitized harvest price
        """
        info = [(mc.price_factor, mc.harvest_price(), mc.sens_harvest_price())
                for mc in self.market_crops_all]
        pfs, prices, sprices = zip(*info)
        rows = []
        rows.append(('Prices', []))
        rows += self.get_market_price_headers()
        rows.append(('Current Harvest Futures', [f'${p:.2f}' for p in prices]))
        rows.append(('Price Sensitivity Factor', [f'{p:.0%}' for p in pfs]))
        rows.append(('Assumed Harvest Price', [f'${p:.2f}' for p in sprices]))
        colspan = len(prices) + 1
        return {'rows': rows, 'colspan': colspan}

    def fut_contract_table(self):
        """
        Show pct of expected bushels and avg. contract price
        """
        info = ((mc.futures_pct_of_expected(), mc.avg_contract_price())
                for mc in self.market_crops)
        spcts, ctprices = zip(*info)
        rows = []
        rows.append(('Marketed Futures', []))
        rows += self.get_fut_contract_headers()
        # rows.append(('', self.market_crop_names))
        rows.append(('% of Expected Bushels', [f'{pct:.0%}' for pct in spcts]))
        rows.append(('Avg. Futures Contract Price', [f'${pr:.2f}' for pr in ctprices]))
        colspan = len(spcts) + 1
        return {'rows': rows, 'colspan': colspan}

    def crop_ins_table(self):
        """
        Show crop insurance selections for each crop and costs in ($000) with total
        """
        base_policies = [
            (fc.coverage_type, fc.product_type, fc.base_coverage_level)
            for fc in self.farm_crops]
        options = [(fc.sco_use, fc.eco_level) for fc in self.farm_crops]
        ci_info = [fc.get_selected_premiums() for fc in self.farm_crops]
        baselabels = []
        scolabels = []
        ecolabels = []
        basecost = 0
        scocost = 0
        ecocost = 0
        for i, ci in enumerate(ci_info):
            ct, pt, cl = base_policies[i]
            ctname = 'Farm' if ct == 1 else 'County' if ct == 0 else 'None'
            ptname = ('RP' if pt == 0 else 'RP-HPE' if pt == 1 else
                      'YP' if pt == 2 else 'None')
            baselvl = 'None' if cl is None else f'{cl:.0%}'
            baselabels.append('None' if ct is None or pt is None or cl is None
                              else f'{ctname} {ptname} {baselvl}')
            scolabels.append('SCO 86%' if options[i][0] else 'No SCO')
            ecolabels.append(f'ECO {options[i][1]:.0%}'
                             if options[i][1] is not None else 'No ECO')
            acres = self.farm_crops[i].planted_acres
            if ci is not None:
                basecost += ci['base'] * acres
                scocost += ci['sco'] * acres
                ecocost += ci['eco'] * acres
        allcosts = [basecost, scocost, ecocost]
        allcosts.append(sum(allcosts))
        costs = [f'${c / 1000:.0f}' for c in allcosts]

        rows = []
        rows.append(('Crop Insurance', []))
        rows += self.get_crop_ins_headers()
        # rows.append(('', self.farm_crop_names + ['$000']))
        rows.append(('Base Policy', baselabels + [costs[0]]))
        rows.append(('SCO', scolabels + [costs[1]]))
        rows.append(('ECO', ecolabels + [costs[2]]))
        rows.append(('Total', [''] * len(baselabels) + [costs[3]]))
        colspan = len(baselabels) + 2
        return {'rows': rows, 'colspan': colspan}

    def title_table(self):
        """
        show PLC acres and ARC-CO acres
        """
        info = [(str(fsc.fsa_crop_type), fsc.plc_base_acres, fsc.arcco_base_acres,
                 fsc.plc_base_acres + fsc.arcco_base_acres,
                 fsc.sens_mya_price(pf=1), fsc.sens_mya_price())
                for fsc in self.fsa_crops]
        cropnames, plc_acres, arcco_acres, tot_acres, myas, smyas = zip(*info)
        rows = []
        rows.append(('Title', []))
        rows.append(('Title Election', cropnames))
        rows.append(('PLC Acres',
                     [f'{0 if tot == 0 else ac/tot:.0%}'
                      for ac, tot in zip(plc_acres, tot_acres)]))
        rows.append(('ARC-CO Acres',
                     [f'{0 if tot == 0 else ac/tot:.0%}'
                      for ac, tot in zip(arcco_acres, tot_acres)]))
        rows.append(('Estimated MYA Price', [f'${mya:.2f}' for mya in smyas]))
        colspan = len(cropnames) + 1
        return {'rows': rows, 'colspan': colspan}


# Dollar sign helper
def add_ds(text, no_ds=False):
    return (text if no_ds else
            f'-${text[1:]}' if text[0] == '-' else f'${text}')
