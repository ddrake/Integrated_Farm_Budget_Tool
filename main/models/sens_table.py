"""
Module sens_table

Generates sensitivity tables with respect to a range of prices and a range of yields
for a given farm year, for a given variable in {pretax, revenue, cost, title, indem}
and "crops" in {corn, fsbeans, wwheat, swheat, dcbeans, farm, wheatdc}.
depending on farm_crops specified
"""
import numpy as np
from numpy import array, zeros, empty

from main.models.farm_year import FarmYear
from main.models.farm_crop import FarmCrop
from main.models.market_crop import MarketCrop


class SensTable(object):
    def __init__(self, farm_year_id):
        self.farm_year = FarmYear.objects.get(pk=farm_year_id)
        self.farm_crops = [fc for fc in
                           FarmCrop.objects.filter(farm_year_id=farm_year_id)
                           if fc.planted_acres > 0 and fc.has_budget]
        self.market_crops = [mc for mc in
                             MarketCrop.objects.filter(farm_year_id=farm_year_id)
                             if any(fc in self.farm_crops
                                    for fc in mc.farm_crops.all())]
        # price and yield factors
        self.pfrange = array([.5, .6, .7, .8, .9, .95, 1, 1.05,
                              1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7])
        self.yfrange = array([.4, .5, .6, .7, .8, .9, 1, 1.05, 1.1])

        # crop info
        self.croptypes = [fc.farm_crop_type for fc in self.farm_crops]
        self.croptypeids = [ct.pk for ct in self.croptypes]
        self.croptypenames = [str(fc.farm_crop_type)
                              .replace('Winter', 'W').replace('Spring', 'S')
                              for fc in self.farm_crops]
        self.croptypetags = [name.lower().replace(' ', '-')
                             for name in self.croptypenames]
        self.mktcropnames = [str(mc).replace('Winter', 'W').replace('Spring', 'S')
                             for mc in self.market_crops]
        self.acres = [fc.planted_acres for fc in self.farm_crops]
        self.total_acres = sum(self.acres)
        self.is_cash_flow = (self.farm_year.report_type == 1)

        # lengths for layout
        self.nfcs = len(self.farm_crops)
        self.nmcs = len(self.market_crops)
        self.npfs = len(self.pfrange)
        self.nyfs = len(self.yfrange)

        # wheat/dc special case
        self.wheatdcixs = None
        self.wheatdc = False
        if 3 in self.croptypeids and 5 in self.croptypeids:
            self.wheatdcixs = [self.croptypeids.index(id) for id in [3, 5]]
            self.wheatdc = True

        # ensure premiums are set
        for fc in self.farm_crops:
            fc.get_crop_ins_prems()

        # non-sensitized prices, yields
        self.harvest_prices = [fc.harvest_price() for fc in self.farm_crops]
        self.mkt_harvest_prices = [mc.harvest_price() for mc in self.market_crops]
        self.expected_yields = [fc.farm_expected_yield() for fc in self.farm_crops]

        # sensitized price, yield arrays
        self.prices = np.outer(self.pfrange, self.harvest_prices)
        self.mprices = np.outer(self.pfrange, self.mkt_harvest_prices)
        self.yields = np.outer(self.yfrange, self.expected_yields)

        # apportioned gov pmt in dollars
        self.gov_pmts = None

        # computed numeric arrays
        self.revenue_values = None
        self.title_values = None
        self.indem_values = None
        self.cost_values = None
        self.pretaxamt_values = None

        # computed string arrays (same for all sens. tables)
        self.yieldblock = None
        self.priceblock = None
        self.alltables = None
        self.info = None

    def set_gov_pmts(self, pf, yf):
        # set apportioned gov pmt in dollars (optimization)
        totgovpmt = self.farm_year.calc_gov_pmt(pf=pf, yf=yf)
        self.gov_pmts = [totgovpmt * ac / self.total_acres for ac in self.acres]

    def get_info(self):
        if self.info is None:
            names = (['Farm'] + self.croptypenames[:] +
                     (['Wheat/DC Beans'] if self.wheatdc else []))
            tags = [n.lower().replace(' ', '_').replace('/', '_') for n in names]
            self.info = {'nfcs': self.nfcs, 'nmcs': self.nmcs,
                         'spanrows': [0, 1, self.nfcs+1], 'crops': zip(tags, names), }
        return self.info

    def get_all_tables(self):
        """
        Main method
        return a dict with keys like pretax_corn, revenue_farm, title_wheatdc
        and with values nested lists of strings to be rendered as html tables.
        """
        if self.alltables is None:
            rslt = {}
            rslt.update(self.get_formatted(
                'revenue', self.get_revenue_values(), 'REVENUE SENSITIVITY ($000)',
                'Revenue before Indemnity and Title payments'))
            rslt.update(self.get_formatted(
                'title', self.get_title_values(),
                'TITLE PAYMENT SENSITIVITY ($000)', ''))
            rslt.update(self.get_formatted(
                'indem', self.get_indem_values(),
                'INSURANCE PAYMENT SENSITIVITY ($000)', ''))
            rslt.update(self.get_formatted(
                'cost', self.get_cost_values(), 'COST SENSITIVITY ($000)', ''))
            rslt.update(self.get_formatted(
                'pretaxamt', self.get_pretaxamt_values(), 'PROFIT SENSITIVITY ($000)',
                'Pre-Tax Cash Flow' if self.is_cash_flow else 'Pre-Tax Income'))
            self.alltables = rslt
        return self.alltables

    def get_formatted(self, tag, values, title, subtitle):
        """
        Takes a name (e.g. 'revenue'), a 3D values array, a title and subtitle
        Returns a dict with keys (name+'crop') and values nested lists of strings
        (i.e. table rows), where the title is prepended by the 'crop' with crop
        a farm crop or 'farm' or 'wheat/dc'
        """
        names = [n.upper() for n in self.croptypenames]
        names.append('FARM')
        if self.wheatdc:
            names.append('WHEAT/DC BEANS')
        tags = [tag + '_' + n.lower().replace(' ', '_').replace('/', '_')
                for n in names]
        result = {}
        for i, n in enumerate(names):
            full = self.full_block(n, title, subtitle, values[i, ...]).tolist()
            # delete title columns that will be replaced by colspans
            for row in full[:2]:
                del row[1:self.nmcs]
            result[tags[i]] = full
            row = full[self.nfcs+1]
            del row[1:self.nmcs]
        return result

    # --------------------------------------------
    # Construction of table blocks (string arrays)
    # --------------------------------------------
    def full_block(self, crop, title, subtitle, values):
        """
        string array representing the full table
        """
        block = empty((self.nfcs+self.npfs+3, self.nmcs+self.nyfs+1),
                      dtype=object)
        block[:self.nfcs+1, :self.nmcs] = self.title_block(crop, title, subtitle)
        block[:self.nfcs+1, self.nmcs:] = self.yields_block()
        block[self.nfcs+1:, :self.nmcs] = self.prices_block()
        block[self.nfcs+1:, self.nmcs:] = self.sens_block(values)
        return block

    def title_block(self, crop, title, subtitle):
        block = empty((self.nfcs+1, self.nmcs), dtype=object)
        block.fill('')
        block[0, 0] = f'{crop} {title}'
        block[1, 0] = subtitle
        return block

    def yields_block(self):
        if self.yieldblock is None:
            block = np.empty((self.nfcs+1, self.nyfs+1), dtype=object)
            block.fill('')
            block[0, 0] = 'ASSUMED FARM YIELDS'
            block[1:self.nfcs+1, 0] = self.croptypenames
            block[1:self.nfcs+1, 1:] = [list(map('{:.0f}'.format, ll))
                                        for ll in self.yields.T.tolist()]
            self.yieldblock = block
        return self.yieldblock

    def prices_block(self):
        if self.priceblock is None:
            block = np.empty((self.npfs+2, self.nmcs), dtype=object)
            block.fill('')
            block[0, 0] = 'ASSUMED HARVEST PRICES'
            block[1, :] = self.mktcropnames
            block[2:, :] = [list(map('${:.2f}'.format, ll))
                            for ll in self.mprices.tolist()]
            self.priceblock = block
        return self.priceblock

    def sens_block(self, values):
        block = empty((self.npfs+2, self.nyfs+1), dtype=object)
        block.fill('')
        block[0, 0] = 'Price'
        block[0, 1] = 'Yields'
        block[1, 1:] = list(map('{:.0%}'.format, self.yfrange))
        block[2:, 0] = list(map('{:.0%}'.format, self.pfrange))
        lst = values.tolist()
        block[2:, 1:] = [list(map('${:,.0f}'.format, ll)) for ll in lst]
        return block

    # -----------------------------------------------------------------------
    # value getters, each returning a 3D numpy array of values in kilodollars
    # -----------------------------------------------------------------------
    def get_revenue_values(self):
        if self.revenue_values is None:
            other_rev = self.farm_year.other_nongrain_income
            self.revenue_values = self.get_values_array(
                'gross_rev_no_title_indem', noncrop=other_rev,
                kwargs={'is_per_acre': True, 'sprice': None})
        return self.revenue_values

    def get_title_values(self):
        if self.title_values is None:
            self.title_values = self.get_values_array(
                'gov_pmt_portion', kwargs={'is_per_acre': True})
        return self.title_values

    def get_indem_values(self):
        if self.indem_values is None:
            self.indem_values = self.get_values_array('get_total_indemnities')
        return self.indem_values

    def get_cost_values(self):
        if self.cost_values is None:
            other_cost = self.farm_year.other_nongrain_expense
            self.cost_values = self.get_values_array(
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

    def get_values_array(self, methodname, noncrop=0, kwargs={}):
        """
        Computes 3D array of values by calling farm_crop methods to get $/acre values.
        noncrop argument is assumed to be in dollars.
        Returns a block for each crop followed by a total block
        and possibly a wheat/dc block (if we have wheat and dc beans).
        """
        cropct = self.nfcs
        blocks = cropct + (2 if self.wheatdc else 1)
        result = zeros((blocks, len(self.pfrange), len(self.yfrange)))
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
        result[cropct, ...] = result[:cropct, ...].sum(axis=0) + noncrop / 1000
        if self.wheatdc:
            result[-1, ...] = result[self.wheatdcixs, ...].sum(axis=0)
        return result