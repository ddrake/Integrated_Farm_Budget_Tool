"""
Module sens_table

Generates sensitivity tables with respect to a range of prices and a range of yields
for a given farm year, for a given variable in {pretax, revenue, cost, title, indem}
and "crops" in {corn, fsbeans, wwheat, swheat, dcbeans, farm, wheatdcbeans}.
depending on farm_crops specified
"""
import numpy as np
from numpy import array, zeros

from main.models.farm_crop import FarmCrop
from main.models.market_crop import MarketCrop


class SensTableGroup(object):
    """
    Computes instance variable self.data, the table of sensitized values.
    Computes price and yield values to be used in row and column headers.
    Manages database caching
    Uses SensTable instances to generate a dict of formatted text sensitivity tables
    """
    def __init__(self, farm_year):
        self.farm_year = farm_year
        # farm crop related info
        self.farm_crops = [fc for fc in
                           FarmCrop.objects.filter(farm_year=farm_year)
                           if fc.planted_acres > 0 and fc.has_budget()]
        self.croptypes = [fc.farm_crop_type for fc in self.farm_crops]
        self.croptypeids = [ct.pk for ct in self.croptypes]
        self.croptypenames = [str(fc.farm_crop_type)
                              .replace('Winter', 'W').replace('Spring', 'S')
                              for fc in self.farm_crops]
        self.croptypetags = [name.lower().replace(' ', '')
                             for name in self.croptypenames]
        self.crop_indices = {name: i for i, name in enumerate(self.croptypetags)}

        self.nfcs = len(self.farm_crops)

        # wheat/dc special case
        self.wheatdcixs = None
        self.wheatdc = False
        if 3 in self.croptypeids and 5 in self.croptypeids:
            self.wheatdcixs = [self.croptypeids.index(id) for id in [3, 5]]
            self.wheatdc = True

        # market crop related info
        self.market_crops = [mc for mc in
                             MarketCrop.objects.filter(farm_year=self.farm_year)
                             if any(fc in self.farm_crops
                                    for fc in mc.farm_crops.all())]

        self.mktcropnames = [str(mc).replace('Winter', 'W').replace('Spring', 'S')
                             for mc in self.market_crops]

        self.acres = [fc.planted_acres for fc in self.farm_crops]
        self.total_acres = sum(self.acres)

        # price and yield factors
        self.pfrange = array([.5, .6, .7, .8, .9, .95, 1, 1.05,
                              1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7])
        self.yfrange = array([.5, .6, .7, .8, .9, .95, 1, 1.05, 1.1])

        self.nincr = 5  # the number of increments (should be odd)
        self.basis_incr = self.farm_year.basis_increment
        self.nst = (self.nincr - 1)//2
        self.bfrange = (None if self.basis_incr == 0 else
                        np.arange(-self.nst, self.nst+1) * self.basis_incr)

        # 3d array of apportioned gov pmt in dollars
        self.gov_pmts = None

        # computed numeric arrays
        self.revenue_values = None
        self.title_values = None
        self.indem_values = None
        self.cost_values = None
        self.cashflow_values = None

        # show all fsa crops for both yield and price blocks
        self.fsa_crops = list(self.farm_year.fsa_crops.all())
        self.fsacropnames = [str(fsac) for fsac in self.fsa_crops]

        # sensitized and non-sensitized prices, yields
        self.harvest_prices = [fc.harvest_price() for fc in self.farm_crops]
        self.mkt_harvest_prices = [mc.harvest_price() for mc in self.market_crops]

        self.prices = np.outer(self.pfrange, self.harvest_prices)
        self.mprices = np.outer(self.pfrange, self.mkt_harvest_prices)

        self.mya_prices = np.array([[fc.sens_mya_price(pf) for pf in self.pfrange]
                                    for fc in self.fsa_crops])
        self.mya_pcts = (self.mya_prices /
                         self.mya_prices[:, 6].reshape(len(self.mya_prices), 1))

        self.yields = np.array([fc.sens_farm_expected_yield(self.yfrange)
                                for fc in self.farm_crops])

        self.cty_yields = np.array([fc.cty_expected_yield(self.yfrange)[0]
                                    for fc in self.fsa_crops])

        self.has_diffs = None
        self.info = None

    def get_farm_crop_idx(self, crop):
        return self.crop_indices[crop]

    def get_crop_idx(self, crop):
        return (-2 if crop == 'farm' and self.wheatdc else
                -1 if crop == 'farm' else
                -1 if crop == 'wheatdcbeans' else
                self.get_farm_crop_idx(crop))

    def get_cashflow_farm(self):
        """
        This is the new 'main' non-ajax method.
        It computes current data and diff and stores both in the database.
        It also generates the cashflow table, stores its text
        in the database for sens_pdf and returns its text.
        """
        if len(self.farm_crops) == 0:
            return None
        self.set_all_data()
        return self.get_selected_table(
            'cashflow', 'farm', (None if self.basis_incr == 0 else self.nst))

    def get_selected_table(self, tbltype, crop, tblnum, isdiff=False):
        """
        Generate a specific table by the user's selections.

        tbltype is in {'cashflow', 'revenue', 'title', 'indem', 'cost'},
        isdiff is a boolean
        crop is enumerated in self.croptype_tag and is
          in {'farm', 'corn', 'fsbeans', 'dcbeans', 'wwheat', 'swheat','wheatdcbeans'}
        tblnum is None or a zero based integer 0..nincr

        It computes no data.  If it's a diff table, it uses the stored diff data.
        Otherwise it uses the stored current data.

        It saves its sensitivity text for sens_pdf
        """
        crop = crop.replace('_', '')
        revenue, title, indem, cost, cashflow = (
            np.array(v) for v in (
                self.farm_year.sensitivity_diff if isdiff else
                self.farm_year.sensitivity_data))
        data = (revenue if tbltype == 'revenue' else cost if tbltype == 'cost' else
                title if tbltype == 'title' else indem if tbltype == 'indem' else
                cashflow)
        table = self.get_table(data, tbltype, crop, tblnum, isdiff)

        self.save_sens_text(table)

        # delete spanned columns for html, but not for pdf
        cs = self.get_class(tbltype, crop)
        cs(self).delete_spanned_cols(table)

        return table

    def get_class(self, tbltype, crop):
        return (SensTableTitle if tbltype == 'title' else
                SensTableStdFarm if crop == 'farm' else
                SensTableStdWheatDC if crop == 'wheatdcbeans' else
                SensTableStdCrop)

    def get_table(self, data, tbltype, crop, tblnum, isdiff):
        """
        Get the table with specified data
        """
        dt = (data[...] if self.basis_incr == 0 else
              data[..., tblnum] if self.basis_incr > 0 and
              tbltype in ['revenue', 'cashflow'] else
              data[..., 0])
        if tbltype == 'revenue':
            info = [dt, 'REVENUE SENSITIVITY ($000)',
                    'Revenue before Indemnity and Title payments']
        elif tbltype == 'title':
            info = [dt, 'TITLE PAYMENT SENSITIVITY ($000)', '']
        elif tbltype == 'indem':
            info = [dt, 'INSURANCE PAYMENT SENSITIVITY ($000)', '']
        elif tbltype == 'cost':
            info = [dt, 'COST SENSITIVITY ($000)', '']
        else:
            info = [dt, 'PROFIT SENSITIVITY ($000)', 'Pre-Tax Cash Flow']

        return self.get_table_for_info(info, tbltype, crop)

    def get_table_for_info(self, info, tbltype, crop):
        """ get the set of tables for a specific item """
        data, title, subtitle = info
        cs = self.get_class(tbltype, crop)
        ix = self.get_crop_idx(crop)
        titlecrop = ('WHEAT/DC BEANS' if crop == 'wheatdcbeans' else
                     'FARM' if crop == 'farm' else self.croptypenames[ix].upper())
        title = (f"{titlecrop} {title}")
        st = cs(self)
        return st.get_formatted(data[ix], crop, title, subtitle)

    def get_info(self):
        """
        Return a dict with info for populating drop-downs, etc in the template.
        """
        if len(self.farm_crops) == 0:
            return {'farmyear': self.farm_year.pk}
        if self.info is None:
            names = (['Farm'] + self.croptypenames[:] +
                     (['Wheat/DC Beans'] if self.wheatdc else []))
            tags = [n.lower().replace(' ', '').replace('/', '') for n in names]
            self.info = {'farmyear': self.farm_year.pk,
                         'crops': zip(tags, names),
                         'hasdiff': self.has_diffs,
                         }
            self.info['nincr'] = 0 if self.bfrange is None else self.nincr
            self.info['basis_incr'] = 0 if self.bfrange is None else self.basis_incr
        return self.info

    # ----------------
    # DATA COMPUTATION
    # ----------------
    def set_all_data(self):
        """
        Compute current data and diffs if possible, saving both current data and
        diff data to the database.
        """
        alldata = self.compute_current_data()
        if self.farm_year.sensitivity_data is not None:
            self.farm_year.sensitivity_diff = self.compute_diff_data()
        self.farm_year.sensitivity_data = alldata
        self.farm_year.save()

    def compute_current_data(self, save=False):
        """
        Compute all the data needed into a nested list which can optionally
        be saved here.   We only want to save if testing.
        """
        self.set_gov_pmts()
        self.revenue_values = self.get_revenue_values()
        self.title_values = self.get_title_values()
        self.indem_values = self.get_indem_values()
        self.cost_values = self.get_cost_values()
        self.cashflow_values = self.get_cashflow_values()
        alldata = [ar.tolist() for ar in
                   [self.revenue_values, self.title_values, self.indem_values,
                    self.cost_values, self.cashflow_values]]
        if save:
            self.farm_year.sensitivity_data = alldata
            self.farm_year.save()
        return alldata

    def compute_diff_data(self):
        """
        Collect all the diffs
        """
        revenue_p, title_p, indem_p, cost_p, cashflow_p = (
            np.array(v) for v in self.farm_year.sensitivity_data)

        if revenue_p.shape == self.revenue_values.shape:
            self.has_diffs = True
            revenue_d = self.revenue_values - revenue_p
            title_d = self.title_values - title_p
            indem_d = self.indem_values - indem_p
            cost_d = self.cost_values - cost_p
            cashflow_d = self.cashflow_values - cashflow_p
            return [ar.tolist() for ar in
                    [revenue_d, title_d, indem_d, cost_d, cashflow_d]]
        else:
            self.has_diffs = False
            return None

    def save_sens_text(self, rslt):
        """ Save the the currently selected text table to the database """
        self.farm_year.sensitivity_text = rslt
        self.farm_year.save()

    def set_gov_pmts(self):
        """ set apportioned gov pmt in dollars (optimization)
            array(np, ny)
        """
        totgovpmt = self.farm_year.calc_gov_pmt(mya_prices=self.mya_prices,
                                                cty_yields=self.cty_yields)
        self.gov_pmts = np.array([totgovpmt * ac / self.total_acres
                                  for ac in self.acres])

    # -----------------------------------------------------------------------
    # return cached value or compute a 3D numpy array of values in kilodollars
    # array(nc+, np, ny) or array(nc+, np, ny, nb)
    def get_revenue_values(self):
        other_rev = self.farm_year.other_nongrain_income
        self.revenue_values = self.get_values_array('revenue', noncrop=other_rev)
        return self.revenue_values

    def get_title_values(self):
        self.title_values = self.get_values_array('gov_pmt')
        return self.title_values

    def get_indem_values(self):
        self.indem_values = self.get_values_array('indemnity')
        return self.indem_values

    def get_cost_values(self):
        other_cost = self.farm_year.other_nongrain_expense
        self.cost_values = self.get_values_array('cost', noncrop=other_cost)
        return self.cost_values

    def get_cashflow_values(self):
        self.cashflow_values = (self.revenue_values + self.title_values +
                                self.indem_values - self.cost_values)
        return self.cashflow_values

    def get_values_array(self, name, noncrop=0, kwargs={}):
        """
        Computes 3D array of values by calling farm_crop methods to get $/acre values.
        noncrop argument is assumed to be in dollars.
        Returns a block for each crop followed by a total block
        and possibly a wheat/dc block (if we have wheat and dc beans).
        """
        nobf = self.bfrange is None
        cropct = self.nfcs
        blocks = cropct + (2 if self.wheatdc else 1)
        npf, nyf = len(self.pfrange), len(self.yfrange)
        result = (zeros((blocks, npf, nyf)) if nobf else
                  zeros((blocks, npf, nyf, len(self.bfrange))))
        for i, (crop, acres) in enumerate(zip(self.farm_crops, self.acres)):
            if name == 'gov_pmt':
                result[i, ...] = (self.gov_pmts[i] if nobf else
                                  self.gov_pmts[i].reshape(15, 9, 1)) / 1000
            elif name == 'cost':
                result[i, ...] = ((crop.total_cost(
                    pf=self.pfrange, yf=self.yfrange) if nobf else
                                   crop.total_cost(
                    pf=self.pfrange, yf=self.yfrange).reshape(15, 9, 1)) * acres / 1000)
            elif name == 'indemnity':
                result[i, ...] = ((crop.get_total_indemnities(
                    pf=self.pfrange, yf=self.yfrange) if nobf else
                                   crop.get_total_indemnities(
                    pf=self.pfrange, yf=self.yfrange).reshape(15, 9, 1)) * acres / 1000)
            elif name == 'revenue':
                if self.bfrange is None:
                    result[i, ...] = (
                        crop.gross_rev_no_title_indem(
                            pf=self.pfrange, yf=self.yfrange) / 1000)
                else:
                    result[i, ...] = (
                        crop.gross_rev_no_title_indem(
                            pf=self.pfrange, yf=self.yfrange, bf=self.bfrange) / 1000)
            else:
                raise ValueError('Unexpected methodname')

            # add total column with noncrop value if any
            result[cropct, ...] = result[:cropct, ...].sum(axis=0) + noncrop / 1000

            # add wheatdc column if we have wheat and dc beans
            if self.wheatdc:
                result[-1, ...] = result[self.wheatdcixs, ...].sum(axis=0)
        return result


