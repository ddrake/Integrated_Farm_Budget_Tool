from numpy import zeros, array
import numpy as np
from math import log, exp
import os
import pickle

from util import Crop, Unit, Prot, Lvl

DATADIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
np.set_printoptions(precision=6)
np.set_printoptions(suppress=True)


class Premiums:
    """
    Class for computing Enterprise and ARC premiums for RP, RP-HPE, YO
    """
    def __init__(self):
        self.load_lookups()
        self.subsidy = (0.8,  0.8,  0.8,  0.8,  0.8,  0.77, 0.68, 0.53)
        self.subsidy_sco = 0.65
        self.subsidy_grip = array([0.59, 0.55, 0.55, 0.49, 0.44])
        self.subsidy_grp = array([0.59, 0.59, 0.55, 0.55, 0.51])
        self.subsidy_eco = 0.44

        self.cover = array([x/100 for x in range(50, 86, 5)])  # coverage levels
        self.arc_cover = array([x/100 for x in range(70, 91, 5)])  # arc coverage levels

        # User inputs
        # -----------
        self.acres = None       # acres to insure

        # extras
        self.hailfire = None         # Hail / Fire protection
        self.prevplant = None         # Prevent plant protection
        self.tause = None      # 1 to use trend-adjusted yields else 0
        self.yieldexcl = None         # 1 to use yield-exclusion else 0

        # yields
        self.aphyield = None   # Actual production history yield
        self.apprYield = None  # Approved yield
        self.tayield = None    # Trend-adjusted yield
        self.expYield = None   # For area base premiums
        # for area options
        self.arevYield = self.tayield if self.tause else self.aphyield

        # price / volatility
        self.aphPrice = None   # Actual or estimated production history price
        self.pvol = None       # Actual or estimate volatility factor

        # Risk related
        self.riskname = None   # {'None', 'AAA', 'BBB', 'CCC', 'DDD'} dep. on county
        self.risk = None       # {0: None, 1: 'AAA', 2: 'BBB', 3: 'CCC', 4: 'DDD'}
        self.highRisk = None   # float looked up by code and riskname in high_risk dict
        self.rtype = None      # int looked up by code and riskname in high_risk dict

        # lookup key codes
        self.code = None       # code for state/county/crop/etc..
        self.fcode = None      # code with decimal suffix for risk
        self.ccode = None       # county code for state/county/crop/etc..
        self.acode = None      # county code with decimal suffix for volatility

        # scalar variables
        # -------------------------
        self.adjMeanQty = None
        self.adjStdQty = None
        self.disEnter = None
        self.effcov = None
        self.jSize = None            # based on acres
        self.liab = None
        self.aliab = None
        self.maxliab = None
        self.lnMean = None
        self.multFactor = None
        self.premRate = None         # Premium rates array (Erev, E)
        self.revCov = None
        self.revYield = None
        self.selected_draws = None
        self.simLoss = None          # Simulated Loss array (Yp, Rp, RpExc)
        self.revExcRateUse = None
        self.revRateUse = None
        self.prot_factor = None      # Protection factor for ARC

        # 3-tuples
        self.mQty = None
        self.stdQty = None

        # (current/prev) pairs
        self.baseRate = None          # Continuous rating base rate
        self.eFactor = None
        self.eFactorRev = None
        self.rateDiffFac = None
        self.revLook = None

        # Array sized (2, 2)  ('E', 'Erev') by (cur, prior)
        self.basePremRate = None

        # Arrays sized (8, 2) (8 coverage levels) by 2 (cur, prior)
        self.rateDiff = None
        self.unitFactor = None
        self.enterpriseFactor = None
        self.enterFactorRev = None

        # Arrays sized (8, 6) (8 coverage levels) by (6 acre size values)
        self.discountEnter = None

        # Premium arrays
        self.prem = None
        self.arc_prem = None
        self.sco_prem = None
        self.eco_prem = None

    # -----------------------------
    # MAIN METHOD: COMPUTE PREMIUMS
    # -----------------------------
    def compute_prems_ent(self, aphyield=180, apprYield=180, tayield=190, acres=100,
                          hailfire=0, prevplant=0, risk='None', tause=1,
                          yieldexcl=0, county='Champaign, IL', crop='Corn',
                          practice='Non-irrigated', croptype='Grain'):
        """
        With farm-specific inputs, compute premiums for optional, basic and enterprise,
        units with RP, RP-HPE or YO protection for all coverage levels.
        """
        self.store_user_settings_ent(aphyield, apprYield, tayield, acres, hailfire,
                                     prevplant, risk, tause, yieldexcl, county,
                                     crop, practice, croptype)
        self.initialize_arrays()
        self.set_multfactor()
        for i in range(8):  # index i corresponds to coverage level
            if self.rateDiff[i, 0] > 0:
                self.set_effcov(i)
                self.set_factors(i)
                self.make_ye_adj(i)
                self.make_rev_liab(i)
                self.set_base_rates(i)
                self.set_base_prem_rates(i)
                self.limit_base_prem_rates(i)
                self.limit_revlook(i)
                self.limit_baserate(i)
                self.set_qtys(i)
                # step 5.01
                # section 5 revenue calculation
                self.simulate_losses(i)
                self.set_rates(i)
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
        if self.hailfire > 0:
            self.multFactor *= hfrate
        if self.prevplant == 1:
            self.multFactor *= pfrate
        if self.prevplant == 2:
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

    def make_ye_adj(self, i):
        """
        Adjust factors for YE (vectorized)
        """
        jjHigh = 5 if self.rateDiff[6, 0] == 0 else 7
        yeAdj = 0
        if self.effcov > 0.85:
            if self.yieldexcl > 0.5:
                yeAdj = (self.effcov - 0.85) / 0.15
            yeAdj = 1 + round(min(1, yeAdj) ** 3, 7) * 0.05
            self.rateDiffFac[0] *= yeAdj
            self.eFactor = np.minimum(self.eFactor, self.enterpriseFactor[jjHigh, :])

    def make_rev_liab(self, i):
        """
        Set the revised yield, the revised cover and the liability
        """
        # step 1
        self.revYield = self.tayield if self.tause else self.apprYield
        self.revCov = self.effcov if self.tause else self.cover[i]
        self.liab = round(round(self.revYield * self.cover[i] + 0.001, 1) *
                          self.aphPrice * self.acres, 0)

    def set_base_rates(self, i):
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

    def set_base_prem_rates(self, i):
        """
        Set vector adjusted base premium rates
        """
        # Worksheet step 8.  Calculate Base Premium Rates Adjusted Base Rate x
        # coverage level rate differential.
        # step 2.04
        prod = self.baseRate * self.rateDiffFac
        self.basePremRate = array((prod * self.eFactor,
                                   prod * self.eFactorRev)).round(8)

    def limit_base_prem_rates(self, i):
        """
        Limit base premium rates based on prior (unpacking vectors)
        """
        # Preliminary base rate is min of cur and 1.2 * prev.
        # step 2.05
        var = self.basePremRate
        for j in range(2):
            if var[j, 0] > var[j, 1] * 1.2:
                var[j, 0] = round(var[j, 1] * 1.2, 8)
            if var[j, 0] > 0.99:
                var[j, 0] = 0

    def limit_revlook(self, i):
        """
        Limit revenue lookup based on previous (unpacking vectors)
        """
        # step 2.06
        if self.revLook[0] > self.revLook[1] * 1.2:
            self.revLook[0] = round(self.revLook[1] * 1.2, 8)
        self.revLook[0] = round(min(self.revLook[0], 0.9999), 4)

    def limit_baserate(self, i):
        """
        Limit base rate based on previous (unpacking vectors)
        """
        # step 2.07
        if self.baseRate[0] > self.baseRate[1] * 1.2:
            self.baseRate[0] = round(self.baseRate[1] * 1.2, 8)

    def set_qtys(self, i):
        """
        Compute mQty and stdQty
        """
        prod = self.revLook[0] * 10000
        revLookup = int(prod * self.discountEnter[3, self.jSize] + 0.5)
        self.mQty, self.stdQty = self.rev_lookup[revLookup]

    def simulate_losses(self, i):
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

    def set_rates(self, i):
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
        prem is (8, 3): 8 coverage levels x (RP, RP-HPE, YP)
        """
        self.prem[i, j] = round(self.liab * round(rate + rateuse, 8), 0)

    def set_prems(self, i):
        """
        Set the pre-subsidy premiums
        """
        self.set_prem(self.premRate[1], i, 0, self.revRateUse)       # RP
        self.set_prem(self.premRate[1], i, 1, self.revExcRateUse)    # RP-HPE
        self.set_prem(self.premRate[0], i, 2)                        # YP

    def apply_subsidy(self, i):
        """
        Apply the subsidy
        """
        for j in range(3):
            self.prem[i, j] -= round(self.prem[i, j] * self.subsidy[i], 0)
            self.prem[i, j] = round(self.prem[i, j] / self.acres, 2)

    def store_user_settings_ent(self, aphyield, apprYield, tayield, acres, hailfire,
                                prevplant, risk, tause, yieldexcl, county, crop,
                                practice, croptype):
        """
        Store settings provide by user when calling calc_premiums, and calculate
        some values derived from them.
        """
        self.aphyield = aphyield
        self.apprYield = apprYield
        self.tayield = tayield
        self.acres = acres
        self.hailfire = hailfire
        self.prevplant = prevplant
        if isinstance(risk, str):
            self.riskname = risk
            self.risk = self.risk_classes[risk]
        else:
            self.risk = risk
            self.riskname = self.rev_risk_classes[risk]
        self.highRisk = None
        self.rtype = None
        self.tause = tause
        self.yieldexcl = yieldexcl

        if self.tayield < self.aphyield:
            self.tayield = self.aphyield

        # codes used to key into dicts
        self.code = self.make_code(county, crop, croptype, practice)
        self.fcode = self.code + 0.1 * (1 + self.risk)
        self.pcode = self.make_pcode()

        # read price and volatility from parameters
        self.aphPrice, self.pvol = self.parameters[self.pcode]

        # Set index based on acreage
        self.jSize = (0 if self.acres < 50 else 1 if self.acres < 100 else
                      2 if self.acres < 200 else 3 if self.acres < 400 else
                      4 if self.acres < 800 else 5)

    def initialize_arrays(self):
        """
        Initialize arrays for premium calculation
        """
        # Initialize current/prev arrays
        self.rateDiffFac = zeros(2)
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
        self.enterpriseFactor = array((self.enterprise_factor[self.fcode],
                                       self.penterprise_factor[self.fcode])).T
        self.enterFactorRev = array((self.enter_factor_rev[self.fcode],
                                     self.penter_factor_rev[self.fcode])).T
        self.selected_draws = self.draws[betaId]

    # -----------------------
    # ARC PREMIUMS
    # -----------------------
    def compute_prems_arc(self, county='Champaign, IL', crop='Corn',
                          practice='Non-irrigated', croptype='Grain',
                          prot_factor=1):
        """
        Get 120 pct values for each area type and level from 70:90
        These are scaled to get the 85 pct and 80 pct columns
        """
        self.arc_prem = zeros((3, 5))
        self.store_user_settings_arc(county, crop, practice, croptype, prot_factor)
        subsidies = (self.subsidy_grip, self.subsidy_grip, self.subsidy_grp)
        dicts = (self.arc_rp, self.arc_rphpe, self.arc_yp)
        for i, subsidy in enumerate(subsidies):
            self.compute_prem_arc(subsidy, dicts[i], i)
        if self.arc_prem.shape != (3, 5):
            raise ValueError(f'arc_prem has shape {self.arc_prem.shape}')
        return self.arc_prem

    def compute_prem_arc(self, subsidy, ardict, idx):
        """
        Compute premiums for the given unit info
        """
        code = self.acode if idx != 2 else self.ccode
        if code not in ardict:
            return
        rate = zeros(5)
        self.expYield, rate[:] = ardict[code]
        self.maxliab = round(self.expYield * self.aphPrice * 1.2, 2)
        self.arc_prem[idx, :] = (self.maxliab * 100 * rate).round(0)
        self.arc_prem[idx, :] -= (self.arc_prem[idx, :] * subsidy).round(0)
        self.arc_prem[idx, :] = (self.arc_prem[idx, :] / 100 *
                                 self.prot_factor / 1.2).round(2)

    def store_user_settings_arc(self, county, crop, practice, croptype, prot_factor):
        """
        Store settings provide by user when calling calc_premiums
        """
        self.code = self.make_code(county, crop, croptype, practice)
        self.ccode = self.make_ccode(county, crop, croptype, practice)
        self.pcode = self.make_pcode()
        self.prot_factor = prot_factor
        # read price and volatility from parameters
        self.aphPrice, self.pvol = self.parameters[self.pcode]
        # codes used to key into dicts
        self.acode = self.ccode + self.pvol

    # -----------------------
    # SCO PREMIUMS
    # -----------------------
    def compute_prems_sco(self, aphyield=180, tayield=190, tause=1,
                          county='Champaign, IL', crop='Corn',
                          practice='Non-irrigated', croptype='Grain'):
        """ Compute all SCO premiums """

        self.store_user_settings_sco(aphyield, tayield, tause, county,
                                     crop, practice, croptype)

        self.sco_prem = zeros((3, 8))
        for i, d in enumerate((self.sco_rp, self.sco_rphpe, self.sco_yp)):
            self.compute_prem_sco(d, i)
        return self.sco_prem

    def compute_prem_sco(self, rate_dict, unit):
        """
        Compute the sco premium for the given dict and unit index
        """
        if self.ccode not in rate_dict:
            return
        rate = rate_dict[self.ccode]
        if unit < 2:
            idx = int((self.pvol - 0.05)*100)
            rate = rate[idx, :]
        self.sco_prem[unit, :] = (self.aliab * (0.86 - self.cover) * rate).round(2)
        self.sco_prem[unit, :] -= (self.subsidy_sco * self.sco_prem[unit, :]).round(2)

    def store_user_settings_sco(self, aphyield, tayield, tause, county,
                                crop, practice, croptype):
        """
        Store settings provide by user when calling calc_premiums
        """
        self.aphyield = aphyield
        self.tayield = tayield
        self.tause = tause
        self.code = self.make_code(county, crop, croptype, practice)
        self.pcode = self.make_pcode()
        # read price and volatility from parameters
        self.aphPrice, self.pvol = self.parameters[self.pcode]
        self.arevYield = self.tayield if self.tause else self.aphyield
        self.aliab = self.arevYield * self.aphPrice

    # -----------------------
    # ECO PREMIUMS
    # -----------------------
    def compute_prems_eco(self, aphyield=180, tayield=190, tause=1,
                          county='Champaign, IL', crop='Corn',
                          practice='Non-irrigated', croptype='Grain'):
        """ Compute all ECO premiums """
        self.store_user_settings_eco(aphyield, tayield, tause, county,
                                     crop, practice, croptype)
        mult = array([0.04, 0.09])  # 90% - 86%, 95% - 86%
        self.eco_prem = zeros((3, 2))
        rate = zeros((3, 2))
        idx = int((self.pvol - 0.05)*100)
        if self.ccode not in self.eco:
            return
        rate = self.eco[self.ccode][idx][::-1, :]  # reorder rows as (RP, RP-HPE, YP)
        # Note: excel/vba code multiplies aliab then divides by .85
        self.eco_prem = (self.aliab * mult * rate * (1 - self.subsidy_eco)).round(2)
        return self.eco_prem

    def store_user_settings_eco(self, aphyield, tayield, tause, county, crop,
                                practice, croptype):
        """
        Store settings provide by user when calling calc_premiums
        """
        self.aphyield = aphyield
        self.tayield = tayield
        self.tause = tause
        self.code = self.make_code(county, crop, croptype, practice)
        self.ccode = self.make_ccode(county, crop, croptype, practice)
        self.pcode = self.make_pcode()
        # read price and volatility from parameters
        self.aphPrice, self.pvol = self.parameters[self.pcode]
        self.arevYield = self.tayield if self.tause else self.aphyield
        self.aliab = self.arevYield * self.aphPrice

    # ------------------------
    # Setup and Initialization
    # ------------------------
    def load_lookups(self):
        """
        Define dicts for lookups
        """
        self.crops = {'Corn': 41, 'Soybeans': 81, 'Wheat': 11}
        self.practices = {'Nfac (non-irrigated)': 53,
                          'Nfac (Irrigated)': 94,
                          'Fac (non-irrigated)': 43,
                          'Fac (Irrigated)': 95,
                          'Non-irrigated': 3,
                          'Irrigated': 2}
        self.types = {'Grain': 16, 'No Type Specified': 997, 'Winter': 11}

        # County products have some different practices and types
        self.cpractices = {'Nfac (non-irrigated)': 53,
                           'Nfac (Irrigated)': 53,
                           'Fac (non-irrigated)': 53,
                           'Fac (Irrigated)': 53,
                           'Non-irrigated': 3,
                           'Irrigated': 3}

        self.risk_classes = {'None': 0, 'AAA': 1, 'BBB': 2, 'CCC': 3, 'DDD': 4}
        self.rev_risk_classes = {0: 'None', 1: 'AAA', 2: 'BBB', 3: 'CCC', 4: 'DDD'}
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
        self.enterprise_factor = get_enterprise_factor()
        self.penterprise_factor = get_penterprise_factor()
        self.enter_factor_rev = get_enter_factor_rev()
        self.penter_factor_rev = get_penter_factor_rev()
        self.rev_lookup = get_rev_lookup()
        self.draws = get_draws()
        self.high_risk = get_high_risk()
        self.parameters = get_parameters()
        # dicts with float key and value tuple(1, tuple(5))
        self.arc_rp = get_arc_rp()
        self.arc_rphpe = get_arc_rphpe()
        self.arc_yp = get_arc_yp()
        # dict with key code, value array(36, 8) (ivol, cover)
        self.sco_rp = get_sco_rp()
        self.sco_rphpe = get_sco_rphpe()
        # dict with key code, value array(8) (cover)
        self.sco_yp = get_sco_yp()
        # dict with key code, value array(36, 3, 2) (ivol, unit, cov)
        self.eco = get_eco()

    def make_code(self, county, crop, croptype, practice):
        """
        Construct an integer code used to key in some tabular data
        """
        cty = self.counties[county] if isinstance(county, str) else county
        crp = self.crops[crop] if isinstance(crop, str) else crop
        crptype = self.types[croptype] if isinstance(croptype, str) else croptype
        prac = self.practices[practice] if isinstance(practice, str) else practice
        return int(f'{int(cty):05d}{crp:02d}{crptype:03d}{prac:03d}')

    def make_ccode(self, county, crop, croptype, practice):
        """
        Construct a COUNTY integer code used to key in some tabular data
        """
        cty = self.counties[county] if isinstance(county, str) else county
        crp = self.crops[crop] if isinstance(crop, str) else crop
        crptype = self.types[croptype] if isinstance(croptype, str) else croptype
        prac = self.cpractices[practice] if isinstance(practice, str) else practice
        return int(f'{int(cty):05d}{crp:02d}{crptype:03d}{prac:03d}')

    def make_pcode(self):
        """
        Construct a string code (crop + state) to key in parameter data (price, vol)
        """
        code = str(self.code)
        return f'{int(code[-8:-6]):02d}{int(code[:-11]):02d}'

    # ------------------
    # Convenience Method
    # ------------------

    def get_all_premiums(self, cropdicts=None):
        """
        Given a list of dicts, one for each crop, including specific choices of unit,
        protection, level, sco_level, eco_level, Return a dict of dicts, each containing
        individual premiums for the base product and options.
        """
        premiums = {}
        for d in cropdicts:
            crop = d['crop']
            name = ('Corn' if crop == Crop.CORN else 'Wheat' if crop == Crop.WHEAT
                    else 'Soybeans')
            cropcode = self.crops[name]
            d['crop'] = cropcode
            values = {'base': 0, 'sco': 0, 'eco': 0}
            if d['unit'] == Unit.ENT:
                d1 = {k: d[k] for k in
                      ('aphyield', 'apprYield', 'tayield', 'acres', 'hailfire',
                       'prevplant', 'risk', 'tause', 'yieldexcl', 'county',
                       'crop', 'practice', 'croptype')}
                prems = self.compute_prems_ent(**d1)
                values['base'] = prems[entlevel_idx(d['level']), d['prot']]
            else:
                d1 = {k: d[k] for k in
                      ('county', 'crop', 'practice', 'croptype', 'prot_factor')}
                prems = self.compute_prems_arc(**d1)
                values['base'] = prems[d['prot'], arclevel_idx(d['level'])]
            if d['sco_level'] > Lvl.NONE:
                d1 = {k: d[k] for k in
                      ('aphyield', 'tayield', 'tause', 'county', 'crop',
                       'practice', 'croptype')}
                prems = self.compute_prems_sco(**d1)
                sco_level = d['level'] if d['sco_level'] == Lvl.DFLT else d['sco_level']
                values['sco'] = prems[d['prot'], entlevel_idx(sco_level)]
            if d['eco_level'] > Lvl.NONE:
                d1 = {k: d[k] for k in
                      ('aphyield', 'tayield', 'tause', 'county', 'crop',
                       'practice', 'croptype')}
                prems = self.compute_prems_eco(**d1)
                values['eco'] = prems[d['prot'], 0 if d['eco_level'] == 85 else 1]
            premiums[crop] = values
        return premiums


# ----------------
# Helper functions
# ----------------
def entlevel_idx(intval):
    if intval < 50 or intval > 85:
        raise ValueError('Invalid level for Enterprise unit')
    return (intval - 50)//5


def arclevel_idx(intval):
    if intval < 70 or intval > 90:
        raise ValueError('Invalid level for ARC unit')
    return (intval - 70)//5


# -------------------------------------
# Helper functions for text file import
# -------------------------------------
def load(filename, processor, **kwargs):
    """
    Try to load a pickle file with the filename.  If it doesn't exist, load the
    textfile, create its dict, and save its dict to a pickle file.
    """
    picklename = f'{DATADIR}/{filename}.pkl'
    if os.path.isfile(picklename):
        print(f'Found {picklename}.')
        with open(picklename, 'rb') as f:
            data = pickle.load(f)
    else:
        print(f'{picklename} not found; loading textfile.')
        items = get_file_items(f'{DATADIR}/{filename}.txt')
        data = processor(items, **kwargs)
        print(f'saving {picklename}')
        with open(picklename, 'wb') as f:
            pickle.dump(data, f)
    return data


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


# ----------
# PROCESSORS
# ----------
def float_key_float_tuple(items, rest=None):
    """
    Get a nested list of items for the given file, then construct a dict
    using the float-converted, first item in each row as the dict key and setting
    the associated value to a tuple of floats from the other items of interest,
    which are selected via the 'rest' argument.
    """
    if rest is None:
        rest = slice(1, None, None)
    return {float(item[0]): tuple(float(it) for it in item[rest]) for item in items}


def int_key_float_tuple(items, rest=None):
    if rest is None:
        rest = slice(1, None, None)
    return {int(item[0]): tuple(float(it) for it in item[rest]) for item in items}


def int_key_list_float_tuple(items):
    items = get_file_items(f'{DATADIR}/draws.txt')
    result = {}
    for code, _, yielddraw, pricedraw in items:
        result.setdefault(int(code), []).append((float(yielddraw), float(pricedraw)))
    return result


def int_key_float_array(items, shape=None, rest=None):
    if rest is None:
        rest = slice(1, None, None)
    return ({int(itm[0]): np.array([float(it) for it in itm[rest]]).reshape(shape)
             for itm in items} if shape is not None else
            {int(itm[0]): np.array([float(it) for it in itm[rest]])
             for itm in items})


def special_counties(items):
    return {f'{cty}, {st}': f'{int(stcode):02}{int(ctycode):03}'
            for stcode, ctycode, cty, st in items}


def special_high_risk(items):
    return {itm[0]+itm[1]: (float(itm[2]), float(itm[3])) for itm in items}


def special_parameters(items):
    return {f'{int(itm[0]):02d}{int(itm[1]):02d}':
            (float(itm[2]), float(itm[3])) for itm in items}


def int_key_int_value(items):
    return {int(item[0]): int(item[1]) for item in items}


def float_pair_float_float_tuple(items):
    return {float(itm[0]): (float(itm[1]), tuple(float(it) for it in itm[2:]))
            for itm in items}


def int_pair_float_float_tuple(items, rest=None):
    if rest is None:
        rest = slice(2, None, None)
    return {int(itm[0]): (float(itm[1]), tuple(float(it) for it in itm[rest]))
            for itm in items}


def float_pair_float_float_array(items, shape=None, rest=None):
    if rest is None:
        rest = slice(2, None, None)
    return {float(itm[0]): (float(itm[1]), tuple(float(it) for it in itm[rest]))
            for itm in items}


def int_pair_float_float_array(items, shape=None):
    return ({int(itm[0]):
             (float(itm[1]),
              np.array([float(it) for it in itm[2:]]).reshape(shape))
             for itm in items} if shape is not None else
            {int(itm[0]): (float(itm[1]), np.array([float(it) for it in itm[2:]]))
             for itm in items})


# ------------
# DICT GETTERS
# ------------
def get_enter_id():
    return load('enterId', int_key_int_value)


def get_beta_id():
    return load('betaid', int_key_int_value)


def get_options():
    return load('options', int_key_float_tuple, rest=slice(1, 4, None))


def get_rates():
    return load('rates', int_key_float_tuple)


def get_rate_diff():
    return load('rateDiff', float_key_float_tuple)


def get_prate_diff():
    return load('prateDiff', float_key_float_tuple)


def get_enterprise_factor():
    return load('enterpriseFactor', float_key_float_tuple)


def get_penterprise_factor():
    return load('penterpriseFactor', float_key_float_tuple)


def get_enter_factor_rev():
    return load('enterFactorRev', float_key_float_tuple)


def get_penter_factor_rev():
    return load('pEnterFactorRev', float_key_float_tuple)


def get_rev_lookup():
    return load('revLookup', int_key_float_tuple)


def get_draws():
    return load('draws', int_key_list_float_tuple)


def get_discount_enter():
    return load('discountEnter', int_key_float_array, shape=(8, 6))


def get_counties():
    return load('counties', special_counties)


def get_high_risk():
    return load('highRisk', special_high_risk)


def get_parameters():
    return load('parameters', special_parameters)


def get_arc_rp():
    return load('griphr', float_pair_float_float_tuple)


def get_arc_rphpe():
    return load('grip', float_pair_float_float_tuple)


def get_arc_yp():
    """
    The second column in the table is 65 coverage, which is not used
    """
    return load('grp', int_pair_float_float_tuple, rest=slice(3, None, None))


def get_sco_rp():
    return load('scoArp', int_key_float_array, shape=(36, 8), rest=slice(2, None, None))


def get_sco_rphpe():
    return load('scoArpw', int_key_float_array, shape=(36, 8),
                rest=slice(2, None, None))


def get_sco_yp():
    return load('scoYp', int_key_float_array, rest=slice(2, None, None))


def get_eco():
    return load('eco', int_key_float_array, shape=(36, 3, 2))
