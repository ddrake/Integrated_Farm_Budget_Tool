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
        self.farm_year = FarmYear.objects.get(pk=farm_year_id)
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
        self.acres = [fc.planted_acres for fc in self.farm_crops]
        self.total_acres = sum(self.acres)
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
        self.prices = np.outer(self.pfrange, self.harvest_prices)
        self.yields = np.outer(self.yfrange, self.expected_yields)
        # gov pmt in dollars
        self.gov_pmt = None

        # computed arrays
        self.revenue_values = None
        self.title_values = None
        self.indem_values = None
        self.cost_values = None
        self.pretaxamt_values = None

    def set_gov_pmts(self, pf, yf):
        # set apportioned gov pmt in dollars
        totgovpmt = self.farm_year.calc_gov_pmt(pf=pf, yf=yf)
        self.gov_pmts = [totgovpmt * ac / self.total_acres
                         for ac in self.acres]

    def get_all_tables(self):
        """
        return a dict with keys like pretax_corn, revenue_farm, title_wheatdc
        """
        rslt = {}
        rslt.update(self.get_revenue_tables())
        rslt.update(self.get_title_tables())
        rslt.update(self.get_indem_tables())
        rslt.update(self.get_cost_tables())
        rslt.update(self.get_pretaxamt_tables())
        return rslt

    # -----------------------------------------------------------------------------
    # table getters, each returning a nested list of formatted strings representing
    # the rows and columns of a sensitivity table
    # -----------------------------------------------------------------------------
    def get_revenue_tables(self):
        """
        Get revenue tables as a dict with values nested lists of strings
        representing table rows for all "crops"
        """
        values = self.get_revenue_values()
        fmt = self.get_formatted('revenue', values)
        return fmt

    def get_title_tables(self):
        """
        Get title (PLC/ARC) tables
        """
        values = self.get_title_values()
        fmt = self.get_formatted('title', values)
        return fmt

    def get_indem_tables(self):
        """
        Get crop insurance indemnity tables
        """
        values = self.get_indem_values()
        fmt = self.get_formatted('indem', values)
        return fmt

    def get_cost_tables(self):
        """
        Get cost tables (total cost)
        """
        values = self.get_cost_values()
        fmt = self.get_formatted('cost', values)
        return fmt

    def get_pretaxamt_tables(self):
        """
        Get revenue tables as a dict with values nested lists of strings
        representing table rows for all "crops"
        """
        values = self.get_pretaxamt_values()
        fmt = self.get_formatted('pretaxamt', values)
        return fmt

    def get_formatted(self, name, values):
        pass

    # -----------------------------------------------------------------------
    # value getters, each returning a 3D numpy array of values in kilodollars
    # -----------------------------------------------------------------------
    def get_revenue_values(self):
        if self.revenue_values is None:
            other_rev = self.farm_year.other_nongrain_income
            self.revenue_values = self.get_values_table(
                'gross_rev_no_title_indem', noncrop=other_rev,
                kwargs={'is_per_acre': True, 'sprice': None})
        return self.revenue_values

    def get_title_values(self):
        if self.title_values is None:
            self.title_values = self.get_values_table(
                'gov_pmt_portion', kwargs={'is_per_acre': True})
        return self.title_values

    def get_indem_values(self):
        if self.indem_values is None:
            self.indem_values = self.get_values_table('get_total_indemnities')
        return self.indem_values

    def get_cost_values(self):
        if self.cost_values is None:
            other_cost = self.farm_year.other_nongrain_expense
            self.cost_values = self.get_values_table(
                'total_cost', noncrop=other_cost,
                kwargs={'is_cash_flow': self.is_cash_flow,
                        'sprice': None, 'bprice': None})
        return self.cost_values

    def get_pretaxamt_values(self):
        if self.pretaxamt_values is None:
            self.pretaxamt_values = (self.get_revenue_values() +
                                     self.get_title_values() +
                                     self.get_indem_values() - self.get_cost_values())
        return self.pretaxamt_values

    def get_values_table(self, methodname, noncrop=0, kwargs={}):
        """
        Computes values by calling farm_crop methods to get $/acre values.
        noncrop argument is assumed to be in dollars.
        Returns a block for each crop followed by a total block
        and possibly a wheat/dc block (if we have wheat and dc beans).
        """
        cropct = len(self.farm_crops) + (2 if self.wheatdc else 1)
        result = zeros((cropct, len(self.pfrange), len(self.yfrange)))
        for j, pf in enumerate(self.pfrange):
            for k, yf in enumerate(self.yfrange):
                if methodname == 'gov_pmt_portion':
                    self.set_gov_pmts(pf, yf)
                for i, (crop, acres) in enumerate(zip(self.farm_crops, self.acres)):
                    if methodname == 'gov_pmt_portion':
                        value = self.gov_pmts[i] / 1000
                    else:
                        if 'sprice' in kwargs:
                            kwargs['sprice'] = self.prices[j, i]
                        if 'bprice' in kwargs:
                            kwargs['bprice'] = self.harvest_prices[i]
                        value = (getattr(crop, methodname)(pf=pf, yf=yf, **kwargs))
                    result[i, j, k] = value * acres / 1000
        result[cropct-1, ...] = result[:cropct-1, ...].sum(axis=0) + noncrop / 1000
        if self.wheatdc:
            result[cropct, ...] = result[self.wheatdcixs, ...].sum(axis=0)
        return result