# ###################################################################################
# SENSTABLES --- FORMATTING
# BASE CLASS
# ###################################################################################
class SensTable(object):
    def __init__(self, grp):
        """
        Takes general and table-specific data for a single sensitivity table
        Generates str values, spans and styles for a single sensitivity table, with
        given SensTableGroup, title, and subtitle in instance variable self.table.
        If prev is provided, its values are subtracted from numerical values in
        self.data to display difference from previous run.
        """
        self.grp = grp
        self.farm_year = grp.farm_year
        self.farm_crops = grp.farm_crops
        # crop info
        self.croptypes = grp.croptypes
        self.croptypeids = grp.croptypeids
        self.croptypenames = grp.croptypenames
        self.croptypetags = grp.croptypetags
        self.crop_indices = grp.crop_indices
        # wheat/dc special case
        self.wheatdcixs = grp.wheatdcixs
        self.wheatdc = grp.wheatdc
        # market crop info
        self.market_crops = grp.market_crops
        self.mktcropnames = grp.mktcropnames
        self.mkt_harvest_prices = grp.mkt_harvest_prices
        # array of sensitized market prices for most price blocks
        self.mprices = grp.mprices

        self.acres = grp.acres
        self.total_acres = grp.total_acres
        # price and yield factors
        self.pfrange = grp.pfrange
        self.yfrange = grp.yfrange
        # fsa_crops
        self.fsa_crops = grp.fsa_crops
        self.fsacropnames = grp.fsacropnames
        # sensitized price arrays needed for title price block
        self.mya_prices = grp.mya_prices.T
        self.mya_pcts = grp.mya_pcts.T
        self.mya_pricepcts = np.zeros((len(self.pfrange), len(self.fsa_crops)*2))
        self.mya_pricepcts[:, 0::2] = self.mya_prices
        self.mya_pricepcts[:, 1::2] = self.mya_pcts
        # sensitized yields needed for yield block
        self.yields = grp.yields
        # needed for title yield block
        self.cty_yields = grp.cty_yields
        # for selecting price column based on crop
        self.mcidx_for_fc = [self.market_crops.index(fc.market_crop)
                             for fc in self.farm_crops]

    def get_farm_crop_idx(self, crop):
        return self.crop_indices[crop]

    def add_styles(self, table):
        """
        This method is overridden in SensTitle
        """
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
        table[2, self.nmcs, 2] += center+bold+bordl  # 'Assumed Farm Yields'
        table[2, self.nmcs:, 2] += bordy
        table[3:self.nfcs+3, self.nmcs, 2] += left+bold+bordl
        table[3:self.nfcs+3, self.nmcs+1:, 2] += right
        table[3:self.nfcs+3, -1, 2] += bordr
        table[3:self.nfcs+3, self.yld1, 2] += bordx+bkg+bold
        table[self.nfcs+2, self.nmcs:, 2] += bordb
        table[self.nfcs+4:, self.yld1, 2] += bordx
        # Yield Bracket
        table[3:self.nfcs+3, self.yld1-2, 2] += bordl
        # Assumed harvest prices block
        table[self.nfcs+3, 0, 2] += center+bold
        table[self.nfcs+3, :self.nmcs, 2] += bordy
        table[self.nfcs+3:self.nfcs+5, self.nmcs, 2] += bordl
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

        # De-duplicate style strings
        rs, cs, _ = table.shape
        for r in range(rs):
            for c in range(cs):
                table[r, c, 2] = ' '.join(list(set(table[r, c, 2].split())))

    def delete_spanned_cols(self, full):
        """
        This method is overridden in SensTitle
        Given the full table as nested list, delete spanned colums
        """
        for row in full[:2]:
            del row[1:self.ncols]
        row = full[2]
        del row[self.nmcs+1:]
        row = full[self.nfcs+3]
        del row[1:self.nmcs]


