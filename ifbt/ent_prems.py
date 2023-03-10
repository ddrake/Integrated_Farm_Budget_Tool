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
        self.subsidy = array([[0.67, 0.64, 0.64, 0.59, 0.59, 0.55, 0.48, 0.38],
                              [0.8,  0.8,  0.8,  0.8,  0.8,  0.77, 0.68, 0.53]]).T

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

        # 8 coverage levels
        self.cover = array([x/100 for x in range(50, 86, 5)])

        # scalar instance variables
        self.adjMeanQty = None
        self.adjStdQty = None
        self.disBasic = None         # factor computed from discountBasic
        self.disEnter = None
        self.effcov = None
        self.jSize = None            # based on acre
        self.liab = None
        self.lnMean = None
        self.multFactor = None
        self.selected_draws = None
        self.premRateO = None        # Premium rate used for optional
        self.premRateB = None        # Premium rate used for basic
        self.premRateE = None        # Premium rate used for enterprise YO
        self.premRateErev = None     # Premium rate used for enterprise rev
        self.revCov = None
        self.revExcRateUse = None
        self.revExcRateEntUse = None
        self.revRateUse = None
        self.revRateEntUse = None
        self.revYield = None
        self.simRpLoss = None
        self.simRpExcLoss = None
        self.simYpLoss = None

        # 3-tuples
        self.mQty = None
        self.stdQty = None

        # Intance variable pairs with the current value in the first position
        # and the previous year value in the second position
        self.baseRate = None          # Continuous rating base rate
        self.basePremRate = None      # Base premium rate
        self.basePremRateE = None     # Base premium rate
        self.basePremRateErev = None
        self.eFactor = None
        self.eFactorRev = None
        self.rateDiffFac = None
        self.revLook = None
        self.uFactor = None

        # Arrays sized (8, 6) (6 values for each of 8 coverage levels)
        self.discountBasic = None
        self.discountEnter = None

        # Arrays sized (8, 2) (8 rows for coverage levels and 2 for current/prev)
        self.rateDiff = None
        self.unitFactor = None
        self.enterpriseFactor = None
        self.enterFactorRev = None

    def load_lookups(self):
        """
        Define dicts for lookups
        """
        self.crops = {'Corn': '41', 'Soybeans': '81', 'Wheat': '11', 'Sorghum': '51'}
        self.practices = {'Nfac (non-irrigated)': '053',
                          'Fac (non-irrigated)': '043',
                          'Non-irrigated': '003',
                          'Irrigated': '002'}
        self.types = {'Grain': '016', 'No Type Specified': '997', 'Winter': '011'}
        self.risk_classes = {'None': 0, 'AAA': 1, 'BBB': 2, 'CCC': 3, 'DDD': 4}
        self.counties = get_counties()
        self.enter_id = get_enter_id()
        self.beta_id = get_beta_id()
        self.options = get_options()
        self.discount_basic = get_discount_basic()
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

    def store_user_settings(self, aphyield, apprYield, tayield, acre, aphPrice, pvol,
                            hf, pf, riskname, tause, ye, county, crop, practice, atype):
        """
        Store settings provide by user when calling calc_premiums
        """
        self.aphyield = aphyield
        self.apprYield = apprYield
        self.tayield = tayield
        self.acre = acre
        self.aphPrice = aphPrice
        self.pvol = pvol
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
        self.prem = zeros((8, 9))

        enterId = self.enter_id[self.code]
        betaId = self.beta_id[self.code]

        # Look up info from the dicts created when the object was constructed
        self.highRisk, self.rtype = ((0, 0) if self.risk == 0 else
                                     self.high_risk[str(self.code)+self.riskname])
        self.discountBasic = self.discount_basic[enterId]
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

    # -------------------------------
    # Core business logic begins here
    # -------------------------------
    def make_code(self, county, crop, atype, practice):
        """
        Construct an integer code used to key in some tabular data
        """
        return int(f'{self.counties[county]}{self.crops[crop]}' +
                   f'{self.types[atype]}{self.practices[practice]}')

    def set_effcov(self, i):
        """
        Set the effective coverage level
        """
        self.effcov = round(0.0001 + self.cover[i] *
                            self.tayield / self.apprYield, 2)

    def get_factor(self, var, j2, ro):
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
        return round(
            var[jfloor, j2] +
            (var[jhigh, j2] - var[jlow, j2]) *
            (ecv - cv[jfloor]) * 20 + 0.00000000001, ro)

    def set_factors(self, i):
        """
        Set factors used to compute base premium rates
        """
        self.rateDiffFac[:] = (
            self.get_factor(self.rateDiff, 0, 9) if self.tause else
            self.rateDiff[i, 0],
            self.get_factor(self.rateDiff, 1, 9) if self.tause else
            self.rateDiff[i, 1])
        self.uFactor[:] = (
            self.get_factor(self.unitFactor, 0, 3) if self.tause else
            self.unitFactor[i, 0],
            self.get_factor(self.unitFactor, 1, 3) if self.tause else
            self.unitFactor[i, 1])
        self.eFactor[:] = (
            self.get_factor(self.enterpriseFactor, 0, 3) if self.tause else
            self.enterpriseFactor[i, 0],
            self.get_factor(self.enterpriseFactor, 1, 3) if self.tause else
            self.enterpriseFactor[i, 1])
        self.eFactorRev[:] = (
            self.get_factor(self.enterFactorRev, 0, 3) if self.tause else
            self.enterFactorRev[i, 0],
            self.get_factor(self.enterFactorRev, 1, 3) if self.tause else
            self.enterFactorRev[i, 1])
        self.disBasic = (
            self.get_factor(self.discountBasic, self.jSize, 4) if self.tause else
            self.discountBasic[i, self.jSize])
        self.disEnter = (
            self.get_factor(self.discountEnter, self.jSize, 4) if self.tause else
            self.discountEnter[i, self.jSize])

    def make_ye_adj(self):
        """
        Adjust factors for YE
        """
        # code for YE adj
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
        # step 1
        self.revYield = self.tayield if self.tause else self.apprYield
        self.revCov = self.effcov if self.tause else self.cover[i]
        self.liab = round(round(self.revYield * self.cover[i] + 0.001, 1) *
                          self.aphPrice * self.acre, 0)

    def set_base_rates(self):
        """
        Set and limit base rates from RMA data
        """
        # step 2.01: Look up current and previous year rates.
        refyield, refrate, exponent, fixedrate = zeros(2), zeros(2), zeros(2), zeros(2)
        (refyield[0], refrate[0], exponent[0], fixedrate[0],
         refyield[1], refrate[1], exponent[1], fixedrate[1]) = self.rates[self.code]

        # Worksheet steps 1, 2: Continuous rating base rate
        self.baseRate[:] = (
            min(max(round(self.aphyield / refyield[0], 2), 0.5), 1.5),
            min(max(round(self.aphyield / refyield[1], 2), 0.5), 1.5))

        # step 2.02
        self.baseRate = (self.baseRate ** exponent).round(8)

        # step 2.03
        self.baseRate = (self.highRisk + self.baseRate * refrate + fixedrate).round(8)
        if self.rtype > 1.5:
            self.baseRate[:] = self.highRisk
        self.revLook[:] = self.baseRate

    def set_base_prem_rates(self):
        """
        Set adjusted base premium rates
        """
        # Worksheet step 8.  Calculate Base Premium Rates Adjusted Base Rate x
        # coverage level rate differential.
        # step 2.04
        prod = self.baseRate * self.rateDiffFac
        self.basePremRate = (prod * self.uFactor).round(8)
        self.basePremRateE = (prod * self.eFactor).round(8)
        self.basePremRateErev = (prod * self.eFactorRev).round(8)

    def limit_base_prem_rates(self):
        """
        Limit base premium rates based on previous
        """
        # Worksheet step 5, 6.  Preliminary base rate is min of cur and 1.2*prev.
        # step 2.05
        for var in (self.basePremRate, self.basePremRateE, self.basePremRateErev):
            if var[0] > var[1] * 1.2:
                var[0] = round(var[1] * 1.2, 8)
            if var[0] > 0.99:
                var[0] = 0

    def limit_revlook(self):
        """
        Limit revenue lookup based on previous
        """
        # step 2.06
        if self.revLook[0] > self.revLook[1] * 1.2:
            self.revLook[0] = round(self.revLook[1] * 1.2, 8)
        self.revLook[0] = round(min(self.revLook[0], 0.9999), 4)

    def limit_baserate(self):
        """
        Limit base rate based on previous
        """
        # step 2.07
        if self.baseRate[0] > self.baseRate[1] * 1.2:
            self.baseRate[0] = round(self.baseRate[1] * 1.2, 8)

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

    def set_qtys(self):
        """
        Compute mQty and stdQty
        """
        prod = self.revLook[0] * 10000
        revLookup = [
            int(prod + 0.5),
            int(prod * self.discountBasic[3, self.jSize] + 0.5),
            int(prod * self.discountEnter[3, self.jSize] + 0.5)]
        self.mQty, self.stdQty = zip(*(self.rev_lookup[k] for k in revLookup))

    def simulate_losses(self, policy):
        """
        Loop through 500 yieldDraw values, incrementing losses.
        """
        # step 5.02
        self.adjMeanQty = round(self.revYield * self.mQty[policy] / 100, 8)
        self.adjStdQty = round(self.revYield * self.stdQty[policy] / 100, 8)
        self.lnMean = round(log(self.aphPrice) - (self.pvol ** 2 / 2), 8)
        # step 5.04 simulate losses
        simYieldLoss, simRevLoss, simRevExcLoss = 0, 0, 0
        for yieldDraw, priceDraw in self.selected_draws:
            # yield insurance
            yld = max(0, yieldDraw * self.adjStdQty + self.adjMeanQty)
            loss = max(0, self.revYield * self.revCov - yld)
            simYieldLoss += loss
            # revenue insurance
            harPrice = min(2 * self.aphPrice,
                           exp(priceDraw * self.pvol + self.lnMean))
            guarPrice = max(harPrice, self.aphPrice)
            loss = max(0, self.revYield * guarPrice * self.revCov - yld * harPrice)
            simRevLoss += loss
            # revenue insurance with exclusion
            loss = max(0, self.revYield * self.aphPrice * self.revCov - yld * harPrice)
            simRevExcLoss += loss
        # step 5.05
        ct = len(self.selected_draws)
        self.simYpLoss = round((simYieldLoss / ct) / (self.revYield * self.revCov), 8)
        self.simRpLoss = round(simRevLoss / ct /
                               (self.revYield * self.revCov * self.aphPrice), 8)
        self.simRpExcLoss = round(simRevExcLoss / ct /
                                  (self.revYield * self.revCov * self.aphPrice), 8)

    def set_rates(self):
        """
        Set the premium rates
        """
        # step 5.06
        revRate = round(max(0.01 * self.basePremRate[0],
                            self.simRpLoss - self.simYpLoss), 8)
        revExcRate = round(max(-0.5 * self.basePremRate[0],
                               self.simRpExcLoss - self.simYpLoss), 8)
        # step 6  No historical revenue capping is performed
        self.revRateUse, self.revRateEntUse = revRate, revRate
        self.revExcRateUse, self.revExcRateEntUse = revExcRate, revExcRate
        # step 8.01
        self.premRateO = self.basePremRate[0] * self.multFactor
        self.premRateB = self.basePremRate[0] * self.multFactor * self.disBasic
        self.premRateE = self.basePremRateE[0] * self.multFactor * self.disEnter
        self.premRateErev = self.basePremRateErev[0] * self.multFactor * self.disEnter

    def set_prem(self, rate, i, j, rateuse=0):
        """
        Set a premium with given rate, indices and optional rateuse
        """
        self.prem[i, j] = round(self.liab * round(rate + rateuse, 8), 0)

    def set_prems(self, i, policy):
        """
        Set the pre-subsidy premiums
        """
        if policy == 0:  # optional policies
            self.set_prem(self.premRateO, i, 0, self.revRateUse)           # rp
            self.set_prem(self.premRateO, i, 3, self.revExcRateUse)        # rpexc
            self.set_prem(self.premRateO, i, 6)                            # yp
        if policy == 1:  # basic policy
            self.set_prem(self.premRateB, i, 1, self.revRateUse)           # rp
            self.set_prem(self.premRateB, i, 4, self.revExcRateUse)        # rpexc
            self.set_prem(self.premRateB, i, 7)                            # yp
        if policy == 2:   # enterprise policy
            self.set_prem(self.premRateErev, i, 2, self.revRateEntUse)     # rp
            self.set_prem(self.premRateErev, i, 5, self.revExcRateEntUse)  # rpexc
            self.set_prem(self.premRateE, i, 8)                            # yp

    def apply_subsidy(self, i):
        """
        Apply the subsidy
        """
        for j in range(9):
            self.prem[i, j] -= round(self.prem[i, j] *
                                     self.subsidy[i, 1 if j % 3 == 2 else 0], 0)
            self.prem[i, j] = round(self.prem[i, j] / self.acre, 2)

    # -----------------------------
    # MAIN METHOD: COMPUTE PREMIUMS
    # -----------------------------
    def compute_premiums(self, aphyield=180, apprYield=180, tayield=190, acre=100,
                         aphPrice=5.91, pvol=0.18, hf=0, pf=0, riskname='None',
                         tause=1, ye=0, county='Champaign, IL', crop='Corn',
                         practice='Non-irrigated', atype='Grain'):
        """
        Given user information, compute premiums for enterprise, optional and basic
        units with RP, RP-HPE or YO protection.
        """
        self.store_user_settings(aphyield, apprYield, tayield, acre, aphPrice,
                                 pvol, hf, pf, riskname, tause, ye, county,
                                 crop, practice, atype)
        self.initialize_arrays()
        self.set_multfactor()
        for i in range(8):
            # index i corresponds to coverage level
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
                #  Loop for units (0=optional, 1=basic, 2=enterprise)
                for policy in range(3):
                    # section 5 revenue calculation
                    self.simulate_losses(policy)
                    self.set_rates()
                    self.set_prems(i, policy)
                self.apply_subsidy(i)
        return self.prem


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
    # draws = {k: tuple(zip(*v)) for k, v in draws.items()}
    # return {k: (np.array(v[0]), np.array(v[1])) for k, v in draws.items()}


def get_discount_basic():
    items = get_file_items('data/discountBasic.txt')
    return {int(itm[0]): np.array([float(it) for it in itm[1:]]).reshape(8, 6)
            for itm in items}


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
