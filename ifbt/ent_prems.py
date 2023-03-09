from numpy import zeros, array
import numpy as np
from math import log, exp


class EntPrems:
    """
    Compute premiums for optional, basic and enterprise unit crop insurance
    """
    # TODO: aphyield and apprYield seem to be switched in the code!!
    # TODO: Which states should we support?
    # TODO: Which crops should we support?
    # TODO: Try to import parameters (it's a mess).
    # Note: UnitFactor.txt has column calc_year with values 2023.
    # Note: There is an unusual level of intermediate rounding in the original code.
    #       It has been preserved here, but should perhaps be questioned.
    # TODO: Should we do anything with the risk classes?
    # The Risk Class drop-down has 4 invisible options under None, I think.
    # locat2 = locat + 0.1 + (0.2 if riskTest == 'AAA' else
    #                         0.3 if riskTest == 'BBB' else
    #                         0.4 if riskTest == 'CCC' else
    #                         0.5 if riskTest == 'DDD' else 0)

    def __init__(self):
        self.load_lookups()
        self.subsidy = array([[0.67, 0.64, 0.64, 0.59, 0.59, 0.55, 0.48, 0.38],
                              [0.8,  0.8,  0.8,  0.8,  0.8,  0.77, 0.68, 0.53]]).T
        self.discountBasic = None
        self.discountEnter = None
        self.rateDiff = None
        self.unitFactor = zeros(2)
        self.enterpriseFactor = None
        self.enterFactorRev = None
        self.yieldDraw = None
        self.priceDraw = None
        self.jSize = None
        self.effcov = None
        self.rateDiffFac = zeros(2)
        self.uFactor = zeros(2)
        self.eFactor = zeros(2)
        self.eFactorRev = zeros(2)
        self.disBasic = None
        self.disEnter = None
        self.baseRate = zeros(2)
        self.revLook = zeros(2)
        self.basePremRate = zeros(2)
        self.basePremRateE = zeros(2)
        self.RateDiffFac = zeros(2)
        self.basePremRateErev = zeros(2)
        np.set_printoptions(precision=2)
        np.set_printoptions(suppress=True)

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

    def make_code(self, county, crop, atype, practice):
        """
        Construct an integer code used to key in some tabular data
        """
        return int(f'{self.counties[county]}{self.crops[crop]}' +
                   f'{self.types[atype]}{self.practices[practice]}')

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
        # TODO: tause = 1 in base case; need to test case tause = 0
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
        self.revYield = self.apprYield if self.tause < 0.5 else self.tayield
        self.revCov = self.cover[i] if self.tause < 0.5 else self.effcov
        self.liab = round(round(self.revYield * self.cover[i] + 0.001, 1) *
                          self.aphPrice * self.acre, 0)

    def set_base_rates(self):
        """
        Set and limit base rates
        """
        # step 2.01
        refyield, refrate, exponent, fixedrate = zeros(2), zeros(2), zeros(2), zeros(2)
        (refyield[0], refrate[0], exponent[0], fixedrate[0],
         refyield[1], refrate[1], exponent[1], fixedrate[1]) = self.rates[self.code]

        self.baseRate[:] = (
            min(max(round(self.aphyield / refyield[0], 2), 0.5), 1.5),
            min(max(round(self.aphyield / refyield[1], 2), 0.5), 1.5))
        # step 2.02
        self.baseRate = (self.baseRate ** exponent).round(8)
        # step 2.03

        # TODO: Get this working to replace the rest of the method
        # self.baseRate = (self.highRisk +
        #                  (self.baseRate + refrate + fixedrate)).round(8)
        # if self.rtype > 1.5:
        #     self.baseRate[:] = self.highRisk
        # self.revLook = self.baseRate

        self.baseRate[0] = round(
            self.highRisk + (self.baseRate[0] * refrate[0]) + fixedrate[0], 8)
        if self.rtype > 1.5:
            self.baseRate[0] = self.highRisk
        self.revLook[0] = self.baseRate[0]

        self.baseRate[1] = round(
            self.highRisk + (self.baseRate[1] * refrate[1]) + fixedrate[1], 8)
        if self.rtype > 1.5:
            self.baseRate[1] = self.highRisk
        self.revLook[1] = self.baseRate[1]

    def set_base_prem_rates(self):
        """
        Set base premium rates
        """
        # step 2.04
        self.basePremRate = (self.baseRate * self.rateDiffFac * self.uFactor).round(8)
        self.basePremRateE = (self.baseRate * self.rateDiffFac * self.eFactor).round(8)
        self.basePremRateErev = (self.baseRate *
                                 self.rateDiffFac * self.eFactorRev).round(8)

    def limit_base_prem_rates(self):
        """
        Limit base premium rates
        """
        # step 2.05
        if self.basePremRate[0] > self.basePremRate[1] * 1.2:
            self.basePremRate[0] = round(self.basePremRate[1] * 1.2, 8)
        if self.basePremRate[0] > 0.99:
            self.basePremRate[0] = 0  # Not 1?  Smells fishy...
        if self.basePremRateE[0] > self.basePremRateE[1] * 1.2:
            self.basePremRateE[0] = round(self.basePremRateE[1] * 1.2, 8)
        if self.basePremRateE[0] > 0.99:
            self.basePremRateE[0] = 0
        if self.basePremRateErev[0] > self.basePremRateErev[1] * 1.2:
            self.basePremRateErev[0] = round(self.basePremRateErev[1] * 1.2, 8)
        if self.basePremRateErev[0] > 0.99:
            self.basePremRateErev[0] = 0

    def limit_revlook(self):
        """
        Limit revenue lookup
        """
        # step 2.06
        if self.revLook[0] > self.revLook[1] * 1.2:
            self.revLook[0] = round(self.revLook[1] * 1.2, 8)
        self.revLook[0] = round(min(self.revLook[0], 0.9999), 4)

    def limit_baserate(self):
        """
        Limit base rate
        """
        # step 2.07
        if self.baseRate[0] > self.baseRate[1] * 1.2:
            self.baseRate[0] = round(self.baseRate[1] * 1.2, 8)

    def set_multfactor(self):
        """
        Set multFactor
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
        revLookup = [
            int(self.revLook[0] * 10000 + 0.5),
            int(self.revLook[0] * self.discountBasic[3, self.jSize] * 10000 + 0.5),
            int(self.revLook[0] * self.discountEnter[3, self.jSize] * 10000 + 0.5)]
        self.mQty, self.stdQty = zip(*(self.rev_lookup[k] for k in revLookup))

    def simulate_losses(self, policy):
        # step 5.02
        self.adjMeanQty = round(self.revYield * self.mQty[policy] / 100, 8)
        self.adjStdQty = round(self.revYield * self.stdQty[policy] / 100, 8)
        self.lnMean = round(log(self.aphPrice) - (self.pvol ** 2 / 2), 8)
        # step 5.04 simulate losses
        simYieldLoss = 0
        simRevLoss = 0
        simRevExcLoss = 0
        for j in range(500):
            # yield insurance
            yld = max(0, self.yieldDraw[j] * self.adjStdQty + self.adjMeanQty)
            loss = max(0, self.revYield * self.revCov - yld)
            simYieldLoss += loss
            # revenue insurance
            harPrice = min(2 * self.aphPrice,
                           exp(self.priceDraw[j] * self.pvol + self.lnMean))
            guarPrice = max(harPrice, self.aphPrice)
            loss = max(0, self.revYield * guarPrice * self.revCov - yld * harPrice)
            simRevLoss += loss
            # revenue insurance with exclusion
            loss = max(0, self.revYield * self.aphPrice * self.revCov - yld * harPrice)
            simRevExcLoss += loss
        # step 5.05
        self.simYpLoss = round((simYieldLoss / 500) / (self.revYield * self.revCov), 8)
        self.simRpLoss = round(simRevLoss / 500 /
                               (self.revYield * self.revCov * self.aphPrice), 8)
        self.simRpExcLoss = round(simRevExcLoss / 500 /
                                  (self.revYield * self.revCov * self.aphPrice), 8)

    def set_rates(self):
        # step 5.06
        revRate = round(max(0.01 * self.basePremRate[0],
                            self.simRpLoss - self.simYpLoss), 8)
        revExcRate = round(max(-0.5 * self.basePremRate[0],
                               self.simRpExcLoss - self.simYpLoss), 8)
        # step 6 calculation of historical revenue capping
        # since krecord = 0, cHisRec = 0 so the if block was removed
        self.revRateUse = revRate
        self.revRateEntUse = revRate
        self.revExcRateUse = revExcRate
        self.revExcRateEntUse = revExcRate
        # step 8.01
        self.premRateO = self.basePremRate[0] * self.multFactor
        self.premRateB = self.basePremRate[0] * self.multFactor * self.disBasic
        self.premRateE = self.basePremRateE[0] * self.multFactor * self.disEnter
        self.premRateErev = self.basePremRateErev[0] * self.multFactor * self.disEnter

    def set_prems(self, i, policy):
        if policy == 0:  # optional policies
            # rp optional
            self.prem[i, 0] = round(self.liab *
                                    round(self.premRateO + self.revRateUse, 8), 0)
            # rpexc optional
            self.prem[i, 3] = round(self.liab *
                                    round(self.premRateO + self.revExcRateUse, 8), 0)
            # yp optional
            self.prem[i, 6] = round(self.liab * round(self.premRateO, 8), 0)
        if policy == 1:  # basic policy
            # rp basic
            self.prem[i, 1] = round(self.liab *
                                    round(self.premRateB + self.revRateUse, 8), 0)
            # rpexc basic
            self.prem[i, 4] = round(self.liab *
                                    round(self.premRateB + self.revExcRateUse, 8), 0)
            # yp basic
            self.prem[i, 7] = round(self.liab * round(self.premRateB, 8), 0)
        if policy == 2:   # enterprise policy
            # rp enterprise
            self.prem[i, 2] = round(self.liab *
                                    round(self.premRateErev + self.revRateEntUse, 8), 0)
            # rpexc enterprise
            self.prem[i, 5] = round(self.liab *
                                    round(self.premRateErev +
                                          self.revExcRateEntUse, 8), 0)
            # yp enterprise
            self.prem[i, 8] = round(self.liab * round(self.premRateE, 8), 0)

    def apply_subsidy(self, i):
        for j in range(9):
            self.prem[i, j] -= round(self.prem[i, j] *
                                     self.subsidy[i, 1 if j % 3 == 2 else 0], 0)
        for j in range(9):
            self.prem[i, j] = round(self.prem[i, j] / self.acre, 2)

    def compute_premiums(self, aphyield=180, apprYield=180, tayield=190, acre=100,
                         aphPrice=5.91, pvol=0.18, hf=0, pf=0, highRisk=0, rtype=0,
                         tause=1, ye=0, county='Champaign, IL', crop='Corn',
                         practice='Non-irrigated', atype='Grain'):
        """
        Given user information, compute premiums for enterprise, optional and basic
        units with RP, RP-HPE or YO protection.
        """
        self.aphyield = aphyield
        self.apprYield = apprYield
        self.tayield = tayield
        self.acre = acre
        self.aphPrice = aphPrice
        self.pvol = pvol
        self.hf = hf
        self.pf = pf
        self.highRisk = highRisk
        self.rtype = rtype
        self.tause = tause
        self.ye = ye

        if self.tayield < self.aphyield:
            self.tayield = self.aphyield

        self.code = self.make_code(county, crop, atype, practice)
        self.fcode = self.code + 0.1
        self.cover = array([x/100 for x in range(50, 86, 5)])
        # -------------------------------------------------------------------
        # Look up info from the dicts created when the object was constructed
        # -------------------------------------------------------------------
        enterId = self.enter_id[self.code]
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
        # self.enterFactorRev = zeros((8, 2))
        # self.enterFactorRev[:, 0] = self.enter_factor_rev[self.fcode]
        # self.enterFactorRev[:, 1] = self.penter_factor_rev[self.fcode]
        betaId = self.beta_id[self.code]
        self.yieldDraw, self.priceDraw = self.draws[betaId]

        self.jSize = (0 if self.acre < 50 else 1 if self.acre < 100 else
                      2 if self.acre < 200 else 3 if self.acre < 400 else
                      4 if self.acre < 800 else 5)

        # will store premiums
        self.prem = zeros((8, 9))
        self.set_multfactor()
        for i in range(8):
            # index i corresponds to coverage level
            if self.rateDiff[i, 0] > 0:
                # Note: rateDiff[i, 0] would result in zero premiums for level.
                self.effcov = round(0.0001 + self.cover[i] *
                                    self.tayield / self.apprYield, 2)
                self.set_factors(i)
                self.make_ye_adj()
                self.make_rev_liab(i)
                self.set_base_rates()
                self.set_base_prem_rates()
                self.limit_base_prem_rates()
                self.limit_revlook()
                # Note: each pass, we set the base rates, use them to get base prem
                # rates, then limit the base rates. Can this be improved?
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
    draws = {k: tuple(zip(*v)) for k, v in draws.items()}
    return {k: (np.array(v[0]), np.array(v[1])) for k, v in draws.items()}


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