# @@@@@@@@@@@@@@@@@@@@@@@@
# STD CROP
# @@@@@@@@@@@@@@@@@@@@@@@@
class SensTableStdCrop(SensTable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nfcs = 1
        self.nmcs = 1
        self.npfs = len(self.pfrange)
        self.nyfs = len(self.yfrange)
        self.nrows = self.nfcs + self.npfs + 5
        self.ncols = self.nmcs + self.nyfs + 1
        self.yld1 = self.nmcs + self.nyfs - 2
        self.prc1 = self.nfcs + self.npfs - 4

    def get_formatted(self, data, crop, title, subtitle):
        """
        Main Method
        """
        fcidx = self.get_farm_crop_idx(crop)
        mcidx = self.mcidx_for_fc[fcidx]
        yield_row = self.yields[fcidx, :]
        price_col = self.mprices[:, mcidx]
        fctname = self.croptypenames[fcidx]
        mctname = self.mktcropnames[mcidx]
        full = self.full_block(data, title, subtitle, yield_row,
                               price_col, fctname, mctname)
        self.add_spans(full)
        self.add_styles(full)
        full = full.tolist()
        # at this point, full is a triply nested list such that full[row, col]
        # is a list with three elements: value as str, colspan as str, styles as str
        return full

    # --------------------------------------------
    # Construction of table blocks (string arrays)
    # --------------------------------------------
    def full_block(self, data, title, subtitle, yield_row, price_col,
                   fctname, mctname):
        """
        string array representing the full table
        with third dimension: [value, span, style]
        """
        block = np.full((self.nrows, self.ncols, 3), '', dtype=object)
        block[:3, :, 0] = self.title_block(title, subtitle)
        block[3:self.nfcs+3, self.nmcs:, 0] = self.yields_block(yield_row, fctname)
        block[self.nfcs+3:, :self.nmcs, 0] = self.prices_block(price_col, mctname)
        block[self.nfcs+3:, self.nmcs:, 0] = self.sens_block(data)
        return block

    def title_block(self, title, subtitle):
        block = np.full((3, self.ncols), '', dtype=object)
        block[0, 0] = title
        block[1, 0] = subtitle
        block[2, self.nmcs] = 'ASSUMED FARM YIELDS'
        return block

    def yields_block(self, yield_row, fctname):
        block = np.full((self.nfcs, self.nyfs+1), '',  dtype=object)
        block.fill('')
        block[:self.nfcs, 0] = fctname
        block[:self.nfcs, 1:] = [f'{yd:.0f}' for yd in yield_row.tolist()]
        return block

    def prices_block(self, price_col, mctname):
        block = np.full((self.npfs+2, self.nmcs), '', dtype=object)
        block[0, 0] = 'ASSUMED HARVEST PRICES'
        block[1, :] = mctname
        block[2:, :] = np.array([f'${mp:.2f}' for mp in price_col.tolist()]
                                ).reshape(self.npfs, 1)
        return block

    def sens_block(self, data):
        block = np.full((self.npfs+2, self.nyfs+1), '', dtype=object)
        block[1, 1:] = list(map('{:.0%}'.format, self.yfrange))
        block[2:, 0] = list(map('{:.0%}'.format, self.pfrange))
        lst = data.tolist()
        block[2:, 1:] = [list(map('{:,.0f}'.format, ll)) for ll in lst]
        return block

    # ----------------------------
    # Addition of spans and styles
    # ----------------------------
    def add_spans(self, table):
        table[0, 0, 1] = str(self.ncols)             # title
        table[1, 0, 1] = str(self.ncols)             # subtitle
        table[2, self.nmcs, 1] = str(self.nyfs+1)    # 'Assumed farm yields'
        table[self.nfcs+3, 0, 1] = str(self.nmcs)    # 'Assumed harvest prices'


# @@@@@@@@@@@@@@@@@@@@@@@@
# STD FARM
# @@@@@@@@@@@@@@@@@@@@@@@@
class SensTableStdFarm(SensTable):
    """
    Formats a standard whole farm table
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # lengths for layout
        self.nfcs = len(self.farm_crops)
        self.nmcs = len(self.market_crops)
        self.npfs = len(self.pfrange)
        self.nyfs = len(self.yfrange)
        self.nrows = self.nfcs + self.npfs + 5
        self.ncols = self.nmcs + self.nyfs + 1
        self.yld1 = self.nmcs + self.nyfs - 2
        self.prc1 = self.nfcs + self.npfs - 4

    def get_formatted(self, data, crop, title, subtitle):
        """
        Main Method
        """
        full = self.full_block(data, title, subtitle)
        self.add_spans(full)
        self.add_styles(full)
        full = full.tolist()
        # at this point, full is a triply nested list such that full[row, col]
        # is a list with three elements: value as str, colspan as str, styles as str
        return full

    # --------------------------------------------
    # Construction of table blocks (string arrays)
    # --------------------------------------------
    def full_block(self, data, title, subtitle):
        """
        string array representing the full table
        with third dimension: [value, span, style]
        """
        block = np.full((self.nrows, self.ncols, 3), '', dtype=object)
        block[:3, :, 0] = self.title_block(title, subtitle)
        block[3:self.nfcs+3, self.nmcs:, 0] = self.yields_block()
        block[self.nfcs+3:, :self.nmcs, 0] = self.prices_block()
        block[self.nfcs+3:, self.nmcs:, 0] = self.sens_block(data)
        return block

    def title_block(self, title, subtitle):
        block = np.full((3, self.ncols), '', dtype=object)
        block[0, 0] = title
        block[1, 0] = subtitle
        block[2, self.nmcs] = 'ASSUMED FARM YIELDS'
        return block

    def yields_block(self):
        block = np.full((self.nfcs, self.nyfs+1), '',  dtype=object)
        block.fill('')
        block[:self.nfcs, 0] = self.croptypenames
        block[:self.nfcs, 1:] = [list(map('{:.0f}'.format, ll))
                                 for ll in self.yields.tolist()]
        return block

    def prices_block(self):
        block = np.full((self.npfs+2, self.nmcs), '', dtype=object)
        block[0, 0] = 'ASSUMED HARVEST PRICES'
        block[1, :] = self.mktcropnames[:]
        block[2:, :] = [list(map('${:.2f}'.format, ll))
                        for ll in self.mprices.tolist()]
        self.pricesblock = block
        return block

    def sens_block(self, data):
        block = np.full((self.npfs+2, self.nyfs+1), '', dtype=object)
        block[1, 1:] = list(map('{:.0%}'.format, self.yfrange))
        block[2:, 0] = list(map('{:.0%}'.format, self.pfrange))
        lst = data.tolist()
        block[2:, 1:] = [list(map('{:,.0f}'.format, ll)) for ll in lst]
        return block

    # ----------------------------
    # Addition of spans and styles
    # ----------------------------
    def add_spans(self, table):
        table[0, 0, 1] = str(self.ncols)             # title
        table[1, 0, 1] = str(self.ncols)             # subtitle
        table[2, self.nmcs, 1] = str(self.nyfs+1)    # 'Assumed farm yields'
        table[self.nfcs+3, 0, 1] = str(self.nmcs)    # 'Assumed harvest prices'


# @@@@@@@@@@@@@@@@@@@@@@@@
# STD WHEATDC
# @@@@@@@@@@@@@@@@@@@@@@@@
class SensTableStdWheatDC(SensTable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # show all fsa crops for both yield and price blocks
        self.fsa_crops = list(self.farm_year.fsa_crops.all())
        # lengths for layout
        self.nfcs = 2
        self.nmcs = 2
        self.npfs = len(self.pfrange)
        self.nyfs = len(self.yfrange)
        self.nrows = self.nfcs + self.npfs + 5
        self.ncols = self.nmcs + self.nyfs + 1
        self.yld1 = self.nmcs + self.nyfs - 2
        self.prc1 = self.nfcs + self.npfs - 4

    def get_formatted(self, data, crop, title, subtitle):
        """
        Main Method
        """
        mcidxs = [self.mcidx_for_fc[i] for i in self.wheatdcixs]
        yield_rows = self.yields[self.wheatdcixs, :]
        price_cols = self.mprices[:, mcidxs]
        fctnames = [self.croptypenames[i] for i in self.wheatdcixs]
        mctnames = [self.mktcropnames[mcidx] for mcidx in mcidxs]
        full = self.full_block(data, title, subtitle, yield_rows, price_cols,
                               fctnames, mctnames)
        self.add_spans(full)
        self.add_styles(full)
        full = full.tolist()
        # at this point, full is a triply nested list such that full[row, col]
        # is a list with three elements: value as str, colspan as str, styles as str
        return full

    # --------------------------------------------
    # Construction of table blocks (string arrays)
    # --------------------------------------------
    def full_block(self, data, title, subtitle, yield_rows, price_cols,
                   fctnames, mctnames):
        """
        string array representing the full table
        with third dimension: [value, span, style]
        """
        block = np.full((self.nrows, self.ncols, 3), '', dtype=object)
        block[:3, :, 0] = self.title_block(title, subtitle)
        block[3:self.nfcs+3, self.nmcs:, 0] = self.yields_block(yield_rows, fctnames)
        block[self.nfcs+3:, :self.nmcs, 0] = self.prices_block(price_cols, mctnames)
        block[self.nfcs+3:, self.nmcs:, 0] = self.sens_block(data)
        return block

    def title_block(self, title, subtitle):
        block = np.full((3, self.ncols), '', dtype=object)
        block[0, 0] = title
        block[1, 0] = subtitle
        block[2, self.nmcs] = 'ASSUMED FARM YIELDS'
        return block

    def yields_block(self, yield_rows, fctnames):
        block = np.full((self.nfcs, self.nyfs+1), '',  dtype=object)
        block.fill('')
        block[:self.nfcs, 0] = fctnames
        block[:self.nfcs, 1:] = [list(map('{:.0f}'.format, ll))
                                 for ll in yield_rows.tolist()]
        return block

    def prices_block(self, price_cols, mctnames):
        block = np.full((self.npfs+2, self.nmcs), '', dtype=object)
        block[0, 0] = 'ASSUMED HARVEST PRICES'
        block[1, :] = mctnames
        block[2:, :] = [list(map('${:.2f}'.format, ll))
                        for ll in price_cols.tolist()]
        return block

    def sens_block(self, data):
        block = np.full((self.npfs+2, self.nyfs+1), '', dtype=object)
        block[1, 1:] = list(map('{:.0%}'.format, self.yfrange))
        block[2:, 0] = list(map('{:.0%}'.format, self.pfrange))
        lst = data.tolist()
        block[2:, 1:] = [list(map('{:,.0f}'.format, ll)) for ll in lst]
        return block

    # ----------------------------
    # Addition of spans and styles
    # ----------------------------
    def add_spans(self, table):
        table[0, 0, 1] = str(self.ncols)             # title
        table[1, 0, 1] = str(self.ncols)             # subtitle
        table[2, self.nmcs, 1] = str(self.nyfs+1)    # 'Assumed farm yields'
        table[self.nfcs+3, 0, 1] = str(self.nmcs)    # 'Assumed harvest prices'


# @@@@@@@@@@@@@@@@@@@@@@@@
# TITLE (Crop Farm and WheatDC)
# @@@@@@@@@@@@@@@@@@@@@@@@
class SensTableTitle(SensTable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # show all fsa crops for both yield and price blocks
        self.fsa_crops = list(self.farm_year.fsa_crops.all())
        # lengths for layout
        self.nfsacs = len(self.fsa_crops)
        self.npfs = len(self.pfrange)
        self.nyfs = len(self.yfrange)
        self.nrows = self.nfsacs + self.npfs + 5
        self.ncols = self.nfsacs*2 + self.nyfs + 1
        self.yld1 = self.nfsacs*2 + self.nyfs - 2
        self.prc1 = self.nfsacs + self.npfs - 4

    def get_formatted(self, data, crop, title, subtitle):
        """
        Main Method for Farm and WheatDC cases
        """
        full = self.full_block(data, title, subtitle)
        # at this point, full is a triply nested list such that full[row, col]
        # is a list with three elements: value as str, colspan as str, styles as str
        self.add_spans(full)
        self.add_styles(full)
        full = full.tolist()
        return full

    # --------------------------------------------
    # Construction of table blocks (string arrays)
    # --------------------------------------------
    def full_block(self, data, title, subtitle):
        """
        string array representing the full table
        with third dimension: [value, span, style]
        """
        block = np.full((self.nrows, self.ncols, 3), '', dtype=object)
        block[:3, :, 0] = self.title_block(title, subtitle)
        block[3:self.nfsacs+3, self.nfsacs*2:, 0] = self.yields_block()
        block[self.nfsacs+3:, :self.nfsacs*2, 0] = self.prices_block()
        block[self.nfsacs+3:, self.nfsacs*2:, 0] = self.sens_block(data)
        return block

    def title_block(self, title, subtitle):
        block = np.full((3, self.ncols), '', dtype=object)
        block[0, 0] = title
        block[1, 0] = subtitle
        block[2, self.nfsacs*2] = 'ASSUMED COUNTY YIELDS'
        return block

    def yields_block(self):
        block = np.full((self.nfsacs, self.nyfs+1), '',  dtype=object)
        block.fill('')
        block[:self.nfsacs, 0] = self.fsacropnames
        block[:self.nfsacs, 1:] = [list(map('{:.0f}'.format, ll))
                                   for ll in self.cty_yields.tolist()]
        return block

    def prices_block(self):
        block = np.full((self.npfs+2, self.nfsacs*2), '', dtype=object)
        block[0, 0] = 'ASSUMED MYA PRICES'
        block[1, ::2] = self.fsacropnames
        block[2:, ::2] = [list(map('${:.2f}'.format, ll))
                          for ll in self.mya_prices.tolist()]
        block[2:, 1::2] = [list(map('{:.0%}'.format, ll))
                           for ll in self.mya_pcts.tolist()]
        return block

    def sens_block(self, data):
        block = np.full((self.npfs+2, self.nyfs+1), '', dtype=object)
        block[1, 1:] = list(map('{:.0%}'.format, self.yfrange))
        block[2:, 0] = list(map('{:.0%}'.format, self.pfrange))
        lst = data.tolist()
        block[2:, 1:] = [list(map('{:,.0f}'.format, ll)) for ll in lst]
        return block

    # ----------------------------
    # Addition of spans and styles
    # ----------------------------
    def add_spans(self, table):
        table[0, 0, 1] = str(self.ncols)                    # title
        table[1, 0, 1] = str(self.ncols)                    # subtitle
        table[2, self.nfsacs*2, 1] = str(self.nyfs+1)       # 'Assumed county yields'
        table[self.nfsacs+3, 0, 1] = str(self.nfsacs*2)     # 'Assumed MYA prices'
        table[self.nfsacs+4, :self.nfsacs*2:2, 1] = str(2)  # FSA crop col heads

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
        # Assumed county yields block
        table[2, self.nfsacs*2, 2] += center+bold+bordl  # 'Assumed County Yields'
        table[2, self.nfsacs*2:, 2] += bordy
        # Yields
        table[3:self.nfsacs+3, self.nfsacs*2, 2] += left+bold+bordl
        table[3:self.nfsacs+3, self.nfsacs*2+1:, 2] += right
        table[3:self.nfsacs+3, -1, 2] += bordr
        table[3:self.nfsacs+3, self.yld1, 2] += bordx+bkg+bold
        table[self.nfsacs+2, self.nfsacs*2:, 2] += bordb
        table[self.nfsacs+4:, self.yld1, 2] += bordx
        # Yield Bracket
        table[3:self.nfsacs+3, self.yld1-2, 2] += bordl
        # Assumed MYA prices block
        table[self.nfsacs+3, 0, 2] += center+bold
        table[self.nfsacs+3, :self.nfsacs*2, 2] += bordy
        table[self.nfsacs+3:self.nfsacs+5, self.nfsacs*2, 2] += bordl
        table[self.nfsacs+4, :self.nfsacs*2, 2] += center+under+bold
        # Not sure if this helps...
        # table[self.nfsacs+4, 2:self.nfsacs*2:2, 2] += bordl
        table[self.nfsacs+5:self.nfsacs+5+self.npfs, :self.nfsacs*2, 2] += right
        table[self.prc1, :self.nfsacs*2+1, 2] += bordy+bkg+bold
        table[self.prc1, self.nfsacs*2+1:, 2] += bordy
        # Price Bracket
        table[self.prc1-2, :self.nfsacs*2, 2] += bordt
        table[self.prc1+2, :self.nfsacs*2, 2] += bordb
        # Base value
        table[self.prc1, self.yld1, 2] += bord+bold
        # Base value bracket
        table[self.prc1-2, self.yld1-2:, 2] += bordt
        table[self.prc1+2, self.yld1-2:, 2] += bordb
        table[self.prc1-2:self.prc1+3, self.yld1-2, 2] += bordl

        # Yield %
        table[self.nfsacs+4, self.nfsacs*2+1:, 2] += bordy+bold
        table[self.nfsacs+4, self.nfsacs*2+1, 2] += bordl
        table[self.nfsacs+4, self.yld1, 2] += bkg
        # Price %
        table[self.nfsacs+5:, self.nfsacs*2, 2] += bordx+bold
        table[self.nfsacs+5, self.nfsacs*2, 2] += bordt+bold

        # Sensitized values
        def isneg(s):
            return s.startswith('-')
        visneg = np.vectorize(isneg)
        table[self.nfsacs+5:, self.nfsacs*2+1:, 2] += np.where(
            visneg(table[self.nfsacs+5:, self.nfsacs*2+1:, 0]), bkgred, bkggrn)
        table[self.nfsacs+5:, self.nfsacs*2+1:, 2] += right

        # De-duplicate style strings
        rs, cs, _ = table.shape
        for r in range(rs):
            for c in range(cs):
                table[r, c, 2] = ' '.join(list(set(table[r, c, 2].split())))

    def delete_spanned_cols(self, full):
        """ Given the full table as nested list, delete spanned colums """
        # title and subtitle
        for row in full[:2]:
            del row[1:self.ncols]
        # assumed county yields
        row = full[2]
        del row[self.nfsacs*2+1:]
        # assumed MYA prices
        row = full[self.nfsacs+3]
        del row[1:self.nfsacs*2]
        # crop labels
        row = full[self.nfsacs+4]
        for i in range(self.nfsacs):
            del row[2*self.nfsacs - 2*i - 1]
