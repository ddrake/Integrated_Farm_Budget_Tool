"""
Module sens_table

Generates sensitivity tables with respect to a range of prices and a range of yields
for a given farm year, for a given variable in {pretax, revenue, cost, title, indem}
and "crops" in {corn, fsbeans, wwheat, swheat, dcbeans, farm, wheatdc}.
depending on farm_crops specified
"""
import numpy as np
from numpy import array, zeros

from main.models.farm_year import FarmYear
from main.models.farm_crop import FarmCrop


class SensTable(object):
    def __init__(self, farm_year_id):
        self.farm_year = FarmYear.objects.get(farm_year_id)
        self.farm_crops = [fc for fc in
                           FarmCrop.objects.filter(farm_year_id=farm_year_id)
                           if fc.planted_acres > 0 and fc.has_budget]
        self.farm_crop_types = [fc.farm_crop_type for fc in self.farm_crops]
        self.pfrange = array([.5, .6, .7, .8, .9, .95, 1, 1.05,
                              1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7])
        self.yfrange = array([.4, .5, .6, .7, .8, .9, 1, 1.05, 1.1])
        self.is_cash_flow = (self.farm_year.report_type == 1)
        self.croptype = {1: 'corn', 2: 'fsbeans', 3: 'wwheat',
                         4: 'swheat', 5: 'wheatdc'}
        self.croptypes = [fc.farm_crop_type for fc in self.farm_crops]
        self.croptypeids = [ct.pk for ct in self.croptypes]
        self.wheatdcixs = None
        self.wheatdc = False
        if 3 in self.croptypeids and 5 in self.croptypeids:
            self.wheatdcixs = [self.croptypeids.index(id) for id in [3, 5]]
            self.wheatdc = True
        for fc in self.farm_crops:
            fc.get_crop_ins_prems()
        # non-sensitized prices
        self.harvest_prices = [fc.harvest_price() for fc in self.farm_crops]
        self.expected_yields = [fc.farm_expected_yield() for fc in self.farm_crops]
        self.set_yields()
        self.set_prices()

    def calc_gov_pmt(self):
        self.farm_year.calc_gov_pmt()

    def set_yields(self):
        self.yields = np.outer(self.pfange, self.expected_yields)

    def set_prices(self):
        self.prices = np.outer(self.yfrange, self.harvest_prices)

    def get_all_tables(self):
        """
        return a dict with keys like pretax_corn, revenue_farm, title_wheatdc
        """
        rslt = {}
        rslt.update(self.get_pretaxamt_tables())
        rslt.update(self.get_revenue_tables())
        rslt.update(self.get_cost_tables())
        rslt.update(self.get_title_tables())
        rslt.update(self.get_indem_tables())
        return rslt

    # -----------------------------------------------------------------------------
    # table getters, each returning a nested list of formatted strings representing
    # the rows and columns of a sensitivity table
    # -----------------------------------------------------------------------------
    def get_pretaxamt_tables(self):
        """
        Get revenue tables as a dict with values nested lists of strings
        representing table rows for all "crops"
        """
        values = self.get_pretaxamt_values()
        fmt = self.get_formatted(values)
        return fmt

    def get_revenue_tables(self):
        """
        Get revenue tables as a dict with values nested lists of strings
        representing table rows for all "crops"
        """
        values = self.get_revenue_values()
        fmt = self.get_formatted(values)
        return fmt

    def get_cost_tables(self):
        """
        Get cost tables (total cost)
        """
        values = self.get_cost_values()
        fmt = self.get_formatted(values)
        return fmt

    def get_title_tables(self):
        """
        Get title (PLC/ARC) tables
        """
        values = self.get_title_values()
        fmt = self.get_formatted(values)
        return fmt

    def get_indem_tables(self):
        """
        Get crop insurance indemnity tables
        """
        values = self.get_indem_values()
        fmt = self.get_formatted(values)
        return fmt

    # -----------------------------------------------------------------------
    # value getters, each returning a 3D numpy array of values in kilodollars
    # -----------------------------------------------------------------------
    def get_pretaxamt_values(self):
        methodname = 'pretax_cash_flow' if self.is_cash_flow else 'pretax_income'
        return self.get_values_table(methodname, isprop=False, noncrop=None,
                                     selfmethod=None)

    def get_revenue_values(self):
        return self.get_values_table('gross_rev_no_title_indem', isprop=False,
                                     noncrop=None, selfmethod=None)

    def get_cost_values(self):
        return self.get_values_table('total_cost', isprop=False,
                                     noncrop=None, selfmethod=None)

    def get_title_values(self):
        return self.get_values_table('gov_pmt_portion', isprop=False, noncrop=None,
                                     selfmethod='calc_gov_pmt')

    def get_indem_values(self):
        return self.get_values_table('get_total_indemnities', isprop=False,
                                     noncrop=None, selfmethod=None)

    def get_values_table(self, methodname, isprop=False, noncrop=None, selfmethod=None):
        """
        A block for each crop followed by a total block and possibly a wheat/dc block
        """
        cropct = len(self.farm_crops) + 2 if self.wheatdc else 1
        result = zeros(cropct, (len(self.pfrange), len(self.yfrange)))
        for i, crop in enumerate(self.farm_crops):
            for j, pf in enumerate(self.pfrange):
                for k, yf in enumerate(self.yfrange):
                    if selfmethod is not None:
                        getattr(self, selfmethod)()
                    result[i, j, k] = (getattr(crop, methodname) if isprop else
                                       getattr(crop, methodname)(pf, yf))
        result[cropct, ...] = result[:cropct, ...].sum() + sum(noncrop)
        if self.wheatdc:
            result[cropct+1, ...] = result[self.wheatdcixs, ...].sum()
        return result
