from numpy import zeros, array
import numpy as np
from math import log, exp


class EntPrems:
    # TODO: aphyield and apprYield seem to be switched in the code!!
    # TODO: Which states should we support?
    # TODO: Which crops should we support?
    # TODO: Should we do anything with the risk classes?
    # TODO: Try to import parameters
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
        return int(f'{self.counties[county]}{self.crops[crop]}' +
                   f'{self.types[atype]}{self.practices[practice]}')

    def compute_premiums(self, aphyield=180, apprYield=180, tayield=190,
                         acre=100, aphPrice=5.91, pvol=0.18, hf=0,
                         pf=0, highRisk=0, rtype=0, tause=1, ye=0,
                         county='Champaign, IL', crop='Corn',
                         practice='Non-irrigated', atype='Grain'):

        if tayield < aphyield:
            tayield = aphyield

        code = self.make_code(county, crop, atype, practice)
        fcode = code + 0.1
        print('code', code, 'fcode', fcode)

        cover = array([x/100 for x in range(50, 86, 5)])

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

        # prem: numpy array to store final premiums
        prem = zeros((8, 9))

        for i in range(8):
            if rateDiff[i, 0] > 0:
                effcov = round(0.0001 + cover[i] * tayield / apprYield, 2)

                jjHigh = 5 if rateDiff[6, 0] == 0 else 7

                # tause = 1 in base case
                if tause < 0.5:
                    rateDiffFac = rateDiff[i, 0]
                    pRateDiffFac = rateDiff[i, 1]
                    uFactor = unitFactor[i, 0]
                    puFactor = unitFactor[i, 1]
                    eFactor = enterpriseFactor[i, 0]
                    peFactor = enterpriseFactor[i, 1]
                    eFactorRev = enterFactorRev[i, 0]
                    peFactorRev = enterFactorRev[i, 1]
                    disBasic = discountBasic[i, jSize]
                    disEnter = discountEnter[i, jSize]
                else:
                    rateDiffFac = get_factor(rateDiff, effcov, cover, rateDiff, 0, 9)
                    pRateDiffFac = get_factor(rateDiff, effcov, cover, rateDiff, 1, 9)
                    uFactor = get_factor(unitFactor, effcov, cover, rateDiff, 0, 3)
                    puFactor = get_factor(unitFactor, effcov, cover, rateDiff, 1, 3)
                    eFactor = get_factor(enterpriseFactor, effcov,
                                         cover, rateDiff, 0, 3)
                    peFactor = get_factor(enterpriseFactor, effcov,
                                          cover, rateDiff, 1, 3)
                    eFactorRev = get_factor(enterFactorRev, effcov,
                                            cover, rateDiff, 0, 3)
                    peFactorRev = get_factor(enterFactorRev, effcov,
                                             cover, rateDiff, 1, 3)
                    disBasic = get_factor(discountBasic, effcov,
                                          cover, rateDiff, jSize, 4)
                    disEnter = get_factor(discountEnter, effcov,
                                          cover, rateDiff, jSize, 4)

                # new code for YE adj
                yeAdj = 0  # vba code declares, but doesn't initialize
                if effcov > 0.85:
                    if ye > 0.5:
                        yeAdj = (effcov - 0.85) / 0.15
                    if yeAdj > 1:
                        yeAdj = 1
                    yeAdj = round(yeAdj ** 3, 7)
                    yeAdj = 1 + yeAdj * 0.05
                    rateDiffFac = rateDiffFac * yeAdj

                    uFactor = min(uFactor, unitFactor[jjHigh, 0])
                    puFactor = min(puFactor, unitFactor[jjHigh, 1])
                    eFactor = min(eFactor, enterpriseFactor[jjHigh, 0])
                    peFactor = min(peFactor, enterpriseFactor[jjHigh, 1])

                # step 1
                revYield = apprYield if tause < 0.5 else tayield
                liab = round(revYield * cover[i] + 0.001, 1) * aphPrice * acre
                revCov = cover[i] if tause < 0.5 else effcov

                # Change -- the following line was added
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
                    basePremRate = 0
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

                # Computes three codes based on revLook: e.g. [162, 111, 111]
                revLookup = array(
                    [int(revLook * 10000 + 0.5),
                     int(revLook * discountBasic[3, jSize] * 10000 + 0.5),
                     int(revLook * discountEnter[3, jSize] * 10000 + 0.5)])

                mQty, stdQty = zip(*(self.rev_lookup[k] for k in revLookup))

                # step 5.01
                #  Loop for units
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

        return prem


