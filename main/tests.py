from datetime import datetime

from django.test import TestCase

from .models.farm_year import FarmYear
from .models.farm_crop import FarmCrop
from .models.budget_table import BudgetManager

from django.contrib.auth.models import User


class FarmYearTestCase(TestCase):
    def setUp(self):
        joe = User.objects.create(username='joe124', password='verrysekrit')
        self.farm_year = FarmYear.objects.create(user=joe, farm_name="Joey's farm",
                                                 state_id=5, county_code=1)

    def test_farm_year(self):
        self.assertEqual(self.farm_year.farm_crops.count(), 4)

    def test_farm_crop_types(self):
        for fc in self.farm_year.farm_crops.all():
            self.assertIn(fc.farm_crop_type_id, (1, 2, 3, 5))


class Madison2023FarmYearTestCase(TestCase):
    def setUp(self):
        dt = datetime(2023, 6, 12)
        jim = User.objects.create(username='jimbo', password='drowssap')
        self.farm_year = FarmYear.objects.create(user=jim, farm_name="Madison Farm",
                                                 state_id=17, county_code=119)
        # update the farm year
        FarmYear.objects.filter(pk=self.farm_year.pk).update(
            cropland_acres_owned=2400, cash_rented_acres=2000,
            var_rent_cap_floor_frac=.1, annual_land_int_expense=150000,
            annual_land_principal_pmt=500000, property_taxes=250000,
            land_repairs=100000, eligible_persons_for_cap=2,
            other_nongrain_expense=140000, other_nongrain_income=150000,
            is_model_run_date_manual=True, manual_model_run_date=dt,
            variable_rented_acres=1000)
        # ensure that the farm year instance is in sync with the db
        self.farm_year = FarmYear.objects.get(pk=self.farm_year.pk)
        # update the farm crops
        self.farm_year.farm_crops.filter(farm_crop_type_id=1).update(
            planted_acres=2500, ta_aph_yield=205, adj_yield=195, rate_yield=195,
            ye_use=True, ta_use=True, coverage_type=1, product_type=0,
            base_coverage_level=.8)
        self.farm_year.farm_crops.filter(farm_crop_type_id=2).update(
            planted_acres=2500, ta_aph_yield=75, adj_yield=69, rate_yield=69,
            ye_use=True, ta_use=True, coverage_type=1, product_type=0,
            base_coverage_level=.8)
        self.farm_year.farm_crops.filter(farm_crop_type_id=3).update(
            planted_acres=400, ta_aph_yield=88, adj_yield=82, rate_yield=82,
            ye_use=True, ta_use=True, coverage_type=1, product_type=0,
            base_coverage_level=.8)
        self.farm_year.farm_crops.filter(farm_crop_type_id=5).update(
            planted_acres=400, ta_aph_yield=55, adj_yield=50, rate_yield=50,
            ye_use=True, ta_use=True, coverage_type=1, product_type=0,
            base_coverage_level=.8)
        corn = self.farm_year.farm_crops.get(farm_crop_type_id=1)
        fsbeans = self.farm_year.farm_crops.get(farm_crop_type_id=2)
        wwheat = self.farm_year.farm_crops.get(farm_crop_type_id=3)
        dcbeans = self.farm_year.farm_crops.get(farm_crop_type_id=5)
        # add budgets
        FarmCrop.add_farm_budget_crop(corn.pk, 69)
        FarmCrop.add_farm_budget_crop(fsbeans.pk, 71)
        FarmCrop.add_farm_budget_crop(wwheat.pk, 73)
        FarmCrop.add_farm_budget_crop(dcbeans.pk, 74)
        # update the market crops
        qcorn = self.farm_year.market_crops.filter(market_crop_type_id=1)
        qcorn.update(assumed_basis_for_new=.1)
        qbeans = self.farm_year.market_crops.filter(market_crop_type_id=2)
        qbeans.update(assumed_basis_for_new=.1)
        qwwheat = self.farm_year.market_crops.filter(market_crop_type_id=3)
        qwwheat.update(assumed_basis_for_new=.1)
        corn = qcorn[0]
        beans = qbeans[0]
        wwheat = qwwheat[0]
        # add contracts
        corn.contracts.create(contract_date=dt, bushels=50000, price=3.5)
        corn.contracts.create(contract_date=dt, bushels=40000, price=3.6)
        corn.contracts.create(contract_date=dt, bushels=50000, price=.1, is_basis=True)
        beans.contracts.create(contract_date=dt, bushels=40000, price=13.2)
        beans.contracts.create(contract_date=dt, bushels=20000, price=.1, is_basis=True)
        wwheat.contracts.create(contract_date=dt, bushels=20000, price=7.1)
        wwheat.contracts.create(contract_date=dt, bushels=30000,
                                price=.12, is_basis=True)
        # update the fsa crops
        qcorn = self.farm_year.fsa_crops.filter(fsa_crop_type_id=1)
        qcorn.update(plc_base_acres=1250, arcco_base_acres=1250, plc_yield=180)
        qbeans = self.farm_year.fsa_crops.filter(fsa_crop_type_id=2)
        qbeans.update(plc_base_acres=1000, arcco_base_acres=2250, plc_yield=58)
        qwheat = self.farm_year.fsa_crops.filter(fsa_crop_type_id=3)
        qwheat.update(plc_base_acres=500, arcco_base_acres=0, plc_yield=65)

    def test_budget(self):
        mgr = BudgetManager(self.farm_year)
        mgr.build_current_budget()
        data = self.farm_year.current_budget_data
        expected = {
            'revenue':
            {'farm_yields': [227.0, 72.0, 85.0, 46.0],
             'planted_acres': [2500.0, 2500.0, 400.0, 400.0],
             'production_bushels': [567.5, 180.0, 34.0, 18.4],
             'contracted_futures': [90.0, 36.29032258064516, 20.0, 3.7096774193548385],
             'uncontracted_futures':
             [477.5, 143.70967741935485, 14.0, 14.69032258064516],
             'contracted_basis_qty':
             [50.0, 18.14516129032258, 30.0, 1.8548387096774193],
             'uncontracted_basis_qty':
             [517.5, 161.8548387096774, 4.0, 16.54516129032258],
             'avg_fut_contract_prices': [3.5444444444444443, 13.2, 7.1, 13.2],
             'harvest_futures_prices': [5.4925, 12.09, 6.46, 12.09],
             'avg_basis_contract_prices': [0.1, 0.1, 0.12, 0.1],
             'assumed_basis_on_remaining': [0.1, 0.1, 0.1, 0.1],
             'contracted_futures_revenue':
             [319.0, 479.0322580645161, 142.0, 48.967741935483865],
             'contracted_basis_revenue':
             [5.0, 1.814516129032258, 3.5999999999999996, 0.18548387096774194],
             'total_contracted_revenue':
             [324.0, 480.84677419354836, 145.6, 49.15322580645161],
             'uncontracted_futures_revenue': [2622.66875, 1737.45, 90.44, 177.606],
             'uncontracted_basis_revenue':
             [51.75, 16.18548387096774, 0.4, 1.6545161290322579],
             'total_uncontracted_revenue':
             [2674.41875, 1753.6354838709678, 90.84, 179.26051612903225],
             'total_crop_revenue':
             [2998.41875, 2234.4822580645164, 236.44, 228.41374193548387],
             'realized_price_per_bushel':
             [5.283557268722467, 12.413790322580647,
              6.9541176470588235, 12.413790322580645]},
            'budget':
            {'crop_revenue':
             [2998418.75, 2234482.2580645164, 236440.0, 228413.74193548388, 0],
             'gov_pmt': [0.0, 0.0, 0.0, 0.0, 0],
             'other_gov_pmts': [0.0, 0.0, 0.0, 0.0, 0],
             'crop_ins_indems': [0.0, 0.0, 18312.0, 19720.0, 0],
             'other_revenue': [0.0, 0.0, 0.0, 0.0, 150000.0],
             'gross_revenue':
             [2998418.75, 2234482.2580645164, 254752.0, 248133.74193548388, 150000.0],
             'fertilizers': [625000.0, 237500.0, 61600.0, 28400.0, 0],
             'pesticides': [307500.0, 185000.0, 10800.0, 26000.0, 0],
             'seed': [325000.0, 210000.0, 20000.0, 23600.0, 0],
             'drying': [85000.0, 10000.0, 400.0, 0.0, 0],
             'storage': [15000.0, 12500.0, 400.0, 400.0, 0],
             'crop_ins_prems': [45800.0, 33950.0, 13540.0, 6595.999999999999, 0],
             'other_direct_costs': [0.0, 0.0, 0.0, 0.0, 0],
             'total_direct_costs': [1403300.0, 688950.0, 106740.0, 84996.0, 0],
             'machine_hire_lease': [50000.0, 45000.0, 7200.0, 8800.0, 0],
             'utilities': [17500.0, 17500.0, 2800.0, 1600.0, 0],
             'machine_repair': [102500.0, 92500.0, 13200.0, 14800.0, 0],
             'fuel_and_oil': [85000.0, 65000.0, 8000.0, 14000.0, 0],
             'light_vehicle': [5000.0, 2500.0, 800.0, 800.0, 0],
             'machine_depreciation': [197500.0, 175000.0, 19600.0, 12800.0, 0],
             'total_power_costs': [457500.0, 397500.0, 51600.0, 52800.0, 0],
             'hired_labor': [62500.0, 55000.0, 9200.0, 7200.0, 0],
             'building_repair_rent': [20000.0, 17500.0, 2400.0, 2400.0, 0],
             'building_depreciation': [35000.0, 30000.0, 4000.0, 2000.0, 0],
             'insurance': [32500.0, 32500.0, 2000.0, 0.0, 0],
             'misc': [32500.0, 32500.0, 4400.0, 0.0, 0],
             'interest_nonland': [50000.0, 45000.0, 5600.0, 4800.0, 0],
             'other_costs': [0.0, 0.0, 0.0, 0.0, 140000.0],
             'total_overhead_costs': [232500.0, 212500.0, 27600.0, 16400.0, 140000.0],
             'total_nonland_costs':
             [2093300.0, 1298950.0, 185940.0, 154196.0, 140000.0],
             'yield_adj_to_nonland_costs': [0.0, 0.0, 0.0, 0.0, 0],
             'total_adj_nonland_costs':
             [2093300.0, 1298950.0, 185940.0, 154196.0, 140000.0],
             'operator_and_land_return':
             [905118.75, 935532.2580645164, 68812.0, 93937.74193548388, 10000.0],
             'land_costs':
             [473611.1111111111, 473611.1111111111, 75777.77777777778, 0.0, 0],
             'revenue_based_adjustment_to_land_rent':
             [-11152.433101460174, -15787.037037037036, -2525.925925925926, -0.0, 0],
             'adjusted_land_rent':
             [462458.67800965096, 457824.0740740741, 73251.85185185185, 0.0, 0],
             'owned_land_cost':
             [462962.962962963, 462962.962962963, 74074.07407407407, 0.0, 0],
             'total_land_cost':
             [925421.6409726139, 920787.0370370371, 147325.92592592593, 0.0, 0],
             'total_cost':
             [3018721.640972614, 2219737.0370370373,
              333265.92592592596, 154196.0, 140000.0],
             'pretax_amount':
             [-20302.890972613823, 14745.221027479041,
              -78513.92592592596, 93937.74193548388, 10000.0],
             'adj_land_rent_per_rented_ac':
             [332970.2481669487, 329633.3333333333, 329633.3333333333, 0, 0],
             'owned_land_cost_per_owned_ac':
             [416666.6666666667, 416666.6666666667, 416666.6666666667, 0, 0]}}
        self.assertEqual(data, expected)

    def test_budget_with_pf8_yf8(self):
        """
        test the budget with price_factor 0.8 for all market crops and
        yield_factor 0.8 for all farm_budget_crops
        """
        self.farm_year.market_crops.all().update(price_factor=0.8)
        self.farm_year.farmbudgetcrop_set.all().update(yield_factor=0.8)
        mgr = BudgetManager(self.farm_year)
        mgr.build_current_budget()
        data = self.farm_year.current_budget_data
        expected = {
            'revenue':
            {'farm_yields': [181.60000000000002, 57.6, 68.0, 36.800000000000004],
             'planted_acres': [2500.0, 2500.0, 400.0, 400.0],
             'production_bushels':
             [454.00000000000006, 144.0, 27.2, 14.720000000000002],
             'contracted_futures':
             [90.0, 36.29032258064516, 20.0, 3.7096774193548394],
             'uncontracted_futures':
             [364.00000000000006, 107.70967741935485,
              7.199999999999999, 11.010322580645163],
             'contracted_basis_qty':
             [50.0, 18.14516129032258, 30.0, 1.8548387096774197],
             'uncontracted_basis_qty':
             [404.00000000000006, 125.85483870967742,
              -2.8000000000000007, 12.865161290322582],
             'avg_fut_contract_prices':
             [3.5444444444444443, 13.2, 7.1, 13.2],
             'harvest_futures_prices': [4.394, 9.672, 5.168, 9.672],
             'avg_basis_contract_prices': [0.1, 0.1, 0.12, 0.1],
             'assumed_basis_on_remaining': [0.1, 0.1, 0.1, 0.1],
             'contracted_futures_revenue':
             [319.0, 479.0322580645161, 142.0, 48.96774193548388],
             'contracted_basis_revenue':
             [5.0, 1.814516129032258, 3.5999999999999996, 0.185483870967742],
             'total_contracted_revenue':
             [324.0, 480.84677419354836, 145.6, 49.15322580645162],
             'uncontracted_futures_revenue':
             [1599.4160000000004, 1041.7680000000003,
              37.209599999999995, 106.49184000000002],
             'uncontracted_basis_revenue':
             [40.400000000000006, 12.585483870967742,
              -0.2800000000000001, 1.2865161290322584],
             'total_uncontracted_revenue':
             [1639.8160000000005, 1054.353483870968,
              36.92959999999999, 107.77835612903229],
             'total_crop_revenue':
             [1963.8160000000005, 1535.2002580645162, 182.5296, 156.9315819354839],
             'realized_price_per_bushel':
             [4.325585903083701, 10.661112903225806,
              6.710647058823529, 10.661112903225806]},
            'budget':
            {'crop_revenue':
             [1963816.0000000005, 1535200.2580645161,
              182529.59999999998, 156931.5819354839, 0],
             'gov_pmt': [0.0, 0.0, 0.0, 0.0, 0],
             'other_gov_pmts': [0.0, 0.0, 0.0, 0.0, 0],
             'crop_ins_indems': [428225.0, 671225.0, 97384.0, 99804.0, 0],
             'other_revenue': [0.0, 0.0, 0.0, 0.0, 150000.0],
             'gross_revenue':
             [2392041.0000000005, 2206425.258064516,
              279913.6, 256735.5819354839, 150000.0],
             'fertilizers': [625000.0, 237500.0, 61600.0, 28400.0, 0],
             'pesticides': [307500.0, 185000.0, 10800.0, 26000.0, 0],
             'seed': [325000.0, 210000.0, 20000.0, 23600.0, 0],
             'drying': [85000.0, 10000.0, 400.0, 0.0, 0],
             'storage': [15000.0, 12500.0, 400.0, 400.0, 0],
             'crop_ins_prems': [45800.0, 33950.0, 13540.0, 6595.999999999999, 0],
             'other_direct_costs': [0.0, 0.0, 0.0, 0.0, 0],
             'total_direct_costs': [1403300.0, 688950.0, 106740.0, 84996.0, 0],
             'machine_hire_lease': [50000.0, 45000.0, 7200.0, 8800.0, 0],
             'utilities': [17500.0, 17500.0, 2800.0, 1600.0, 0],
             'machine_repair': [102500.0, 92500.0, 13200.0, 14800.0, 0],
             'fuel_and_oil': [85000.0, 65000.0, 8000.0, 14000.0, 0],
             'light_vehicle': [5000.0, 2500.0, 800.0, 800.0, 0],
             'machine_depreciation': [197500.0, 175000.0, 19600.0, 12800.0, 0],
             'total_power_costs': [457500.0, 397500.0, 51600.0, 52800.0, 0],
             'hired_labor': [62500.0, 55000.0, 9200.0, 7200.0, 0],
             'building_repair_rent': [20000.0, 17500.0, 2400.0, 2400.0, 0],
             'building_depreciation': [35000.0, 30000.0, 4000.0, 2000.0, 0],
             'insurance': [32500.0, 32500.0, 2000.0, 0.0, 0],
             'misc': [32500.0, 32500.0, 4400.0, 0.0, 0],
             'interest_nonland': [50000.0, 45000.0, 5600.0, 4800.0, 0],
             'other_costs': [0.0, 0.0, 0.0, 0.0, 140000.0],
             'total_overhead_costs': [232500.0, 212500.0, 27600.0, 16400.0, 140000.0],
             'total_nonland_costs':
             [2093300.0, 1298950.0, 185940.0, 154196.0, 140000.0],
             'yield_adj_to_nonland_costs':
             [-79545.39999999998, -51957.99999999999,
              -7065.719999999998, -5859.4479999999985, 0],
             'total_adj_nonland_costs':
             [2013754.6, 1246992.0, 178874.28, 148336.552, 140000.0],
             'operator_and_land_return':
             [378286.4000000004, 959433.2580645159,
              101039.31999999998, 108399.02993548391, 10000.0],
             'land_costs':
             [473611.1111111111, 473611.1111111111, 75777.77777777778, 0.0, 0],
             'revenue_based_adjustment_to_land_rent':
             [-15787.037037037036, -15787.037037037036, -2525.925925925926, -0.0, 0],
             'adjusted_land_rent':
             [457824.0740740741, 457824.0740740741, 73251.85185185185, 0.0, 0],
             'owned_land_cost':
             [462962.962962963, 462962.962962963, 74074.07407407407, 0.0, 0],
             'total_land_cost':
             [920787.0370370371, 920787.0370370371, 147325.92592592593, 0.0, 0],
             'total_cost':
             [2934541.637037037, 2167779.0370370373,
              326200.2059259259, 148336.552, 140000.0],
             'pretax_amount':
             [-542500.6370370365, 38646.221027478576,
              -46286.60592592595, 108399.02993548391, 10000.0],
             'adj_land_rent_per_rented_ac':
             [329633.3333333333, 329633.3333333333, 329633.3333333333, 0, 0],
             'owned_land_cost_per_owned_ac':
             [416666.6666666667, 416666.6666666667, 416666.6666666667, 0, 0]}
        }
        self.assertEqual(data, expected)

    def test_budget_with_pf7_yf7(self):
        """
        test the budget with price_factor 0.8 for all market crops and
        yield_factor 0.8 for all farm_budget_crops
        """
        self.farm_year.market_crops.all().update(price_factor=0.7)
        self.farm_year.farmbudgetcrop_set.all().update(yield_factor=0.7)
        mgr = BudgetManager(self.farm_year)
        mgr.build_current_budget()
        data = self.farm_year.current_budget_data
        expected = {
            'revenue':
            {'farm_yields':
             [158.89999999999998, 50.4, 59.49999999999999, 32.199999999999996],
             'planted_acres':
             [2500.0, 2500.0, 400.0, 400.0],
             'production_bushels':
             [397.24999999999994, 126.0, 23.799999999999997, 12.879999999999999],
             'contracted_futures': [90.0, 36.29032258064516, 20.0, 3.709677419354838],
             'uncontracted_futures':
             [307.24999999999994, 89.70967741935485,
              3.799999999999997, 9.170322580645161],
             'contracted_basis_qty': [50.0, 18.14516129032258, 30.0, 1.854838709677419],
             'uncontracted_basis_qty':
             [347.24999999999994, 107.85483870967742,
              -6.200000000000003, 11.025161290322579],
             'avg_fut_contract_prices': [3.5444444444444443, 13.2, 7.1, 13.2],
             'harvest_futures_prices':
             [3.8447499999999994, 8.463, 4.521999999999999, 8.463],
             'avg_basis_contract_prices': [0.1, 0.1, 0.12, 0.1],
             'assumed_basis_on_remaining': [0.1, 0.1, 0.1, 0.1],
             'contracted_futures_revenue':
             [319.0, 479.0322580645161, 142.0, 48.96774193548386],
             'contracted_basis_revenue':
             [5.0, 1.814516129032258, 3.5999999999999996, 0.1854838709677419],
             'total_contracted_revenue':
             [324.0, 480.84677419354836, 145.6, 49.1532258064516],
             'uncontracted_futures_revenue':
             [1181.2994374999996, 759.213, 17.183599999999984, 77.60843999999999],
             'uncontracted_basis_revenue':
             [34.724999999999994, 10.785483870967743,
              -0.6200000000000003, 1.102516129032258],
             'total_uncontracted_revenue':
             [1216.0244374999995, 769.9984838709677,
              16.563599999999983, 78.71095612903224],
             'total_crop_revenue':
             [1540.0244374999995, 1250.845258064516,
              162.16359999999997, 127.86418193548384],
             'realized_price_per_bushel':
             [3.8767134990560095, 9.92734331797235,
              6.813596638655462, 9.92734331797235]},
            'budget':
            {'crop_revenue':
             [1540024.4374999995, 1250845.258064516,
              162163.59999999998, 127864.18193548384, 0],
             'gov_pmt':
             [86297.8448275862, 86297.8448275862,
              13807.655172413793, 13807.655172413793, 0],
             'other_gov_pmts': [0.0, 0.0, 0.0, 0.0, 0],
             'crop_ins_indems': [895775.0, 997650.0, 130328.0, 133172.0, 0],
             'other_revenue': [0.0, 0.0, 0.0, 0.0, 150000.0],
             'gross_revenue': [2522097.282327586, 2334793.102892102,
                               306299.2551724138, 274843.8371078976, 150000.0],
             'fertilizers': [625000.0, 237500.0, 61600.0, 28400.0, 0],
             'pesticides': [307500.0, 185000.0, 10800.0, 26000.0, 0],
             'seed': [325000.0, 210000.0, 20000.0, 23600.0, 0],
             'drying': [85000.0, 10000.0, 400.0, 0.0, 0],
             'storage': [15000.0, 12500.0, 400.0, 400.0, 0],
             'crop_ins_prems': [45800.0, 33950.0, 13540.0, 6595.999999999999, 0],
             'other_direct_costs': [0.0, 0.0, 0.0, 0.0, 0],
             'total_direct_costs': [1403300.0, 688950.0, 106740.0, 84996.0, 0],
             'machine_hire_lease': [50000.0, 45000.0, 7200.0, 8800.0, 0],
             'utilities': [17500.0, 17500.0, 2800.0, 1600.0, 0],
             'machine_repair': [102500.0, 92500.0, 13200.0, 14800.0, 0],
             'fuel_and_oil': [85000.0, 65000.0, 8000.0, 14000.0, 0],
             'light_vehicle': [5000.0, 2500.0, 800.0, 800.0, 0],
             'machine_depreciation': [197500.0, 175000.0, 19600.0, 12800.0, 0],
             'total_power_costs': [457500.0, 397500.0, 51600.0, 52800.0, 0],
             'hired_labor': [62500.0, 55000.0, 9200.0, 7200.0, 0],
             'building_repair_rent': [20000.0, 17500.0, 2400.0, 2400.0, 0],
             'building_depreciation': [35000.0, 30000.0, 4000.0, 2000.0, 0],
             'insurance': [32500.0, 32500.0, 2000.0, 0.0, 0],
             'misc': [32500.0, 32500.0, 4400.0, 0.0, 0],
             'interest_nonland': [50000.0, 45000.0, 5600.0, 4800.0, 0],
             'other_costs': [0.0, 0.0, 0.0, 0.0, 140000.0],
             'total_overhead_costs': [232500.0, 212500.0, 27600.0, 16400.0, 140000.0],
             'total_nonland_costs':
             [2093300.0, 1298950.0, 185940.0, 154196.0, 140000.0],
             'yield_adj_to_nonland_costs':
             [-119318.10000000002, -77937.00000000001,
              -10598.580000000002, -8789.172, 0],
             'total_adj_nonland_costs':
             [1973981.9, 1221013.0, 175341.41999999998, 145406.828, 140000.0],
             'operator_and_land_return':
             [548115.382327586, 1113780.1028921022,
              130957.83517241379, 129437.00910789761, 10000.0],
             'land_costs':
             [473611.1111111111, 473611.1111111111, 75777.77777777778, 0.0, 0],
             'revenue_based_adjustment_to_land_rent':
             [-15787.037037037036, -15787.037037037036, -2525.925925925926, -0.0, 0],
             'adjusted_land_rent':
             [457824.0740740741, 457824.0740740741, 73251.85185185185, 0.0, 0],
             'owned_land_cost':
             [462962.962962963, 462962.962962963, 74074.07407407407, 0.0, 0],
             'total_land_cost':
             [920787.0370370371, 920787.0370370371, 147325.92592592593, 0.0, 0],
             'total_cost':
             [2894768.9370370368, 2141800.0370370373,
              322667.3459259259, 145406.828, 140000.0],
             'pretax_amount':
             [-372671.6547094509, 192993.0658550649,
              -16368.090753512108, 129437.00910789761, 10000.0],
             'adj_land_rent_per_rented_ac':
             [329633.3333333333, 329633.3333333333, 329633.3333333333, 0, 0],
             'owned_land_cost_per_owned_ac':
             [416666.6666666667, 416666.6666666667, 416666.6666666667, 0, 0]}
        }
        self.assertEqual(data, expected)
