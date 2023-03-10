from numpy import zeros, array
import numpy as np
from math import log, exp

np.set_printoptions(precision=2)
np.set_printoptions(suppress=True)


class EntPrems:
    """
    Class for computing 'Combo' premiums for optional, basic and enterprise
    unit crop insurance, for RP, RP-HPE, YO, for coverage levels 50, 55, ..., 85
    """
    def __init__(self):
        self.load_lookups()
        self.subsidy = (0.8,  0.8,  0.8,  0.8,  0.8,  0.77, 0.68, 0.53)

        self.cover = array([x/100 for x in range(50, 86, 5)])  # coverage levels

        # User inputs
        # -----------
        self.acre = None       # acres to insure

        # yields
        self.aphyield = None   # Actual production history yield
        self.apprYield = None  # Approved yield
        self.tayield = None    # Trend-adjusted yield

        # price / volatility
        self.aphPrice = None   # Actual or estimated production history price
        self.pvol = None       # Actual or estimate volatility factor

        # extras
        self.hf = None         # Hail / Fire protection
        self.pf = None         # Prevent plant protection
        self.tause = None      # 1 to use trend-adjusted yields else 0
        self.ye = None         # 1 to use yield-exclusion else 0

        # Risk related
        self.riskname = None   # {'None', 'AAA', 'BBB', 'CCC', 'DDD'} dep. on county
        self.risk = None       # {0: None, 1: 'AAA', 2: 'BBB', 3: 'CCC', 4: 'DDD'}
        self.highRisk = None   # float looked up by code and riskname in high_risk dict
        self.rtype = None      # int looked up by code and riskname in high_risk dict

        # lookup key codes
        self.code = None       # code for state/county/crop/etc..
        self.fcode = None      # code with decimal suffix for risk

        # scalar variables
        # -------------------------
        self.adjMeanQty = None
        self.adjStdQty = None
        self.disEnter = None
        self.effcov = None
        self.jSize = None            # based on acre
        self.liab = None
        self.lnMean = None
        self.multFactor = None
        self.premRate = None         # Premium rates array (Erev, E)
        self.revCov = None
        self.revYield = None
        self.selected_draws = None
        self.simLoss = None          # Simulated Loss array (Yp, Rp, RpExc)
        # only keep 2nd index
        self.revExcRateUse = None
        self.revRateUse = None

        # 3-tuples
        self.mQty = None
        self.stdQty = None

        # (current/prev) pairs
        self.baseRate = None          # Continuous rating base rate
        self.eFactor = None
        self.eFactorRev = None
        self.rateDiffFac = None
        self.revLook = None
        self.uFactor = None

        # Array sized (2, 2)  ('E', 'Erev') by (cur, prior)
        self.basePremRate = None

        # Arrays sized (8, 2) (8 coverage levels) by 2 (cur, prior)
        self.rateDiff = None
        self.unitFactor = None
        self.enterpriseFactor = None
        self.enterFactorRev = None

        # Arrays sized (8, 6) (8 coverage levels) by (6 acre size values)
        self.discountEnter = None

    # -----------------------------
    # MAIN METHOD: COMPUTE PREMIUMS
    # -----------------------------
    def compute_premiums(self, aphyield=180, apprYield=180, tayield=190, acre=100,
                         hf=0, pf=0, riskname='None', tause=1, ye=0,
                         county='Champaign, IL', crop='Corn',
                         practice='Non-irrigated', atype='Grain'):
        """
        With farm-specific inputs, compute premiums for optional, basic and enterprise,
        units with RP, RP-HPE or YO protection for all coverage levels.
        """
        self.store_user_settings(aphyield, apprYield, tayield, acre, hf, pf, riskname,
                                 tause, ye, county, crop, practice, atype)
        self.initialize_arrays()
        self.set_multfactor()
        for i in range(8):  # index i corresponds to coverage level
            if self.rateDiff[i, 0] > 0:
                self.set_effcov(i)
                self.set_factors(i)
                self.make_ye_adj()
                self.make_rev_liab(i)
                self.set_base_rates()
                self.set_base_prem_rates()
                self.limit_base_prem_rates()
                self.limit_revlook()
                self.limit_baserate()
                self.set_qtys()
                # step 5.01
                # section 5 revenue calculation
                self.simulate_losses()
                self.set_rates()
                self.set_prems(i)
                self.apply_subsidy(i)
        return self.prem

    def set_multfactor(self):
        """
        Set Multiplicative Factor used in Worksheet step 7.
        """
        # options factor
        hfrate, pfrate, ptrate = self.options[self.code]
        self.multFactor = 1
        if self.hf > 0:
            self.multFactor *= hfrate
        if self.pf == 1:
            self.multFactor *= pfrate
        if self.pf == 2:
            self.multFactor *= ptrate

    def set_effcov(self, i):
        """
        Set the effective coverage level
        """
        self.effcov = round(0.0001 + self.cover[i] *
                            self.tayield / self.apprYield, 2)

    def set_factors(self, i):
        """
        Set 4 vector factors and 2 scalar factors used to compute base premium rates
        """
        self.rateDiffFac[:] = (
            self.get_factor(self.rateDiff, i, 0, 9),
            self.get_factor(self.rateDiff, i, 1, 9))
        self.uFactor[:] = (
            self.get_factor(self.unitFactor, i, 0, 3),
            self.get_factor(self.unitFactor, i, 1, 3))
        self.eFactor[:] = (
            self.get_factor(self.enterpriseFactor, i, 0, 3),
            self.get_factor(self.enterpriseFactor, i, 1, 3))
        self.eFactorRev[:] = (
            self.get_factor(self.enterFactorRev, i, 0, 3),
            self.get_factor(self.enterFactorRev, i, 1, 3))
        self.disEnter = self.get_factor(self.discountEnter, i, self.jSize, 4)

    def get_factor(self, var, i, j2, ro):
        """
        Given a variable (e.g. rateDiff), a 2nd index and a roundoff precision,
        first compute some indices, then use them to get a factor (e.g. rateDiffFac)
        """
        ecv, cv, rd = self.effcov, self.cover, self.rateDiff
        jlow = (0 if ecv < 0.55 else 1 if ecv < 0.6 else 2 if ecv < 0.65 else
                3 if ecv < 0.7 else 4 if ecv < 0.75 else 5 if ecv < 0.8 else 6)
        jhigh = (0 if ecv < 0.5 else 1 if ecv < 0.55 else 2 if ecv < 0.6 else
                 3 if ecv < 0.65 else 4 if ecv < 0.7 else 5 if ecv < 0.75 else
                 6 if ecv < 0.8 else 7)
        jfloor = (0 if ecv < 0.55 else 1 if ecv < 0.6 else 2 if ecv < 0.65 else
                  3 if ecv < 0.7 else 4 if ecv < 0.75 else 5 if ecv < 0.8 else
                  6 if ecv < 0.85 else 7)
        if ecv > 0.75 and rd[6, 0] == 0:
            jlow = 4
            jhigh = 5
            jfloor = 5
        return (
            round(var[jfloor, j2] + (var[jhigh, j2] - var[jlow, j2]) *
                  (ecv - cv[jfloor]) * 20 + 1e-11, ro) if self.tause else
            var[i, j2])

    def make_ye_adj(self):
        """
        Adjust factors for YE (vectorized)
        """
        jjHigh = 5 if self.rateDiff[6, 0] == 0 else 7
        yeAdj = 0
        if self.effcov > 0.85:
            if self.ye > 0.5:
                yeAdj = (self.effcov - 0.85) / 0.15
            yeAdj = 1 + round(min(1, yeAdj) ** 3, 7) * 0.05
            self.rateDiffFac[0] *= yeAdj
            self.uFactor = np.minimum(self.uFactor, self.unitFactor[jjHigh, :])
            self.eFactor = np.minimum(self.eFactor, self.enterpriseFactor[jjHigh, :])

    def make_rev_liab(self, i):
        """
        Set the revised yield, the revised cover and the liability
        """
        # step 1
        self.revYield = self.tayield if self.tause else self.apprYield
        self.revCov = self.effcov if self.tause else self.cover[i]
        self.liab = round(round(self.revYield * self.cover[i] + 0.001, 1) *
                          self.aphPrice * self.acre, 0)

    def set_base_rates(self):
        """
        Set and limit vector base rates from RMA data
        """
        # step 2.01: Look up current and previous year rates.
        refyield, refrate, exponent, fixedrate = zeros(2), zeros(2), zeros(2), zeros(2)
        (refyield[0], refrate[0], exponent[0], fixedrate[0],
         refyield[1], refrate[1], exponent[1], fixedrate[1]) = self.rates[self.code]

        # Worksheet steps 1, 2: Continuous rating base rate (current/prior)
        self.baseRate = np.minimum(np.maximum(
            (self.aphyield / refyield).round(2), 0.5), 1.5)

        # step 2.02: vectorized (current/prior)
        self.baseRate = (self.baseRate ** exponent).round(8)

        # step 2.03: vectorized (current/prior)
        self.baseRate = (self.highRisk + self.baseRate * refrate + fixedrate).round(8)
        if self.rtype > 1.5:
            self.baseRate[:] = self.highRisk
        self.revLook[:] = self.baseRate

    def set_base_prem_rates(self):
        """
        Set vector adjusted base premium rates
        """
        # Worksheet step 8.  Calculate Base Premium Rates Adjusted Base Rate x
        # coverage level rate differential.
        # step 2.04
        prod = self.baseRate * self.rateDiffFac
        self.basePremRate = array((prod * self.eFactor,
                                   prod * self.eFactorRev)).round(8)

    def limit_base_prem_rates(self):
        """
        Limit base premium rates based on prior (unpacking vectors)
        """
        # Preliminary base rate is min of cur and 1.2 * prev.
        # step 2.05
        var = self.basePremRate
        for i in range(2):
            if var[i, 0] > var[i, 1] * 1.2:
                var[i, 0] = round(var[i, 1] * 1.2, 8)
            if var[i, 0] > 0.99:
                var[i, 0] = 0

    def limit_revlook(self):
        """
        Limit revenue lookup based on previous (unpacking vectors)
        """
        # step 2.06
        if self.revLook[0] > self.revLook[1] * 1.2:
            self.revLook[0] = round(self.revLook[1] * 1.2, 8)
        self.revLook[0] = round(min(self.revLook[0], 0.9999), 4)

    def limit_baserate(self):
        """
        Limit base rate based on previous (unpacking vectors)
        """
        # step 2.07
        if self.baseRate[0] > self.baseRate[1] * 1.2:
            self.baseRate[0] = round(self.baseRate[1] * 1.2, 8)

    def set_qtys(self):
        """
        Compute mQty and stdQty
        """
        prod = self.revLook[0] * 10000
        revLookup = int(prod * self.discountEnter[3, self.jSize] + 0.5)
        self.mQty, self.stdQty = self.rev_lookup[revLookup]

    def simulate_losses(self):
        """
        Loop through 500 yield, price pairs, incrementing losses.
        """
        # step 5.02
        self.adjMeanQty = round(self.revYield * self.mQty / 100, 8)
        self.adjStdQty = round(self.revYield * self.stdQty / 100, 8)
        self.lnMean = round(log(self.aphPrice) - (self.pvol ** 2 / 2), 8)
        # step 5.04 simulate losses

        simloss = zeros(3)  # (Yp, Rp, RpExc)
        for yieldDraw, priceDraw in self.selected_draws:
            # yield insurance
            yld = max(0, yieldDraw * self.adjStdQty + self.adjMeanQty)
            loss = max(0, self.revYield * self.revCov - yld)
            simloss[0] += loss
            # revenue insurance
            harPrice = min(2 * self.aphPrice,
                           exp(priceDraw * self.pvol + self.lnMean))
            guarPrice = max(harPrice, self.aphPrice)
            loss = max(0, self.revYield * guarPrice * self.revCov - yld * harPrice)
            simloss[1] += loss
            # revenue insurance with exclusion
            loss = max(0, self.revYield * self.aphPrice * self.revCov - yld * harPrice)
            simloss[2] += loss
        # step 5.05
        ct = len(self.selected_draws)
        self.simLoss[0] = round((simloss[0] / ct) / (self.revYield * self.revCov), 8)
        self.simLoss[1] = round(simloss[1] / ct /
                                (self.revYield * self.revCov * self.aphPrice), 8)
        self.simLoss[2] = round(simloss[2] / ct /
                                (self.revYield * self.revCov * self.aphPrice), 8)

    def set_rates(self):
        """
        Set the premium rates
        """
        # step 5.06
        self.revRateUse = round(max(0.01 * self.basePremRate[0, 0],
                                self.simLoss[1] - self.simLoss[0]), 8)
        self.revExcRateUse = round(max(-0.5 * self.basePremRate[0, 0],
                                   self.simLoss[2] - self.simLoss[0]), 8)
        # step 6  No historical revenue capping is performed
        # step 8.01
        self.premRate[0] = self.basePremRate[0, 0] * self.multFactor * self.disEnter
        self.premRate[1] = self.basePremRate[1, 0] * self.multFactor * self.disEnter

    def set_prem(self, rate, i, j, rateuse=0):
        """
        Set a premium with given rate, indices and optional rateuse
        """
        self.prem[i, j] = round(self.liab * round(rate + rateuse, 8), 0)

    def set_prems(self, i):
        """
        Set the pre-subsidy premiums
        """
        self.set_prem(self.premRate[1], i, 0, self.revRateUse)       # rp
        self.set_prem(self.premRate[1], i, 1, self.revExcRateUse)    # rpexc
        self.set_prem(self.premRate[0], i, 2)                        # yp

    def apply_subsidy(self, i):
        """
        Apply the subsidy
        """
        for j in range(3):
            self.prem[i, j] -= round(self.prem[i, j] * self.subsidy[i], 0)
            self.prem[i, j] = round(self.prem[i, j] / self.acre, 2)

    # ------------------------
    # Setup and Initialization
    # ------------------------
    def load_lookups(self):
        """
        Define dicts for lookups
        """
        self.crops = {'Corn': '41', 'Soybeans': '81', 'Wheat': '11'}
        self.practices = {'Nfac (non-irrigated)': '053',
                          'Fac (non-irrigated)': '043',
                          'Non-irrigated': '003',
                          'Irrigated': '002'}
        self.types = {'Grain': '016', 'No Type Specified': '997', 'Winter': '011'}
        self.risk_classes = {'None': 0, 'AAA': 1, 'BBB': 2, 'CCC': 3, 'DDD': 4}
        self.states = {
            'IL': '17', 'AL': '01', 'AR': '05', 'FL': '12', 'GA': '13', 'IN': '18',
            'IA': '19', 'KS': '20', 'KY': '21', 'LA': '22', 'MD': '24', 'MI': '26',
            'MN': '27', 'MS': '28', 'MO': '29', 'NE': '31', 'NC': '37', 'ND': '38',
            'OH': '39', 'PA': '41', 'SC': '45', 'SD': '46', 'TN': '47', 'VA': '51',
            'WV': '54', 'WI': '55', 'OK': '40', 'TX': '48'}

        self.counties = get_counties()
        self.enter_id = get_enter_id()
        self.beta_id = get_beta_id()
        self.options = get_options()
        self.discount_enter = get_discount_enter()
        self.rates = get_rates()
        self.rate_diff = get_rate_diff()
        self.prate_diff = get_prate_diff()
        self.unit_factor = get_unit_factor()
        self.punit_factor = get_punit_factor()
        self.enterprise_factor = get_enterprise_factor()
        self.penterprise_factor = get_penterprise_factor()
        self.enter_factor_rev = get_enter_factor_rev()
        self.penter_factor_rev = get_penter_factor_rev()
        self.rev_lookup = get_rev_lookup()
        self.draws = get_draws()
        self.high_risk = get_high_risk()
        self.parameters = get_parameters()

    def store_user_settings(self, aphyield, apprYield, tayield, acre, hf, pf, riskname,
                            tause, ye, county, crop, practice, atype):
        """
        Store settings provide by user when calling calc_premiums
        """
        self.aphyield = aphyield
        self.apprYield = apprYield
        self.tayield = tayield
        self.acre = acre
        self.hf = hf
        self.pf = pf
        self.riskname = riskname
        self.risk = self.risk_classes[self.riskname]
        self.highRisk = None
        self.rtype = None
        self.tause = tause
        self.ye = ye

        if self.tayield < self.aphyield:
            self.tayield = self.aphyield

        # codes used to key into dicts
        self.code = self.make_code(county, crop, atype, practice)
        self.fcode = self.code + 0.1 * (1 + self.risk)
        self.pcode = self.make_pcode(str(self.code))

        # read price and volatility from parameters
        self.aphPrice, self.pvol = self.parameters[self.pcode]

        # Set index based on acreage
        self.jSize = (0 if self.acre < 50 else 1 if self.acre < 100 else
                      2 if self.acre < 200 else 3 if self.acre < 400 else
                      4 if self.acre < 800 else 5)

    def initialize_arrays(self):
        """
        Initialize arrays for premium calculation
        """
        # Initialize current/prev arrays
        self.rateDiffFac = zeros(2)
        self.uFactor = zeros(2)
        self.eFactor = zeros(2)
        self.eFactorRev = zeros(2)
        self.baseRate = zeros(2)
        self.revLook = zeros(2)

        # Initialize array to hold premiums
        self.prem = zeros((8, 3))

        enterId = self.enter_id[self.code]
        betaId = self.beta_id[self.code]

        self.premRate = zeros(2)  # Premium rates array (Erev, E)
        self.simLoss = zeros(3)   # Simulated losses array (Yp, Rp, RpExc)

        # Look up info from the dicts created when the object was constructed
        self.highRisk, self.rtype = ((0, 0) if self.risk == 0 else
                                     self.high_risk[str(self.code)+self.riskname])
        self.discountEnter = self.discount_enter[enterId]
        self.rateDiff = array((self.rate_diff[self.fcode],
                               self.prate_diff[self.fcode])).T
        self.unitFactor = array((self.unit_factor[self.fcode],
                                 self.punit_factor[self.fcode])).T
        self.enterpriseFactor = array((self.enterprise_factor[self.fcode],
                                       self.penterprise_factor[self.fcode])).T
        self.enterFactorRev = array((self.enter_factor_rev[self.fcode],
                                     self.penter_factor_rev[self.fcode])).T
        self.selected_draws = self.draws[betaId]

    def make_code(self, county, crop, atype, practice):
        """
        Construct an integer code used to key in some tabular data
        """
        return int(f'{self.counties[county]}{self.crops[crop]}' +
                   f'{self.types[atype]}{self.practices[practice]}')

    def make_pcode(self, code):
        """
        Construct a string code (crop + state) to key in parameter data (price, vol)
        """
        return code[5:7]+code[:2]