def get_factor(var, ecv, cv, rd, j2, ro):
    jlow = (0 if ecv < 0.55 else 1 if ecv < 0.6 else
            2 if ecv < 0.65 else 3 if ecv < 0.7 else
            4 if ecv < 0.75 else 5 if ecv < 0.8 else 6)
    jhigh = (0 if ecv < 0.5 else 1 if ecv < 0.55 else
             2 if ecv < 0.6 else 3 if ecv < 0.65 else
             4 if ecv < 0.7 else 5 if ecv < 0.75 else
             6 if ecv < 0.8 else 7)
    jfloor = (0 if ecv < 0.55 else 1 if ecv < 0.6 else
              2 if ecv < 0.65 else 3 if ecv < 0.7 else
              4 if ecv < 0.75 else 5 if ecv < 0.8 else
              6 if ecv < 0.85 else 7)

    if ecv > 0.75 and rd[6, 0] == 0:
        jlow = 4
        jhigh = 5
        jfloor = 5

    return round(
        var[jfloor, j2] +
        (var[jhigh, j2] - var[jlow, j2]) *
        (ecv - cv[jfloor]) * 20 + 0.00000000001, ro)


def get_enter_id():
    with open('data/enterId.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    enter_id = {int(code): int(unitId) for code, unitId in items}
    return enter_id


def get_beta_id():
    with open('data/betaid.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    beta_id = {int(code): int(betaId) for code, betaId in items}
    return beta_id


def get_options():
    with open('data/options.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    rates = {int(code): (float(hf), float(pf), float(pt))
             for code, hf, pf, pt, _ in items}
    return rates


def get_rates():
    with open('data/rates.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    rates = {int(code): (float(refyld), float(refrate), float(expon),
                         float(fixrate), float(prefyield), float(prefrate),
                         float(pexpon), float(pfixrate))
             for code, refyld, refrate, expon, fixrate, prefyield,
             prefrate, pexpon, pfixrate in items}
    return rates


def get_rate_diff():
    with open('data/rateDiff.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    rate_diff = {float(fcode): (float(c50), float(c55), float(c60),
                 float(c65), float(c70), float(c75), float(c80), float(c85))
                 for fcode, c50, c55, c60, c65, c70, c75, c80, c85 in items}
    return rate_diff


def get_prate_diff():
    with open('data/prateDiff.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    prate_diff = {float(fcode): (float(c50), float(c55), float(c60),
                  float(c65), float(c70), float(c75), float(c80), float(c85))
                  for fcode, c50, c55, c60, c65, c70, c75, c80, c85 in items}
    return prate_diff


def get_unit_factor():
    with open('data/UnitFactor.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    unit_factor = {float(fcode): (float(c50), float(c55), float(c60),
                   float(c65), float(c70), float(c75), float(c80), float(c85))
                   for fcode, idd, yr, c50, c55, c60, c65, c70, c75, c80, c85 in items}
    return unit_factor


def get_punit_factor():
    with open('data/punitFactor.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    punit_factor = {float(fcode): (float(c50), float(c55), float(c60),
                    float(c65), float(c70), float(c75), float(c80), float(c85))
                    for fcode, c50, c55, c60, c65, c70, c75, c80, c85 in items}
    return punit_factor


