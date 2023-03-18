from numpy import zeros, array
import numpy as np
from math import log, exp
import os
import pickle

from util import Crop, Unit, Lvl

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
        self.appryield = None  # Approved yield
        self.tayield = None    # Trend-adjusted yield
        self.expyield = None   # For area base premiums
        # for area options
        self.arevyield = self.tayield if self.tause else self.aphyield

        # price / volatility
        self.aphprice = None   # Actual or estimated production history price
        self.pvol = None       # Actual or estimate volatility factor

        # Risk related
        self.riskname = None   # {'None', 'AAA', 'BBB', 'CCC', 'DDD'} dep. on county
        # 0 if riskname == 'None', 1 if riskname in('AAA', 2: 'BBB', 3: 'CCC', 4: 'DDD')
        self.risk = None
        self.highrisk = None   # float looked up by code and riskname in high_risk dict
        self.rtype = None      # int looked up by code and riskname in high_risk dict

        # lookup key codes
        self.code = None       # code for state/county/crop/etc..
        self.fcode = None      # code with decimal suffix for risk
        self.ccode = None       # county code for state/county/crop/etc..
        self.acode = None      # county code with decimal suffix for volatility

        # scalar variables
        # -------------------------
        self.adjmeanqty = None
        self.adjstdqty = None
        self.disenter = None
        self.effcov = None
        self.jsize = None            # based on acres
        self.liab = None
        self.aliab = None
        self.maxliab = None
        self.lnmean = None
        self.multfactor = None
        self.premrate = None         # Premium rates array (Erev, E)
        self.revcov = None
        self.revyield = None
        self.selected_draws = None
        self.simloss = None          # Simulated Loss array (Yp, Rp, RpExc)
        self.revexc_rateuse = None
        self.rev_rateuse = None
        self.prot_factor = None      # Protection factor for ARC

        # 3-tuples
        self.mqty = None
        self.stdqty = None

        # (current/prev) pairs
        self.baserate = None          # Continuous rating base rate
        self.efactor = None
        self.efactor_rev = None
        self.ratediff_fac = None
        self.revlook = None

        # Array sized (2, 2)  ('E', 'Erev') by (cur, prior)
        self.basepremrate = None

        # Arrays sized (8, 2) (8 coverage levels) by 2 (cur, prior)
        self.ratediff = None
        self.enterprisefactor = None
        self.enterfactor_rev = None

        # Arrays sized (8, 6) (8 coverage levels) by (6 acre size values)
        self.discountenter = None

        # Premium arrays
        self.prem = None
        self.arc_prem = None
        self.sco_prem = None
        self.eco_prem = None

    # -----------------------------
    # MAIN METHOD: COMPUTE PREMIUMS
    # -----------------------------
    def compute_prems_ent(self, aphyield=180, appryield=180, tayield=190, acres=100,
                          hailfire=0, prevplant=0, risk='None', tause=1,
                          yieldexcl=0, county='Champaign, IL', crop='Corn',
                          practice='Non-irrigated', croptype='Grain'):
        """
        With farm-specific inputs, compute premiums for optional, basic and enterprise,
        units with RP, RP-HPE or YO protection for all coverage levels.
        """
        self.store_user_settings_ent(aphyield, appryield, tayield, acres, hailfire,
                                     prevplant, risk, tause, yieldexcl, county,
                                     crop, practice, croptype)
        self.initialize_arrays()
        self.set_multfactor()
        for i in range(8):  # index i corresponds to coverage level
            if self.ratediff[i, 0] > 0:
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
        self.multfactor = 1
        if self.hailfire > 0:
            self.multfactor *= hfrate
        if self.prevplant == 1:
            self.multfactor *= pfrate
        if self.prevplant == 2:
            self.multfactor *= ptrate

    def set_effcov(self, i):
        """
        Set the effective coverage level
        """
        self.effcov = round(0.0001 + self.cover[i] *
                            self.tayield / self.appryield, 2)

    def set_factors(self, i):
        """
        Set 4 vector factors and 2 scalar factors used to compute base premium rates
        """
        self.ratediff_fac[:] = (
            self.get_factor(self.ratediff, i, 0, 9),
            self.get_factor(self.ratediff, i, 1, 9))
        self.efactor[:] = (
            self.get_factor(self.enterprisefactor, i, 0, 3),
            self.get_factor(self.enterprisefactor, i, 1, 3))
        self.efactor_rev[:] = (
            self.get_factor(self.enterfactor_rev, i, 0, 3),
            self.get_factor(self.enterfactor_rev, i, 1, 3))
        self.disenter = self.get_factor(self.discountenter, i, self.jsize, 4)

    def get_factor(self, var, i, j2, ro):
        """
        Given a variable (e.g. ratediff), a 2nd index and a roundoff precision,
        first compute some indices, then use them to get a factor (e.g. ratediff_fac)
        """
        def maxind(ifirst, ilast, offset):
            """
            Get the largest index of cover for which the condition holds, and
            return it after subtracting offset.
            """
            i = ilast
            while i >= ifirst and self.effcov < self.cover[i]:
                i -= 1
            return i + 1 - offset

        jlow, jhigh, jfloor = maxind(1, 6, 1), maxind(0, 6, 0), maxind(1, 7, 1)
        if self.effcov > 0.75 and self.ratediff[6, 0] == 0:
            jlow, jhigh, jfloor = 4, 5, 5

        return (round(var[jfloor, j2] + (var[jhigh, j2] - var[jlow, j2]) *
                      (self.effcov - self.cover[jfloor]) * 20 + 1e-11, ro)
                if self.tause else var[i, j2])

    def make_ye_adj(self, i):
        """
        Adjust factors for YE (vectorized)
        """
        jjhigh = 5 if self.ratediff[6, 0] == 0 else 7
        yeadj = 0
        if self.effcov > 0.85:
            if self.yieldexcl > 0.5:
                yeadj = (self.effcov - 0.85) / 0.15
            yeadj = 1 + round(min(1, yeadj) ** 3, 7) * 0.05
            self.ratediff_fac[0] *= yeadj
            self.efactor = np.minimum(self.efactor, self.enterprisefactor[jjhigh, :])

    def make_rev_liab(self, i):
        """
        Set the revised yield, the revised cover and the liability
        """
        # step 1
        self.revyield = self.tayield if self.tause else self.appryield
        self.revcov = self.effcov if self.tause else self.cover[i]
        self.liab = round(round(self.revyield * self.cover[i] + 0.001, 1) *
                          self.aphprice * self.acres, 0)

    def set_base_rates(self, i):
        """
        Set and limit vector base rates from RMA data
        """
        # step 2.01: Look up current and previous year rates.
        refyield, refrate, exponent, fixedrate = zeros(2), zeros(2), zeros(2), zeros(2)
        (refyield[0], refrate[0], exponent[0], fixedrate[0],
         refyield[1], refrate[1], exponent[1], fixedrate[1]) = self.rates[self.code]

        # Worksheet steps 1, 2: Continuous rating base rate (current/prior)
        self.baserate = np.minimum(np.maximum(
            (self.aphyield / refyield).round(2), 0.5), 1.5)

        # step 2.02: vectorized (current/prior)
        self.baserate = (self.baserate ** exponent).round(8)

        # step 2.03: vectorized (current/prior)
        self.baserate = (self.highrisk + self.baserate * refrate + fixedrate).round(8)
        if self.rtype > 1.5:
            self.baserate[:] = self.highrisk
        self.revlook[:] = self.baserate

    def set_base_prem_rates(self, i):
        """
        Set vector adjusted base premium rates
        """
        # Worksheet step 8.  Calculate Base Premium Rates Adjusted Base Rate x
        # coverage level rate differential.
        # step 2.04
        prod = self.baserate * self.ratediff_fac
        self.basepremrate = array((prod * self.efactor,
                                   prod * self.efactor_rev)).round(8)

    def limit_base_prem_rates(self, i):
        """
        Limit base premium rates based on prior (unpacking vectors)
        """
        # Preliminary base rate is min of cur and 1.2 * prev.
        # step 2.05
        var = self.basepremrate
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
        if self.revlook[0] > self.revlook[1] * 1.2:
            self.revlook[0] = round(self.revlook[1] * 1.2, 8)
        self.revlook[0] = round(min(self.revlook[0], 0.9999), 4)

    def limit_baserate(self, i):
        """
        Limit base rate based on previous (unpacking vectors)
        """
        # step 2.07
        if self.baserate[0] > self.baserate[1] * 1.2:
            self.baserate[0] = round(self.baserate[1] * 1.2, 8)

    def set_qtys(self, i):
        """
        Compute mqty and stdqty
        """
        revLookup = int(
            self.revlook[0] * 10000 * self.discountenter[3, self.jsize] + 0.5)
        self.mqty, self.stdqty = self.rev_lookup[revLookup]

    def simulate_losses(self, i):
        """
        Loop through 500 yield, price pairs, incrementing losses.
        """
        # step 5.02
        self.adjmeanqty = round(self.revyield * self.mqty / 100, 8)
        self.adjstdqty = round(self.revyield * self.stdqty / 100, 8)
        self.lnmean = round(log(self.aphprice) - (self.pvol ** 2 / 2), 8)
        # step 5.04 simulate losses

        simloss = zeros(3)  # (Yp, Rp, RpExc)
        for yielddraw, pricedraw in self.selected_draws:
            # yield protection
            yld = max(0, yielddraw * self.adjstdqty + self.adjmeanqty)
            loss = max(0, self.revyield * self.revcov - yld)
            simloss[0] += loss
            # revenue protection
            harPrice = min(2 * self.aphprice,
                           exp(pricedraw * self.pvol + self.lnmean))
            guarPrice = max(harPrice, self.aphprice)
            loss = max(0, self.revyield * guarPrice * self.revcov - yld * harPrice)
            simloss[1] += loss
            # revenue protection with harvest price exclusion
            loss = max(0, self.revyield * self.aphprice * self.revcov - yld * harPrice)
            simloss[2] += loss
        # step 5.05
        ct = len(self.selected_draws)
        self.simloss[0] = round((simloss[0] / ct) / (self.revyield * self.revcov), 8)
        self.simloss[1] = round(simloss[1] / ct /
                                (self.revyield * self.revcov * self.aphprice), 8)
        self.simloss[2] = round(simloss[2] / ct /
                                (self.revyield * self.revcov * self.aphprice), 8)

    def set_rates(self, i):
        """
        Set the premium rates
        """
        # step 5.06
        self.rev_rateuse = round(max(0.01 * self.basepremrate[0, 0],
                                 self.simloss[1] - self.simloss[0]), 8)
        self.revexc_rateuse = round(max(-0.5 * self.basepremrate[0, 0],
                                    self.simloss[2] - self.simloss[0]), 8)
        # step 6  No historical revenue capping is performed
        # step 8.01
        self.premrate[0] = self.basepremrate[0, 0] * self.multfactor * self.disenter
        self.premrate[1] = self.basepremrate[1, 0] * self.multfactor * self.disenter

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
        self.set_prem(self.premrate[1], i, 0, self.rev_rateuse)       # RP
        self.set_prem(self.premrate[1], i, 1, self.revexc_rateuse)    # RP-HPE
        self.set_prem(self.premrate[0], i, 2)                        # YP

    def apply_subsidy(self, i):
        """
        Apply the subsidy
        """
        for j in range(3):
            self.prem[i, j] -= round(self.prem[i, j] * self.subsidy[i], 0)
            self.prem[i, j] = round(self.prem[i, j] / self.acres, 2)

    def store_user_settings_ent(self, aphyield, appryield, tayield, acres, hailfire,
                                prevplant, risk, tause, yieldexcl, county, crop,
                                practice, croptype):
        """
        Store settings provide by user when calling calc_premiums, and calculate
        some values derived from them.
        """
        self.aphyield = aphyield
        self.appryield = appryield
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
        self.highrisk = None
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
        self.aphprice, self.pvol = self.parameters[self.pcode]

        # Set index based on acreage
        self.jsize = (0 if self.acres < 50 else 1 if self.acres < 100 else
                      2 if self.acres < 200 else 3 if self.acres < 400 else
                      4 if self.acres < 800 else 5)

    def initialize_arrays(self):
        """
        Initialize arrays for premium calculation
        """
        # Initialize current/prev arrays
        self.ratediff_fac = zeros(2)
        self.efactor = zeros(2)
        self.efactor_rev = zeros(2)
        self.baserate = zeros(2)
        self.revlook = zeros(2)

        # Initialize array to hold premiums
        self.prem = zeros((8, 3))

        enterId = self.enter_id[self.code]
        betaId = self.beta_id[self.code]

        self.premrate = zeros(2)  # Premium rates array (Erev, E)
        self.simloss = zeros(3)   # Simulated losses array (Yp, Rp, RpExc)

        # Look up info from the dicts created when the object was constructed
        self.highrisk, self.rtype = ((0, 0) if self.risk == 0 else
                                     self.high_risk[str(self.code)+self.riskname])
        self.discountenter = self.discount_enter[enterId]
        self.ratediff = array((self.rate_diff[self.fcode],
                               self.prate_diff[self.fcode])).T
        self.enterprisefactor = array((self.enterprise_factor[self.fcode],
                                       self.penterprise_factor[self.fcode])).T
        self.enterfactor_rev = array((self.enter_factor_rev[self.fcode],
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
        self.expyield, rate[:] = ardict[code]
        self.maxliab = round(self.expyield * self.aphprice * 1.2, 2)
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
        self.aphprice, self.pvol = self.parameters[self.pcode]
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

        keys = (self.sco_rp_key[self.ccode], self.sco_rphpe_key[self.ccode], self.ccode)
        self.sco_prem = zeros((3, 8))
        for i, d in enumerate(zip((self.sco_rp, self.sco_rphpe, self.sco_yp), keys)):
            self.compute_prem_sco(d, i)
        return self.sco_prem

    def compute_prem_sco(self, rate_dict, unit):
        """
        Compute the sco premium for the given dict and unit index
        """
        rdict, key = rate_dict
        if key not in rdict:
            # return
            raise KeyError('key not in rdict')
        rate = rdict[key]
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
        self.ccode = self.make_ccode(county, crop, croptype, practice)
        self.pcode = self.make_pcode()
        # read price and volatility from parameters
        self.aphprice, self.pvol = self.parameters[self.pcode]
        self.arevyield = self.tayield if self.tause else self.aphyield
        self.aliab = self.arevyield * self.aphprice

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
        if self.ccode not in self.eco_key:
            # return
            raise KeyError('self.ccode not in self.eco_key')
        key = self.eco_key[self.ccode]
        if key not in self.eco:
            # return
            raise KeyError('key not in self.eco')
        rate = self.eco[key][idx][::-1, :]  # reorder rows as (RP, RP-HPE, YP)
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
        self.aphprice, self.pvol = self.parameters[self.pcode]
        self.arevyield = self.tayield if self.tause else self.aphyield
        self.aliab = self.arevyield * self.aphprice

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
        self.croptypes = {'Grain': 16, 'No Type Specified': 997, 'Winter': 11}

        # County products have some different practices and croptypes
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
        self.sco_rp_key = get_sco_rp_key()
        self.sco_rp = get_sco_rp()
        self.sco_rphpe_key = get_sco_rphpe_key()
        self.sco_rphpe = get_sco_rphpe()
        # dict with key code, value array(8) (cover)
        self.sco_yp = get_sco_yp()
        # dict with key code, value array(36, 3, 2) (ivol, unit, cov)
        self.eco_key = get_eco_key()
        self.eco = get_eco()

    def make_code(self, county, crop, croptype, practice):
        """
        Construct an integer code used to key in some tabular data
        """
        cty = self.counties[county] if isinstance(county, str) else county
        crp = self.crops[crop] if isinstance(crop, str) else crop
        crptype = self.croptypes[croptype] if isinstance(croptype, str) else croptype
        prac = self.practices[practice] if isinstance(practice, str) else practice
        return int(f'{int(cty):05d}{crp:02d}{crptype:03d}{prac:03d}')

    def make_ccode(self, county, crop, croptype, practice):
        """
        Construct a COUNTY integer code used to key in some tabular data
        """
        cty = self.counties[county] if isinstance(county, str) else county
        crp = self.crops[crop] if isinstance(crop, str) else crop
        crptype = self.croptypes[croptype] if isinstance(croptype, str) else croptype
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
        Given a list of dicts, one for each crop, containing specific choices of
        unit, level, sco_level, eco_level, Return a dict of dicts, each containing
        individual premiums for the base product and options.
        """
        premiums = {}
        if cropdicts is None:
            return premiums
        for d in cropdicts:
            crop = d['crop']
            name = ('Corn' if crop == Crop.CORN else 'Wheat' if crop == Crop.WHEAT
                    else 'Soybeans')
            cropcode = self.crops[name]
            d['crop'] = cropcode
            values = {'base': 0, 'sco': 0, 'eco': 0}
            if d['unit'] == Unit.ENT:
                d1 = {k: d[k] for k in
                      ('aphyield', 'appryield', 'tayield', 'acres', 'hailfire',
                       'prevplant', 'risk', 'tause', 'yieldexcl', 'county',
                       'crop', 'practice', 'croptype')}
                prems = self.compute_prems_ent(**d1)
                values['base'] = prems[entlevel_idx(d['level']), d['protection']]
            else:
                d1 = {k: d[k] for k in
                      ('county', 'crop', 'practice', 'croptype', 'prot_factor')}
                prems = self.compute_prems_arc(**d1)
                values['base'] = prems[d['protection'], arclevel_idx(d['level'])]
            if d['sco_level'] > Lvl.NONE:
                d1 = {k: d[k] for k in
                      ('aphyield', 'tayield', 'tause', 'county', 'crop',
                       'practice', 'croptype')}
                prems = self.compute_prems_sco(**d1)
                sco_level = d['level'] if d['sco_level'] == Lvl.DFLT else d['sco_level']
                values['sco'] = prems[d['protection'], entlevel_idx(sco_level)]
            if d['eco_level'] > Lvl.NONE:
                d1 = {k: d[k] for k in
                      ('aphyield', 'tayield', 'tause', 'county', 'crop',
                       'practice', 'croptype')}
                prems = self.compute_prems_eco(**d1)
                values['eco'] = prems[d['protection'], 0 if d['eco_level'] == 85 else 1]
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


def get_sco_rp_key():
    return load('scoArp_key', int_key_int_value)


def get_sco_rp():
    return load('scoArp', int_key_float_array, shape=(36, 8))


def get_sco_rphpe_key():
    return load('scoArpw_key', int_key_int_value)


def get_sco_rphpe():
    return load('scoArpw', int_key_float_array, shape=(36, 8))


def get_sco_yp():
    return load('scoYp', int_key_float_array, rest=slice(2, None, None))


def get_eco_key():
    return load('eco_key', int_key_int_value)


def get_eco():
    return load('eco', int_key_float_array, shape=(36, 3, 2))
