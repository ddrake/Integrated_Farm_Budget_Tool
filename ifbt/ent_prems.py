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
        np.set_printoptions(precision=2)
        np.set_printoptions(suppress=True)

    def load_lookups(self):
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
        self.subsidy = array([[0.67, 0.64, 0.64, 0.59, 0.59, 0.55, 0.48, 0.38],
                              [0.8,  0.8,  0.8,  0.8,  0.8,  0.77, 0.68, 0.53]]).T

    def make_code(self, county, crop, atype, practice):
        """
        Construct an integer code used to key in some tabular data
        """
        return int(f'{self.counties[county]}{self.crops[crop]}' +
                   f'{self.types[atype]}{self.practices[practice]}')

    def compute_premiums(self, aphyield=180, apprYield=180, tayield=190, acre=100,
                         aphPrice=5.91, pvol=0.18, hf=0, pf=0, highRisk=0, rtype=0,
                         tause=1, ye=0, county='Champaign, IL', crop='Corn',
                         practice='Non-irrigated', atype='Grain'):
        """
        Given user information, compute premiums for enterprise, optional and basic
        units with RP, RP-HPE or YO protection.
        """
        if tayield < aphyield:
            tayield = aphyield

        code = self.make_code(county, crop, atype, practice)
        fcode = code + 0.1
        cover = array([x/100 for x in range(50, 86, 5)])
        # -------------------------------------------------------------------
        # Look up info from the dicts created when the object was constructed
        # -------------------------------------------------------------------
        (refyield, refrate, exponent, fixedrate,
         prefyield, prefrate, pexponent, pfixedrate) = self.rates[code]
        hfrate, pfrate, ptrate = self.options[code]
        betaId = self.beta_id[code]
        enterId = self.enter_id[code]
        discountBasic = self.discount_basic[enterId]
        discountEnter = self.discount_enter[enterId]
        rateDiff = zeros((8, 2))
        rateDiff[:, 0] = self.rate_diff[fcode]
        rateDiff[:, 1] = self.prate_diff[fcode]
        unitFactor = zeros((8, 2))
        unitFactor[:, 0] = self.unit_factor[fcode]
        unitFactor[:, 1] = self.punit_factor[fcode]
        enterpriseFactor = zeros((8, 2))
        enterpriseFactor[:, 0] = self.enterprise_factor[fcode]
        enterpriseFactor[:, 1] = self.penterprise_factor[fcode]
        enterFactorRev = zeros((8, 2))
        enterFactorRev[:, 0] = self.enter_factor_rev[fcode]
        enterFactorRev[:, 1] = self.penter_factor_rev[fcode]
        yieldDraw, priceDraw = self.draws[betaId]

        jSize = (0 if acre < 50 else 1 if acre < 100 else 2 if acre < 200 else
                 3 if acre < 400 else 4 if acre < 800 else 5)

        # will store premiums
        prem = zeros((8, 9))

        for i in range(8):
            # index i corresponds to coverage level
            if rateDiff[i, 0] > 0:
                # Note: if rateDiff[i, 0] were to be negative for some level i,
                # the premiums for that coverage level would be zero (undefined).
                effcov = round(0.0001 + cover[i] * tayield / apprYield, 2)
                jjHigh = 5 if rateDiff[6, 0] == 0 else 7
                # tause = 1 in base case; need to test case tause = 0
                rateDiffFac = (get_factor(rateDiff, effcov, cover, rateDiff, 0, 9)
                               if tause else rateDiff[i, 0])
                pRateDiffFac = (get_factor(rateDiff, effcov, cover, rateDiff, 1, 9)
                                if tause else rateDiff[i, 1])
                uFactor = (get_factor(unitFactor, effcov, cover, rateDiff, 0, 3)
                           if tause else unitFactor[i, 0])
                puFactor = (get_factor(unitFactor, effcov, cover, rateDiff, 1, 3)
                            if tause else unitFactor[i, 1])
                eFactor = (get_factor(enterpriseFactor, effcov, cover, rateDiff, 0, 3)
                           if tause else enterpriseFactor[i, 0])
                peFactor = (get_factor(enterpriseFactor, effcov, cover, rateDiff, 1, 3)
                            if tause else enterpriseFactor[i, 1])
                eFactorRev = (get_factor(enterFactorRev, effcov, cover, rateDiff, 0, 3)
                              if tause else enterFactorRev[i, 0])
                peFactorRev = (get_factor(enterFactorRev, effcov, cover, rateDiff, 1, 3)
                               if tause else enterFactorRev[i, 1])
                disBasic = (get_factor(discountBasic, effcov, cover, rateDiff, jSize, 4)
                            if tause else discountBasic[i, jSize])
                disEnter = (get_factor(discountEnter, effcov, cover, rateDiff, jSize, 4)
                            if tause else discountEnter[i, jSize])
                # code for YE adj
                yeAdj = 0
                if effcov > 0.85:
                    if ye > 0.5:
                        yeAdj = (effcov - 0.85) / 0.15
                    yeAdj = 1 + round(min(1, yeAdj) ** 3, 7) * 0.05
                    rateDiffFac *= yeAdj
                    uFactor = min(uFactor, unitFactor[jjHigh, 0])
                    puFactor = min(puFactor, unitFactor[jjHigh, 1])
                    eFactor = min(eFactor, enterpriseFactor[jjHigh, 0])
                    peFactor = min(peFactor, enterpriseFactor[jjHigh, 1])
                # step 1
                revYield = apprYield if tause < 0.5 else tayield
                liab = round(revYield * cover[i] + 0.001, 1) * aphPrice * acre
                revCov = cover[i] if tause < 0.5 else effcov
                liab = round(liab, 0)
                # step 2.01
                baseRate = min(max(round(aphyield / refyield, 2), 0.5), 1.5)
                pbaseRate = min(max(round(aphyield / prefyield, 2), 0.5), 1.5)
                # step 2.02
                baseRate = round(baseRate ** exponent, 8)
                pbaseRate = round(pbaseRate ** pexponent, 8)
                # step 2.03
                baseRate = round(highRisk + (baseRate * refrate) + fixedrate, 8)
                if rtype > 1.5:
                    baseRate = highRisk
                revLook = baseRate
                pbaseRate = round(highRisk + (pbaseRate * prefrate) + pfixedrate, 8)
                if rtype > 1.5:
                    pbaseRate = highRisk
                prevLook = pbaseRate
                # step 2.04
                basePremRate = round(baseRate * rateDiffFac * uFactor, 8)
                pbasePremRate = round(pbaseRate * pRateDiffFac * puFactor, 8)
                basePremRateE = round(baseRate * rateDiffFac * eFactor, 8)
                pbasePremRateE = round(pbaseRate * pRateDiffFac * peFactor, 8)
                basePremRateErev = round(baseRate * rateDiffFac * eFactorRev, 8)
                pbasePremRateErev = round(pbaseRate * pRateDiffFac * peFactorRev, 8)
                # step 2.05
                if basePremRate > pbasePremRate * 1.2:
                    basePremRate = round(pbasePremRate * 1.2, 8)
                if basePremRate > 0.99:
                    basePremRate = 0  # Not 1?  Smells fishy...
                if basePremRateE > pbasePremRateE * 1.2:
                    basePremRateE = round(pbasePremRateE * 1.2, 8)
                if basePremRateE > 0.99:
                    basePremRateE = 0
                if basePremRateErev > pbasePremRateErev * 1.2:
                    basePremRateErev = round(pbasePremRateErev * 1.2, 8)
                if basePremRateErev > 0.99:
                    basePremRateErev = 0
                # step 2.06
                if revLook > prevLook * 1.2:
                    revLook = round(prevLook * 1.2, 8)
                revLook = round(min(revLook, 0.9999), 4)
                # step 2.07
                if baseRate > pbaseRate * 1.2:
                    baseRate = round(pbaseRate * 1.2, 8)
                # options factor
                multFactor = 1
                if hf > 0:
                    multFactor *= hfrate
                if pf == 1:
                    multFactor *= pfrate
                if pf == 2:
                    multFactor *= ptrate
                # Compute three codes to look up mQty, stdQty
                revLookup = [
                    int(revLook * 10000 + 0.5),
                    int(revLook * discountBasic[3, jSize] * 10000 + 0.5),
                    int(revLook * discountEnter[3, jSize] * 10000 + 0.5)]
                mQty, stdQty = zip(*(self.rev_lookup[k] for k in revLookup))
                # step 5.01
                #  Loop for units (0=optional, 1=basic, 2=enterprise)
                for ii in range(3):
                    # section 5 revenue calculation
                    # step 5.02
                    adjMeanQty = round(revYield * mQty[ii] / 100, 8)
                    adjStdQty = round(revYield * stdQty[ii] / 100, 8)
                    lnMean = round(log(aphPrice) - (pvol ** 2 / 2), 8)
                    # step 5.04 simulate losses
                    simYieldLoss = 0
                    simRevLoss = 0
                    simRevExcLoss = 0
                    for j in range(500):
                        # yield insurance
                        yld = max(0, yieldDraw[j] * adjStdQty + adjMeanQty)
                        loss = max(0, revYield * revCov - yld)
                        simYieldLoss += loss
                        # revenue insurance
                        harPrice = min(2 * aphPrice, exp(priceDraw[j] * pvol + lnMean))
                        guarPrice = max(harPrice, aphPrice)
                        loss = max(0, revYield * guarPrice * revCov - yld * harPrice)
                        simRevLoss += loss
                        # revenue insurance with exclusion
                        loss = max(0, revYield * aphPrice * revCov - yld * harPrice)
                        simRevExcLoss += loss
                    # step 5.05
                    simYpLoss = round((simYieldLoss / 500) / (revYield * revCov), 8)
                    simRpLoss = round(simRevLoss / 500 /
                                      (revYield * revCov * aphPrice), 8)
                    simRpExcLoss = round(simRevExcLoss / 500 /
                                         (revYield * revCov * aphPrice), 8)
                    # step 5.06
                    revRate = round(max(0.01 * basePremRate, simRpLoss - simYpLoss), 8)
                    revExcRate = round(max(-0.5 * basePremRate,
                                           simRpExcLoss - simYpLoss), 8)
                    # step 6 calculation of historical revenue capping
                    # since krecord = 0, cHisRec = 0 so the if block was removed
                    revRateUse = revRate
                    revRateEntUse = revRate
                    revExcRateUse = revExcRate
                    revExcRateEntUse = revExcRate
                    # step 8.01
                    premRateO = basePremRate * multFactor
                    premRateB = basePremRate * multFactor * disBasic
                    premRateE = basePremRateE * multFactor * disEnter
                    premRateErev = basePremRateErev * multFactor * disEnter
                    if ii == 0:  # optional policies
                        # rp optional
                        prem[i, 0] = round(liab * round(premRateO + revRateUse, 8), 0)
                        # rpexc optional
                        prem[i, 3] = round(liab *
                                           round(premRateO + revExcRateUse, 8), 0)
                        # yp optional
                        prem[i, 6] = round(liab * round(premRateO, 8), 0)
                    if ii == 1:  # basic policy
                        # rp basic
                        prem[i, 1] = round(liab * round(premRateB + revRateUse, 8), 0)
                        # rpexc basic
                        prem[i, 4] = round(liab *
                                           round(premRateB + revExcRateUse, 8), 0)
                        # yp basic
                        prem[i, 7] = round(liab * round(premRateB, 8), 0)
                    if ii == 2:   # enterprise policy
                        # rp enterprise
                        prem[i, 2] = round(liab *
                                           round(premRateErev + revRateEntUse, 8), 0)
                        # rpexc enterprise
                        prem[i, 5] = round(liab *
                                           round(premRateErev + revExcRateEntUse, 8), 0)
                        # yp enterprise
                        prem[i, 8] = round(liab * round(premRateE, 8), 0)
                for j in range(9):
                    prem[i, j] -= round(prem[i, j] *
                                        self.subsidy[i, 1 if j % 3 == 2 else 0], 0)
                for j in range(9):
                    prem[i, j] = round(prem[i, j] / acre, 2)
                # end large if block
            # end coverage level i loop
        return prem


def get_factor(var, ecv, cv, rd, j2, ro):
    """
    Given a variable (e.g. rateDiff), effcov, cover, rateDiff, a 2nd index
    and a roundoff precision, first compute some indices, then use them to get a
    factor (e.g. rateDiffFac)
    """
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
