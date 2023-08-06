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
        self.yfrange = array([.5, .6, .7, .8, .9, .95, 1, 1.05, 1.1])

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

        # lengths for layout
        self.nfcs = len(self.farm_crops)
        self.nmcs = len(self.market_crops)
        self.npfs = len(self.pfrange)
        self.nyfs = len(self.yfrange)
        self.nrows = self.nfcs + self.npfs + 5
        self.ncols = self.nmcs + self.nyfs + 1
        self.yld1 = self.nmcs + self.nyfs - 2
        self.prc1 = self.nfcs + self.npfs - 4

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

        # TODO: once prices are finalized (post next July contract end) we should
        # no longer sensitize them. At that point in time, will sensitivity tables
        # still be of value?
        self.prices = np.outer(self.pfrange, self.harvest_prices)
        self.mprices = np.outer(self.pfrange, self.mkt_harvest_prices)
        # once yields are finalized, we no longer sensitize them
        self.yields = np.array(
            [fc.sens_farm_expected_yield(yf) for yf in self.yfrange
             for fc in self.farm_crops]).reshape(self.nyfs, self.nfcs)

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
        self.info = None
        self.tot_nonland_cost = [fc.total_nonland_costs() for fc in self.farm_crops]
        self.yieldsblock = None
        self.pricesblock = None

    def set_gov_pmts(self, pf, yf):
        # set apportioned gov pmt in dollars (optimization)
        totgovpmt = self.farm_year.calc_gov_pmt(pf=pf, yf=yf)
        self.gov_pmts = [totgovpmt * ac / self.total_acres for ac in self.acres]

    def get_info(self):
        if len(self.farm_crops) == 0:
            return {'farmyear': self.farm_year.pk}
        if self.info is None:
            names = (['Farm'] + self.croptypenames[:] +
                     (['Wheat/DC Beans'] if self.wheatdc else []))
            tags = [n.lower().replace(' ', '_').replace('/', '_') for n in names]
            self.info = {'farmyear': self.farm_year.pk,
                         'crops': zip(tags, names),
                         'hasdiff': self.farm_year.sensitivity_data is not None,
                         }
        return self.info

    def save_sens_data(self):
        alldata = [ar.tolist() for ar in
                   [self.revenue_values, self.title_values, self.indem_values,
                    self.cost_values, self.pretaxamt_values]]
        self.farm_year.sensitivity_data = alldata
        self.farm_year.save()

    def get_all_tables(self):
        """
        Main method
        return a dict with keys like pretax_corn, revenue_farm, title_wheatdc
        and with values nested lists of strings to be rendered as html tables.
        """
        rslt = {}
        if len(self.farm_crops) == 0:
            return None

        self.get_tables(rslt)
        if self.farm_year.sensitivity_data is not None:
            revenue_p, title_p, indem_p, cost_p, pretaxamt_p = (
                np.array(v) for v in self.farm_year.sensitivity_data)
            # if the array shapes have changed, e.g. by setting a crop's acres to zero
            # we can't provide a diff.
            if revenue_p.shape == self.revenue_values.shape:
                self.get_tables(rslt, arrays=(revenue_p, title_p, indem_p,
                                              cost_p, pretaxamt_p))
        self.save_sens_data()
        return rslt

    def get_tables(self, rslt, arrays=None):
        diff = (arrays is not None)
        if diff:
            revenue_p, title_p, indem_p, cost_p, pretaxamt_p = arrays

        items = [
            ['revenue' + ('_diff' if diff else ''),
             (self.revenue_values - revenue_p) if diff else self.get_revenue_values(),
             'REVENUE SENSITIVITY ($000)',
             'Revenue before Indemnity and Title payments'],
            ['title' + ('_diff' if diff else ''),
             (self.title_values - title_p) if diff else self.get_title_values(),
             'TITLE PAYMENT SENSITIVITY ($000)', ''],
            ['indem' + ('_diff' if diff else ''),
             (self.indem_values - indem_p) if diff else self.get_indem_values(),
             'INSURANCE PAYMENT SENSITIVITY ($000)', ''],
            ['cost' + ('_diff' if diff else ''),
             (self.cost_values - cost_p) if diff else self.get_cost_values(),
             'COST SENSITIVITY ($000)', ''],
            ['pretaxamt' + ('_diff' if diff else ''),
             (self.pretaxamt_values - pretaxamt_p) if diff else
             self.get_pretaxamt_values(),
             'PROFIT SENSITIVITY ($000)', 'Pre-Tax Cash Flow']]
        for args in items:
            rslt.update(self.get_formatted(*args))

    def add_styles(self, table):
        bkg = ' bg-slate-100'
        bkggrn = ' bg-green-100'
        bkgred = ' bg-red-100'
        bord = ' border border-black'
        bordx = ' border-x border-black'
        bordy = ' border-y border-black'
        bordt = ' border-t border-black'
        bordb = ' border-b border-black'
        bordl = ' border-l border-black'
        bordr = ' border-r border-black'
        bold = ' font-bold'
        left = ' text-left'
        right = ' text-right'
        center = ' text-center'
        under = ' underline'
        # Titles
        table[:2, 0, 2] += left+bold
        # Assumed farm yields block
        table[2, self.nmcs, 2] += center+bold+bord  # 'Assumed Farm Yields'
        table[3:self.nfcs+3, self.nmcs, 2] += left+bold+bordl
        table[3:self.nfcs+3, self.nmcs+1:, 2] += right
        table[3:self.nfcs+3, -1, 2] += bordr
        table[3:self.nfcs+3, self.yld1, 2] += bordx+bkg+bold
        table[self.nfcs+2, self.nmcs:, 2] += bordb
        table[self.nfcs+4:, self.yld1, 2] += bordx
        # Yield Bracket
        table[3:self.nfcs+3, self.yld1-2, 2] += bordl
        # Assumed harvest prices block
        table[self.nfcs+3, 0, 2] += center+bold+bord
        table[self.nfcs+4, self.nmcs, 2] += bordl
        table[self.nfcs+4, :self.nmcs, 2] += right+under+bold
        table[self.nfcs+5:self.nfcs+5+self.npfs, :self.nmcs, 2] += right
        table[self.prc1, :self.nmcs+1, 2] += bordy+bkg+bold
        table[self.prc1, self.nmcs+1:, 2] += bordy
        # Price Bracket
        table[self.prc1-2, :self.nmcs, 2] += bordt
        table[self.prc1+2, :self.nmcs, 2] += bordb
        # Base value
        table[self.prc1, self.yld1, 2] += bord+bold
        # Base value bracket
        table[self.prc1-2, self.yld1-2:, 2] += bordt
        table[self.prc1+2, self.yld1-2:, 2] += bordb
        table[self.prc1-2:self.prc1+3, self.yld1-2, 2] += bordl

        # Yield %
        table[self.nfcs+4, self.nmcs+1:, 2] += bordy+bold
        table[self.nfcs+4, self.nmcs+1, 2] += bordl
        table[self.nfcs+4, self.yld1, 2] += bkg
        # Price %
        table[self.nfcs+5:, self.nmcs, 2] += bordx+bold
        table[self.nfcs+5, self.nmcs, 2] += bordt+bold

        # Sensitized values
        def isneg(s):
            return s.startswith('-')
        visneg = np.vectorize(isneg)
        table[self.nfcs+5:, self.nmcs+1:, 2] += np.where(
            visneg(table[self.nfcs+5:, self.nmcs+1:, 0]), bkgred, bkggrn)
        table[self.nfcs+5:, self.nmcs+1:, 2] += right

    def add_spans(self, table):
        table[0, 0, 1] = str(self.ncols)             # title
        table[1, 0, 1] = str(self.ncols)             # subtitle
        table[2, self.nmcs, 1] = str(self.nyfs+1)    # 'Assumed farm yields'
        table[self.nfcs+3, 0, 1] = str(self.nmcs)    # 'Assumed harvest prices'

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
            maintitle = f'{n} {title}'
            full = self.full_block(n, values[i, ...], maintitle, subtitle)
            self.add_spans(full)
            self.add_styles(full)
            full = full.tolist()
            # delete columns which will be spanned over
            for row in full[:2]:
                del row[1:self.ncols]
            row = full[2]
            del row[self.nmcs+1:]
            row = full[self.nfcs+3]
            del row[1:self.nmcs]

            result[tags[i]] = full
        return result

    # --------------------------------------------
    # Construction of table blocks (string arrays)
    # --------------------------------------------
    def full_block(self, crop, values, title, subtitle):
        """
        string array representing the full table
        with third dimension: [value, span, style]
        """
        block = np.full((self.nrows, self.ncols, 3), '', dtype=object)
        block[:3, :, 0] = self.title_block(title, subtitle)
        block[3:self.nfcs+3, self.nmcs:, 0] = self.yields_block()
        block[self.nfcs+3:, :self.nmcs, 0] = self.prices_block()
        block[self.nfcs+3:, self.nmcs:, 0] = self.sens_block(values)
        return block

    def title_block(self, title, subtitle):
        block = np.full((3, self.ncols), '', dtype=object)
        block[0, 0] = title
        block[1, 0] = subtitle
        block[2, self.nmcs] = 'ASSUMED FARM YIELDS'
        return block

    def yields_block(self):
        if self.yieldsblock is None:
            block = np.full((self.nfcs, self.nyfs+1), '',  dtype=object)
            block.fill('')
            block[:self.nfcs, 0] = self.croptypenames
            block[:self.nfcs, 1:] = [list(map('{:.0f}'.format, ll))
                                     for ll in self.yields.T.tolist()]
            self.yieldsblock = block
        return self.yieldsblock

    def prices_block(self):
        if self.pricesblock is None:
            block = np.full((self.npfs+2, self.nmcs), '', dtype=object)
            block[0, 0] = 'ASSUMED HARVEST PRICES'
            block[1, :] = self.mktcropnames[:]
            block[2:, :] = [list(map('${:.2f}'.format, ll))
                            for ll in self.mprices.tolist()]
            self.pricesblock = block
        return self.pricesblock

    def sens_block(self, values):
        block = np.full((self.npfs+2, self.nyfs+1), '', dtype=object)
        # Maybe not necessary
        # block[0, 0] = 'Price'
        # block[0, 1] = 'Yields'
        block[1, 1:] = list(map('{:.0%}'.format, self.yfrange))
        block[2:, 0] = list(map('{:.0%}'.format, self.pfrange))
        lst = values.tolist()
        block[2:, 1:] = [list(map('{:,.0f}'.format, ll)) for ll in lst]
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
            self.title_values = self.get_values_array('gov_pmt_portion')
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
                kwargs={'sprice': None})
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
                    self.set_gov_pmts([pf]*3, [yf]*3)
                for i, (crop, acres) in enumerate(zip(self.farm_crops, self.acres)):
                    if methodname == 'gov_pmt_portion':
                        result[i, j, k] = self.gov_pmts[i] / 1000
                    elif methodname == 'total_cost':
                        result[i, j, k] = (
                            crop.total_cost(
                                pf=pf, yf=yf,
                                tot_nonland_cost=self.tot_nonland_cost[i], **kwargs)
                            * acres / 1000)
                    else:
                        if 'sprice' in kwargs:
                            kwargs['sprice'] = self.prices[j, i]
                        value = (getattr(crop, methodname)(pf=pf, yf=yf, **kwargs))
                        result[i, j, k] = value * acres / 1000
        result[cropct, ...] = result[:cropct, ...].sum(axis=0) + noncrop / 1000
        if self.wheatdc:
            result[-1, ...] = result[self.wheatdcixs, ...].sum(axis=0)
        return result