def get_enterprise_factor():
    with open('data/enterpriseFactor.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    enterprise_factor = {float(fcode): (float(c50), float(c55), float(c60),
                         float(c65), float(c70), float(c75), float(c80), float(c85))
                         for fcode, c50, c55, c60, c65, c70, c75, c80, c85 in items}
    return enterprise_factor


def get_penterprise_factor():
    with open('data/penterpriseFactor.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    penterprise_factor = {float(fcode): (float(c50), float(c55), float(c60),
                          float(c65), float(c70), float(c75), float(c80), float(c85))
                          for fcode, c50, c55, c60, c65, c70, c75, c80, c85 in items}
    return penterprise_factor


def get_enter_factor_rev():
    with open('data/enterFactorRev.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    enter_factor_rev = {float(fcode): (float(c50), float(c55), float(c60),
                        float(c65), float(c70), float(c75), float(c80), float(c85))
                        for fcode, c50, c55, c60, c65, c70, c75, c80, c85 in items}
    return enter_factor_rev


def get_penter_factor_rev():
    with open('data/pEnterFactorRev.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    penter_factor_rev = {float(fcode): (float(c50), float(c55), float(c60),
                         float(c65), float(c70), float(c75), float(c80), float(c85))
                         for fcode, c50, c55, c60, c65, c70, c75, c80, c85 in items}
    return penter_factor_rev


def get_rev_lookup():
    with open('data/revLookup.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    rev_lookup = {int(code): (float(qty), float(std)) for code, qty, std in items}
    return rev_lookup


def get_draws():
    draws = {}
    with open('data/draws.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    for code, _, yielddraw, pricedraw in items:
        draws.setdefault(int(code), []).append((float(yielddraw), float(pricedraw)))
    draws = {k: tuple(zip(*v)) for k, v in draws.items()}
    return {k: (np.array(v[0]), np.array(v[1])) for k, v in draws.items()}


def get_discount_basic():
    with open('data/discountBasic.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    discounts = {int(code): np.array([
        [float(c50s1), float(c50s2), float(c50s3),
         float(c50s4), float(c50s5), float(c50s6)],
        [float(c55s1), float(c55s2), float(c55s3),
         float(c55s4), float(c55s5), float(c55s6)],
        [float(c60s1), float(c60s2), float(c60s3),
         float(c60s4), float(c60s5), float(c60s6)],
        [float(c65s1), float(c65s2), float(c65s3),
         float(c65s4), float(c65s5), float(c65s6)],
        [float(c70s1), float(c70s2), float(c70s3),
         float(c70s4), float(c70s5), float(c70s6)],
        [float(c75s1), float(c75s2), float(c75s3),
         float(c75s4), float(c75s5), float(c75s6)],
        [float(c80s1), float(c80s2), float(c80s3),
         float(c80s4), float(c80s5), float(c80s6)],
        [float(c85s1), float(c85s2), float(c85s3),
         float(c85s4), float(c85s5), float(c85s6)],
    ]) for code,
           c50s1, c50s2, c50s3, c50s4, c50s5, c50s6,
           c55s1, c55s2, c55s3, c55s4, c55s5, c55s6,
           c60s1, c60s2, c60s3, c60s4, c60s5, c60s6,
           c65s1, c65s2, c65s3, c65s4, c65s5, c65s6,
           c70s1, c70s2, c70s3, c70s4, c70s5, c70s6,
           c75s1, c75s2, c75s3, c75s4, c75s5, c75s6,
           c80s1, c80s2, c80s3, c80s4, c80s5, c80s6,
           c85s1, c85s2, c85s3, c85s4, c85s5, c85s6,
           in items}
    return discounts