# -------------------------------------
# Helper functions for text file import
# -------------------------------------


def readfile(filename):
    """
    Read a tab-separated textfile into a string and return it
    """
    with open(filename, 'r') as f:
        contents = f.read()
    return contents


def get_file_items(filename):
    """
    Get file contents then return a nested list of the tab separated
    values for each line.
    """
    contents = readfile(filename)
    return (line.split() for line in contents.strip().split('\n'))


def get_float_tuple_dict(filename, rest=None):
    """
    Get a nested list of items for the given file, then construct a dict
    using the float-converted, first item in each row as the dict key and setting
    the associated value to a tuple of floats from the other items of interest,
    which are selected via the 'rest' argument.
    """
    if rest is None:
        rest = slice(1, None, None)
    items = get_file_items(filename)
    return {float(item[0]): tuple(float(it) for it in item[rest]) for item in items}


def get_enter_id():
    items = get_file_items('data/enterId.txt')
    return {int(code): int(unitId) for code, unitId in items}


def get_beta_id():
    items = get_file_items('data/betaid.txt')
    return {int(code): int(betaId) for code, betaId in items}


def get_options():
    items = get_file_items('data/options.txt')
    return {int(code): (float(hf), float(pf), float(pt))
            for code, hf, pf, pt, _ in items}


