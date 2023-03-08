from numpy import zeros, ones, array
import numpy as np
from math import log, exp


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
    with open('data/rateDiff.txt', 'r') as f:
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


def make_code(county, crop, atype, practice):
    return int(f'{counties[county]}{crops[crop]}{types[atype]}{practices[practice]}')


def get_counties():
    with open('data/counties.txt', 'r') as f:
        contents = f.read()
    lines = contents.strip().split('\n')
    items = (line.split() for line in lines)
    return {f'{cty}, {st}': f'{int(stcode):02}{int(ctycode):03}'
            for stcode, ctycode, cty, st in items}


# ---------------
# USER INPUT DATA
# ---------------
# aphyield
# --------
# TODO: aphyield and apprYield seem to be switched in the code!!
# Sheet1.Cells(91, 5) -> round(O7,)
# O7 is 'Rate Yield'
aphyield = 180

# appryield
# ---------
# Sheet1.Cells(83, 5) -> round(G7,)
# G7 is 'APH Yield'
apprYield = 180

# tayield
# -------
# Sheet1.Cells(89, 8) -> M7 (TA Yield)
tayield = 190

if tayield < aphyield:
    tayield = aphyield

# acre
# ----
# Cells(85, 5) -> F8
acre = 100

# aphPrice
# --------
# Cells(84, 5) -> Sheets("parameters").Cells('AG5')
# Based on crop in E4 and state in E2, lookup projected price.
aphPrice = 5.91

# pvol
# ----
# Cells(86, 5) -> Sheets("parameters").Cells('AG6')
# Based on crop in E4 and state in E2, lookup volatility
pvol = 0.18

# hf (possibly harvest factor, e.g prevented harvest?)
# --
# Sheet1.Cells(87, 5) -> K78 (hardcoded 0)
# not accessible through interface; not updated by vba code
hf = 0

# pf (prevent planting factor)
# --
# Sheet1.Cells(88, 5) lookup S8 (Prevented planting)
# standard -> 0, Plus 5% -> 1, Plus 10% -> 2
pf = 0

# highRisk
# --------
# Sheet1.Cells(89, 5)
# lookup S7 (Risk class) only visible option is None -> 0
highRisk = 0

# rtype
# -----
# Sheet1.Cells(90, 5) (factor)
# lookup S7 (Risk class) only visible option is None -> 0
rtype = 0

# tause
# -----
# Sheet1.Cells(90, 8) -> 0 if K7 is 'No' else 1
# K7 is 'TA/YE adjustment'
tause = 1

# YE
# --
# Sheet1.Cells(90, 11) -> 1 if K7 is 'YE' or 'TA/YE' else 0
YE = 0

# prem: numpy array to store final premiums
prem = zeros((8, 9))

crops = {'Corn': '41', 'Soybeans': '81', 'Wheat': '11', 'Sorghum': '51'}
practices = {'Non-irrigated': '003', 'Irrigated': '002'}
types = {'Grain': '016'}
counties = get_counties()

county = 'Champaign, IL'
crop = 'Corn'
practice = 'Non-irrigated'
atype = 'Grain'
code = make_code(county, crop, atype, practice)
fcode = code + 0.1

enter_id = get_enter_id()
beta_id = get_beta_id()
options = get_options()
discount_basic = get_discount_basic()
discount_enter = get_discount_enter()
rates = get_rates()
rate_diff = get_rate_diff()
prate_diff = get_prate_diff()
unit_factor = get_unit_factor()
punit_factor = get_punit_factor()
enterprise_factor = get_enterprise_factor()
penterprise_factor = get_penterprise_factor()
enter_factor_rev = get_enter_factor_rev()
penter_factor_rev = get_penter_factor_rev()
rev_lookup = get_rev_lookup()
draws = get_draws()

# cover: coverage levels as fractions
# -----------------------------------
cover = array([x/100 for x in range(50, 86, 5)])

# subsidy: hard-coded subsidy
# ---------------------------
subsidy = array([[0.67, 0.64, 0.64, 0.59, 0.59, 0.55, 0.48, 0.38],
                 [0.8,  0.8,  0.8,  0.8,  0.8,  0.77, 0.68, 0.53]]).T

# Rates table values
# ------------------
(refyield, refrate, exponent, fixedrate,
 prefyield, prefrate, pexponent, pfixedrate) = rates[code]

# options table values
# --------------------
hfrate, pfrate, ptrate = options[code]

# betaId: integer key value
# -------------------------
betaId = beta_id[code]

# enterId: discountBasic and discountEnter are keyed on enterId
# -------------------------------------------------------------
enterId = enter_id[code]

# discountBasic values
# --------------------
discountBasic = discount_basic[enterId]

# discountEnter values
# --------------------
discountEnter = discount_enter[enterId]

# locat2
# ------
# Used to update spreadsheet with suffixed code, e.g. 1701941016003.1
# The Risk Class drop-down has 4 invisible options under None, I think.
# riskTest = Sheet1.Cells(7, 19)
# locat2 = locat + 0.1 + (0.2 if riskTest == 'AAA' else
#                         0.3 if riskTest == 'BBB' else
#                         0.4 if riskTest == 'CCC' else
#                         0.5 if riskTest == 'DDD' else 0)
# Sheet1.Cells('G79') = locat2