def get_discount_enter():
    with open('data/discountEnter.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    discounts = {int(code): np.array([
        [float(c50s1), float(c50s2), float(c50s3),
         float(c50s4), float(c50s5), float(c50s6)],
        [float(c55s1), float(c55s2), float(c55s3),
         float(c55s4), float(c55s5), float(c55s6)],
        [float(c60s1), float(c60s2), float(c60s3),
         float(c60s4), float(c60s5), float(c60s6)],
        [float(c65s1), float(c65s2), float(c65s3),
         float(c65s4), float(c65s5), float(c65s6)],
        [float(c70s1), float(c70s2), float(c70s3),
         float(c70s4), float(c70s5), float(c70s6)],
        [float(c75s1), float(c75s2), float(c75s3),
         float(c75s4), float(c75s5), float(c75s6)],
        [float(c80s1), float(c80s2), float(c80s3),
         float(c80s4), float(c80s5), float(c80s6)],
        [float(c85s1), float(c85s2), float(c85s3),
         float(c85s4), float(c85s5), float(c85s6)],
    ]) for code,
           c50s1, c50s2, c50s3, c50s4, c50s5, c50s6,
           c55s1, c55s2, c55s3, c55s4, c55s5, c55s6,
           c60s1, c60s2, c60s3, c60s4, c60s5, c60s6,
           c65s1, c65s2, c65s3, c65s4, c65s5, c65s6,
           c70s1, c70s2, c70s3, c70s4, c70s5, c70s6,
           c75s1, c75s2, c75s3, c75s4, c75s5, c75s6,
           c80s1, c80s2, c80s3, c80s4, c80s5, c80s6,
           c85s1, c85s2, c85s3, c85s4, c85s5, c85s6,
           in items}
    return discounts


def get_counties():
    with open('data/counties.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    return {f'{cty}, {st}': f'{int(stcode):02}{int(ctycode):03}'
            for stcode, ctycode, cty, st in items}