def get_rates():
    items = get_file_items('data/rates.txt')
    return {int(item[0]): tuple(float(it) for it in item[1:]) for item in items}


def get_rate_diff():
    return get_float_tuple_dict('data/rateDiff.txt')


def get_prate_diff():
    return get_float_tuple_dict('data/prateDiff.txt')


def get_unit_factor():
    return get_float_tuple_dict('data/UnitFactor.txt', rest=slice(3, None, None))


def get_punit_factor():
    return get_float_tuple_dict('data/punitFactor.txt')


def get_enterprise_factor():
    return get_float_tuple_dict('data/enterpriseFactor.txt')


def get_penterprise_factor():
    return get_float_tuple_dict('data/penterpriseFactor.txt')


def get_enter_factor_rev():
    return get_float_tuple_dict('data/enterFactorRev.txt')


def get_penter_factor_rev():
    return get_float_tuple_dict('data/pEnterFactorRev.txt')


def get_rev_lookup():
    items = get_file_items('data/revLookup.txt')
    return {int(code): (float(qty), float(std)) for code, qty, std in items}


def get_draws():
    items = get_file_items('data/draws.txt')
    draws = {}
    for code, _, yielddraw, pricedraw in items:
        draws.setdefault(int(code), []).append((float(yielddraw), float(pricedraw)))
    return draws


def get_discount_enter():
    items = get_file_items('data/discountEnter.txt')
    return {int(itm[0]): np.array([float(it) for it in itm[1:]]).reshape(8, 6)
            for itm in items}


def get_counties():
    items = get_file_items('data/counties.txt')
    return {f'{cty}, {st}': f'{int(stcode):02}{int(ctycode):03}'
            for stcode, ctycode, cty, st in items}


def get_high_risk():
    items = get_file_items('data/highRisk.txt')
    return {itm[0]+itm[1]: (float(itm[2]), float(itm[3])) for itm in items}


def get_parameters():
    items = get_file_items('data/parameters.txt')
    return {f'{int(itm[0]):02d}{int(itm[1]):02d}':
            (float(itm[2]), float(itm[3])) for itm in items}