# rateDiff
# --------
# These tables have a mix of float codes and int codes...
rateDiff = zeros((8, 2))
try:
    rateDiff[:, 0] = rate_diff[code]
except KeyError:
    rateDiff[:, 0] = rate_diff[fcode]
try:
    rateDiff[:, 1] = prate_diff[code]
except KeyError:
    rateDiff[:, 1] = prate_diff[fcode]

# unitFactor
# ----------
unitFactor = zeros((8, 2))
unitFactor[:, 0] = unit_factor[fcode]
unitFactor[:, 1] = punit_factor[fcode]

# enterpriseFactor
# ----------------
enterpriseFactor = zeros((8, 2))
enterpriseFactor[:, 0] = enterprise_factor[fcode]
enterpriseFactor[:, 1] = penterprise_factor[fcode]

# enterFactorRev
# --------------
enterFactorRev = zeros((8, 2))
enterFactorRev[:, 0] = enter_factor_rev[fcode]
enterFactorRev[:, 1] = penter_factor_rev[fcode]

# yieldDraw and priceDraw
# ---------
yieldDraw, priceDraw = draws[betaId]
# Historic capping
# Note: the vba code uses data from historicCapping only if krecord >= 0.5
# but krecord is hard-coded to 0.
krecord = 0
cHisRec = 0
crefYield = 1
crefRate = 1
cexpValue = 1
cfixedRate = 1
cprefYield = 1
cprefRate = 1
cpexpValue = 1
cpfixedRate = 1
cbeta = ones(15)

jSize = (0 if acre < 50 else 1 if acre < 100 else 2 if acre < 200 else
         3 if acre < 400 else 4 if acre < 800 else 5)

for i in range(8):
    print('for i', i, rateDiff[i, 0])
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
            eFactor = get_factor(enterpriseFactor, effcov, cover, rateDiff, 0, 3)
            peFactor = get_factor(enterpriseFactor, effcov, cover, rateDiff, 1, 3)
            eFactorRev = get_factor(enterFactorRev, effcov, cover, rateDiff, 0, 3)
            peFactorRev = get_factor(enterFactorRev, effcov, cover, rateDiff, 1, 3)
            disBasic = get_factor(discountBasic, effcov, cover, rateDiff, jSize, 4)
            disEnter = get_factor(discountEnter, effcov, cover, rateDiff, jSize, 4)

        # new code for YE adj
        yeAdj = 0  # vba code declares, but doesn't initialize
        if effcov > 0.85:
            if YE > 0.5:
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

        # revLookup
        # Computes three codes based on revLook: e.g. [162, 111, 111]
        revLookup = [
            int(revLook * 10000 + 0.5),
            int(revLook * discountBasic[3, jSize] * 10000 + 0.5),
            int(revLook * discountEnter[3, jSize] * 10000 + 0.5)]

        # values corresponding to revLookup
        mQty, stdQty = zip(*(rev_lookup[k] for k in revLookup))

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
            simRpLoss = round(simRevLoss / 500 / (revYield * revCov * aphPrice), 8)
            simRpExcLoss = round(simRevExcLoss / 500 /
                                 (revYield * revCov * aphPrice), 8)

            # step 5.06
            revRate = round(max(0.01 * basePremRate, simRpLoss - simYpLoss), 8)
            revExcRate = round(max(-0.5 * basePremRate, simRpExcLoss - simYpLoss), 8)

            print('5.06', i, revRate, revExcRate)

            # step 6 calculation of historical revenue capping
            # since krecord = 0, cHisRec = 0 so the if block was removed
            revRateUse = revRate
            revRateEntUse = revRate
            revExcRateUse = revExcRate
            revExcRateEntUse = revExcRate

            # step 8.01i
            premRateO = basePremRate * multFactor
            premRateB = basePremRate * multFactor * disBasic
            premRateE = basePremRateE * multFactor * disEnter
            premRateErev = basePremRateErev * multFactor * disEnter

            if ii == 0:  # optional policies
                # rp optional
                prem[i, 0] = round(liab * round(premRateO + revRateUse, 8), 0)
                # rpexc optional
                prem[i, 3] = round(liab * round(premRateO + revExcRateUse, 8), 0)
                # yp optional
                prem[i, 6] = round(liab * round(premRateO, 8), 0)
            if ii == 1:  # basic policy
                # rp basic
                prem[i, 1] = round(liab * round(premRateB + revRateUse, 8), 0)
                # rpexc basic
                prem[i, 4] = round(liab * round(premRateB + revExcRateUse, 8), 0)
                # yp basic
                prem[i, 7] = round(liab * round(premRateB, 8), 0)
            if ii == 2:   # enterprise policy
                # rp enterprise
                prem[i, 2] = round(liab * round(premRateErev + revRateEntUse, 8), 0)
                # rpexc enterprise
                prem[i, 5] = round(liab * round(premRateErev + revExcRateEntUse, 8), 0)
                # yp enterprise
                prem[i, 8] = round(liab * round(premRateE, 8), 0)

        for j in range(9):
            prem[i, j] -= round(prem[i, j] * subsidy[i, 1 if j % 3 == 2 else 0], 0)

        for j in range(9):
            prem[i, j] = round(prem[i, j] / acre, 2)

np.set_printoptions(precision=2)
np.set_printoptions(suppress=True)
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
print(prem)
with open('prems.txt', 'w') as f:
    f.write(str(prem))