if __name__ == '__main__':

    # TODO: aphyield and apprYield seem to be switched in the code!!

    ep = EntPrems()
    prem = ep.compute_premiums()
    print("Premiums for Default settings (verified)")
    print(prem)

    expected = array(
        [[02.27,  1.49,  0.9 ,  1.66,  1.17,  0.71,  1.86,  1.21,  0.73],
         [03.46,  2.34,  1.28,  2.22,  1.61,  0.87,  2.69,  1.79,  0.99],
         [04.81,  3.41,  1.79,  2.92,  2.02,  1.01,  3.63,  2.46,  1.37],
         [07.96,  5.85,  2.62,  4.69,  3.26,  1.36,  5.79,  4.01,  1.96],
         [11.36,  8.54,  3.79,  6.56,  4.69,  1.91,  7.89,  5.57,  2.69],
         [17.83, 13.9 ,  6.38, 10.39,  7.52,  3.12, 11.86,  8.53,  4.22],
         [28.75, 23.23, 12.72, 17.34, 12.94,  6.39, 18.53, 13.57,  7.90],
         [46.85, 39.29, 26.97, 28.59, 22.35, 14.13, 28.72, 21.48, 15.34]])

    assert np.all((prem - expected) == 0), "values don't all match"
    print()

    settings = {
        'aphyield': 180,
        'apprYield': 180,
        'tayield': 190,
        'acre': 3000,
        'aphPrice': 5.91,
        'pvol': 0.18,
        'hf': 0,        # possibly harvest factor
        'pf': 0,        # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'highRisk': 0,  # only visible option is None -> 0
        'rtype': 0,     # only visible option is None -> 0
        'tause': 1,     # 0 if K7 is 'No' else 1
        'ye': 0,        # 1 if K7 is 'YE' or 'TA/YE' else 0
        'county': 'Champaign, IL',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'atype': 'Grain'
    }
    prem = ep.compute_premiums(**settings)
    print("Premiums for 3000 acres corn (verified)")
    print(prem)
    expected = array(
      [[02.27,  1.37,  0.83,  1.66,  1.11,  0.67,  1.86,  1.12,  0.68],
       [03.46,  2.11,  1.16,  2.22,  1.49,  0.81,  2.69,  1.62,  0.90],
       [04.81,  3.1 ,  1.62,  2.92,  1.86,  0.94,  3.63,  2.21,  1.23],
       [07.96,  5.35,  2.4 ,  4.69,  2.92,  1.22,  5.79,  3.62,  1.76],
       [11.36,  7.87,  3.5 ,  6.55,  4.26,  1.74,  7.89,  5.03,  2.42],
       [17.83, 12.92,  5.95, 10.38,  6.86,  2.85, 11.86,  7.71,  3.81],
       [28.75, 21.8 , 11.99, 17.34, 11.85,  5.87, 18.53, 12.29,  7.15],
       [46.85, 37.22, 25.66, 28.59, 20.64, 13.09, 28.72, 19.5 , 13.92]])

    assert np.all((prem - expected) == 0), "values don't all match"
    print()

    settings = {
        'aphyield': 58.0,
        'apprYield': 58.0,
        'tayield': 60,
        'acre': 3000,
        'aphPrice': 13.76,
        'pvol': 0.13,
        'hf': 0,        # possibly harvest factor
        'pf': 0,        # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'highRisk': 0,  # only visible option is None -> 0
        'rtype': 0,     # only visible option is None -> 0
        'tause': 1,     # 0 if K7 is 'No' else 1
        'ye': 0,        # 1 if K7 is 'YE' or 'TA/YE' else 0
        'county': 'Champaign, IL',
        'crop': 'Soybeans',
        'practice': 'Nfac (non-irrigated)',
        'atype': 'No Type Specified'
    }
    prem = ep.compute_premiums(**settings)
    print("Premiums for 3000 acres full season soybeans in Champaign (verified)")
    print(prem)
    expected = array(
      [[00.41,  0.27,  0.16,  0.35,  0.23,  0.14,  0.38,  0.25,  0.15],
       [00.64,  0.43,  0.24,  0.46,  0.31,  0.17,  0.52,  0.36,  0.20],
       [00.89,  0.66,  0.37,  0.58,  0.42,  0.23,  0.69,  0.49,  0.27],
       [01.53,  1.18,  0.58,  0.84,  0.64,  0.31,  1.06,  0.8 ,  0.39],
       [02.45,  1.99,  0.97,  1.22,  0.97,  0.47,  1.44,  1.13,  0.55],
       [04.32,  3.73,  1.9 ,  1.91,  1.64,  0.83,  2.24,  1.83,  0.93],
       [07.12,  6.38,  3.9 ,  2.96,  2.61,  1.58,  3.49,  2.94,  1.78],
       [11.82, 10.92,  8.23,  4.59,  4.16,  3.1 ,  5.36,  4.64,  3.45]])

    assert np.all((prem - expected) == 0), "values don't all match"
    print()

    settings = {
        'aphyield': 39.0,
        'apprYield': 39.0,
        'tayield': 38.5,
        'acre': 300,
        'aphPrice': 7.25,
        'pvol': 0.24,
        'hf': 0,        # possibly harvest factor
        'pf': 0,        # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'highRisk': 0,  # only visible option is None -> 0
        'rtype': 0,     # only visible option is None -> 0
        'tause': 1,     # 0 if K7 is 'No' else 1
        'ye': 0,        # 1 if K7 is 'YE' or 'TA/YE' else 0
        'county': 'Champaign, IL',
        'crop': 'Wheat',
        'practice': 'Non-irrigated',
        'atype': 'Winter'
    }
    prem = ep.compute_premiums(**settings)
    print("Premiums for 300 acres wheat in Champaign (verified)")
    print(prem)
    expected = array(
      [[06.88,  4.54,  2.75,  5.98,  3.87,  2.34,  5.59,  3.5 ,  2.12],
       [09.05,  6.04,  3.36,  7.89,  5.15,  2.86,  7.38,  4.63,  2.57],
       [10.75,  7.29,  4.05,  9.35,  6.2 ,  3.44,  8.8 ,  5.54,  3.08],
       [14.59,  9.92,  4.84, 12.7 ,  8.45,  4.12, 11.93,  7.52,  3.67],
       [17.9 , 12.53,  5.99, 15.7 , 10.79,  5.14, 14.78,  9.68,  4.60],
       [23.85, 17.78,  8.77, 21.01, 15.45,  7.58, 19.81, 14.01,  6.84],
       [33.15, 26.01, 15.2 , 29.35, 22.83, 13.24, 27.71, 20.84, 12.02],
       [47.28, 38.74, 27.46, 42.14, 34.24, 24.05, 39.89, 31.51, 21.98]])

    assert np.all((prem - expected) == 0), "values don't all match"
    print()

    settings = {
        'aphyield': 154,
        'apprYield': 154,
        'tayield': 164,
        'acre': 100,
        'aphPrice': 5.91,
        'pvol': 0.18,
        'hf': 0,        # possibly harvest factor
        'pf': 0,        # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'highRisk': 0,  # only visible option is None -> 0
        'rtype': 0,     # only visible option is None -> 0
        'tause': 1,     # 0 if K7 is 'No' else 1
        'ye': 0,        # 1 if K7 is 'YE' or 'TA/YE' else 0
        'county': 'Madison, IL',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'atype': 'Grain'
    }
    prem = ep.compute_premiums(**settings)
    print("Premiums for Madison County corn (verified)")
    print(prem)
    expected = array(
      [[04.88,  3.16,  1.92,  3.43,  2.21,  1.34,  4.06,  2.61,  1.58],
       [06.98,  4.69,  2.6 ,  4.75,  3.07,  1.71,  5.67,  3.73,  2.07],
       [08.91,  6.16,  3.42,  5.92,  3.89,  2.16,  7.14,  4.79,  2.66],
       [13.27,  9.32,  4.55,  8.62,  5.67,  2.77, 10.25,  7.01,  3.42],
       [18.29, 13.4 ,  6.47, 11.99,  8.08,  3.87, 13.66,  9.55,  4.59],
       [26.58, 20.12, 10.02, 17.74, 12.46,  6.11, 19.62, 13.96,  6.87],
       [40.08, 31.25, 18.47, 27.45, 19.85, 11.45, 29.37, 21.3 , 12.34],
       [60.49, 48.81, 36.25, 42.24, 31.56, 23.17, 43.35, 32.1 , 22.92]])

    assert np.all((prem - expected) == 0), "values don't all match"
    print()

    settings = {
        'aphyield': 47.0,
        'apprYield': 47.0,
        'tayield': 50,
        'acre': 3000,
        'aphPrice': 13.76,
        'pvol': 0.13,
        'hf': 0,        # possibly harvest factor
        'pf': 0,        # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'highRisk': 0,  # only visible option is None -> 0
        'rtype': 0,     # only visible option is None -> 0
        'tause': 1,     # 0 if K7 is 'No' else 1
        'ye': 0,        # 1 if K7 is 'YE' or 'TA/YE' else 0
        'county': 'Madison, IL',
        'crop': 'Soybeans',
        'practice': 'Nfac (non-irrigated)',
        'atype': 'No Type Specified'
    }
    prem = ep.compute_premiums(**settings)
    print("Premiums for 3000 acres full season soybeans in Madison (verified)")
    print(prem)
    expected = array(
      [[02.21,  1.5 ,  0.91,  1.68,  1.15,  0.69,  1.93,  1.3 ,  0.79],
       [03.26,  2.27,  1.26,  2.32,  1.58,  0.88,  2.72,  1.89,  1.05],
       [04.41,  3.21,  1.79,  3.09,  2.15,  1.2 ,  3.52,  2.54,  1.41],
       [06.77,  5.15,  2.51,  4.7 ,  3.42,  1.67,  5.26,  3.91,  1.91],
       [08.89,  7.06,  3.44,  6.13,  4.69,  2.29,  6.89,  5.29,  2.58],
       [13.41, 11.01,  5.59,  9.33,  7.31,  3.7 , 10.38,  8.26,  4.18],
       [20.36, 17.19, 10.42, 14.31, 11.59,  6.97, 15.72, 12.86,  7.76],
       [30.55, 26.54, 19.98, 21.67, 18.1 , 13.58, 23.27, 19.55, 14.52]])

    assert np.all((prem - expected) == 0), "values don't all match"
    print()

    settings = {
        'aphyield': 58.0,
        'apprYield': 58.0,
        'tayield': 61.0,
        'acre': 300,
        'aphPrice': 7.25,
        'pvol': 0.24,
        'hf': 0,        # possibly harvest factor
        'pf': 0,        # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'highRisk': 0,  # only visible option is None -> 0
        'rtype': 0,     # only visible option is None -> 0
        'tause': 1,     # 0 if K7 is 'No' else 1
        'ye': 0,        # 1 if K7 is 'YE' or 'TA/YE' else 0
        'county': 'Madison, IL',
        'crop': 'Wheat',
        'practice': 'Non-irrigated',
        'atype': 'Winter'
    }
    prem = ep.compute_premiums(**settings)
    print("Premiums for 300 acres wheat in Madison (verified)")
    print(prem)
    expected = array(
      [[08.11,  5.4 ,  3.27,  6.95,  4.55,  2.76,  6.32,  3.97,  2.41],
       [10.7 ,  7.25,  4.03,  9.14,  6.1 ,  3.39,  8.25,  5.19,  2.88],
       [12.75,  8.82,  4.9 , 10.9 ,  7.38,  4.1 ,  9.78,  6.16,  3.42],
       [17.63, 12.54,  6.05, 15.14, 10.45,  5.03, 13.61,  8.78,  4.22],
       [22.12, 16.58,  7.85, 19.01, 14.  ,  6.59, 17.18, 11.97,  5.60],
       [29.46, 23.27, 11.38, 25.41, 19.81,  9.61, 22.99, 17.08,  8.21],
       [40.93, 33.73, 19.56, 35.39, 28.89, 16.58, 32.14, 25.15, 14.28],
       [56.73, 48.8 , 35.2 , 49.01, 41.83, 29.92, 44.57, 36.56, 25.51]])

    assert np.all((prem - expected) == 0), "values don't all match"
    print()

    settings = {
        'aphyield': 47.0,
        'apprYield': 47.0,
        'tayield': 49.0,
        'acre': 300,
        'aphPrice': 13.76,
        'pvol': 0.13,
        'hf': 0,        # possibly harvest factor
        'pf': 0,        # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'highRisk': 0,  # only visible option is None -> 0
        'rtype': 0,     # only visible option is None -> 0
        'tause': 1,     # 0 if K7 is 'No' else 1
        'ye': 0,        # 1 if K7 is 'YE' or 'TA/YE' else 0
        'county': 'Madison, IL',
        'crop': 'Soybeans',
        'practice': 'Fac (non-irrigated)',
        'atype': 'No Type Specified'
    }
    prem = ep.compute_premiums(**settings)
    print("Premiums for 300 acres Fac soybeans in Madison (verified)")
    print(prem)
    expected = array(
      [[04.06,  2.81,  1.7 ,  3.13,  2.1 ,  1.28,  3.48,  2.42,  1.47],
       [05.75,  4.07,  2.26,  4.38,  2.99,  1.66,  4.83,  3.41,  1.90],
       [07.63,  5.59,  3.11,  5.79,  4.06,  2.26,  6.29,  4.55,  2.53],
       [11.  ,  8.31,  4.05,  8.34,  6.03,  2.94,  9.03,  6.64,  3.24],
       [13.7 , 10.58,  5.16, 10.37,  7.62,  3.72, 11.23,  8.43,  4.11],
       [18.83, 14.86,  7.57, 14.27, 10.75,  5.47, 15.4 , 11.82,  6.01],
       [27.14, 21.95, 13.34, 20.67, 15.97,  9.66, 22.21, 17.43, 10.56],
       [40.52, 33.73, 25.34, 31.25, 24.87, 18.62, 32.94, 26.56, 19.73]])

    assert np.all((prem - expected) == 0), "values don't all match"
    print()
