from numpy import zeros, array, log, exp
import numpy as np
import os
import pickle

from util import Crop, Unit, Lvl

DATADIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
np.set_printoptions(precision=6)
np.set_printoptions(suppress=True)


class Premium:
    """
    Class for computing Enterprise and ARC premiums for RP, RP-HPE, YO
    """
    def __init__(self):
        self.load_lookups()
        # preset subsidy values
        self.subsidy_ent = array((0.8,  0.8,  0.8,  0.8,  0.8,  0.77, 0.68, 0.53))
        self.subsidy_sco = 0.65
        self.subsidy_grip = array([0.59, 0.55, 0.55, 0.49, 0.44])
        self.subsidy_grp = array([0.59, 0.59, 0.55, 0.55, 0.51])
        self.subsidy_eco = 0.44

        self.cover = array([x/100 for x in range(50, 86, 5)])  # coverage levels
        self.arc_cover = array([x/100 for x in range(70, 91, 5)])  # arc coverage levels

        # User inputs
        # -----------
        # acres to insure for given county, crop, croptype and practice.
        self.acres = None
        # 0: standard policy, 1: deduction for hail/fire exclusion
        self.hailfire = None
        # 0: standard coverage, 1: premium for 5% prevent plant buyup
        self.prevplant = None
        # 0: no trend yield adjustment, 1: use trend-adjusted yields
        self.tause = None
        # 0: no yield exclusion, 1: allow certain past year's yield data (e.g. 2012)
        #     and replaced by an alternative yield.
        self.yieldexcl = None
        # Actual production history yield
        self.aphyield = None
        # Rate yield (Approved yield?)
        self.appryield = None
        # Trend-adjusted yield (takes into effect a positive trendline in historical
        #     yields).
        self.tayield = None
        # Risk related
        # Currently, user can provide either string (riskname) or integer(risk))
        self.riskname = None   # {'None', 'AAA', 'BBB', 'CCC', 'DDD'} dep. on county
        # 0 if riskname == 'None', 1 if riskname in('AAA', 2: 'BBB', 3: 'CCC', 4: 'DDD')
        self.risk = None

        # scalar variables
        # -------------------------
        self.expyield = None   # Looked up for area base premiums
        # Computed for area options (ECO, SCO)
        self.arevyield = self.tayield if self.tause else self.aphyield
        # Actual or estimated price.
        # Looked up for state, crop.  Actual matches RMA (avg harvest price for Feb).
        self.aphprice = None
        # Actual or estimate volatility factor.
        # Looked up for state, crop.  Actual matches RMA (options prices last week Feb).
        self.pvol = None
        # looked up by code and riskname if riskname is not 'None'
        self.highrisk = None
        # int looked up by code and riskname if riskname is not 'None'
        self.rtype = None

        # lookup key codes
        self.code = None       # int code for state/county/crop/etc..
        self.fcode = None      # int code with one extra digit for risk
        self.ccode = None      # county code for state/county/crop/etc..
        self.acode = None      # county code with decimal suffix for volatility
        # computed from revyield and mqty, stdqty, which are looked up based on
        # (revlook and # discountentr[3, jsize]).  Used in loss simulation
        self.adjmeanqty = None
        self.adjstdqty = None
        # interpolated lookup used to set RP, RP-HPE premium rates
        self.disenter = None
        # effective cover: coverage level times ratio of tayield/aphyield
        # used in intepolation and several other calculations.
        self.effcov = None
        self.jsize = None            # index based on acres
        # dollar amount based on revyield, aphprice, acres and cover.
        self.liab = None
        # dollar amount used in county options (SCO, ECO)
        self.aliab = None
        # revised cover: effcov if tause else cover
        self.revcov = None
        # revised yield: tayield if tause else appryield
        self.revyield = None
        # used in ARC: expected yield * price * max prot_factor (1.2)
        self.maxliab = None
        # log(aphprice) - pvol**2/2, used to compute harvest price in loss simulation.
        self.lnmean = None
        # multiplies in the hail/fire and prev plant rates in premium rate calc.
        self.multfactor = None
        self.prot_factor = None      # Protection factor (aka payment factor) for ARC
        # Used to lookup mqty, stdqty for loss simulation
        self.revlook = None
        # based on basepremrate and simulated losses
        # Arrays sized (8)
        self.rphpe_rateuse = None
        self.rp_rateuse = None

        # Arrays, tuples, vectors
        self.premrate = None         # Premium rates array (Erev, E)
        # Array sized (500, 2) 500 (pricedraw, yielddraw) pairs used in loss simulation
        self.selected_draws = None
        self.simloss = None          # Simulated Loss array (Yp, Rp, RpExc)

        # 3-tuples
        self.mqty = None             # Mean quantity used in loss simulation
        self.stdqty = None           # STD quantity used in loss simulation

        # (cur, prior) pairs
        self.baserate = None          # Continuous rating base rate
        # Interpolated from enterprisefactor, used to compute basepremrate for YP
        self.efactor = None
        # Interpolated from enterprisefactorrev, compute basepremrate for RP, RP-HPE
        self.efactor_rev = None
        # Interpolated from ratediff, used to scale all basepremrates.
        self.ratediff_fac = None

        # Array sized (2, 8, 2) ('YP', 'RP/RP-HPE') by levels by (cur, prior)
        self.basepremrate = None

        # Arrays sized (8, 2) (8 coverage levels) by 2 (cur, prior)
        # RMA base county differential
        self.ratediff = None
        self.enterprisefactor = None  # used to compute basepremrate for YP
        self.enterfactor_rev = None   # used to compute basepremrate for RP, RP-HPE

        # Arrays sized (8, 6) (8 coverage levels) by (6 acre size values)
        # RMA Eenterprise unit factor, used to get disenter, used to set premium rates.
        self.discountenter = None

        # Premium arrays
        self.prem_ent = None
        self.prem_arc = None
        self.prem_sco = None
        self.prem_eco = None

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
        self.set_effcov()
        self.set_factors()
        self.make_ye_adj()
        self.make_rev_liab()
        self.set_base_rates()
        self.set_base_prem_rates()
        self.limit_base_prem_rates()
        self.limit_baserate()
        self.set_qtys()
        self.simulate_losses()
        self.set_rates()
        self.set_prems()
        self.apply_subsidy()
        # TODO: Think about this more.  The orig code sets the premium to zero in this
        # edge case, which can't occur with the current data.
        # Perhaps it would be better to raise an error or put a negative
        # premium value if this ever happens...
        self.prem_ent = np.where(self.ratediff[:, 0].reshape(8, 1) < 0,
                                 np.zeros_like(self.prem_ent), self.prem_ent)
        return self.prem_ent

    def set_multfactor(self):
        """
        Set Multiplicative Factor used to scale rates for hailfire, prevplant
        """
        hfrate, pfrate, _ = self.options[self.options_key[self.code]]
        self.multfactor = 1
        if self.hailfire > 0:
            self.multfactor *= hfrate
        if self.prevplant == 1:
            self.multfactor *= pfrate

    def set_effcov(self):
        """
        Set the effective coverage level (Note: depends on tayield regardless of tause)
        """
        self.effcov = (0.0001 + self.cover * self.tayield / self.appryield).round(2)

    def set_factors(self):
        varpairs = [
            (self.ratediff[:, 0], 9), (self.ratediff[:, 1], 9),
            (self.enterprisefactor[:, 0], 3), (self.enterprisefactor[:, 1], 3),
            (self.enterfactor_rev[:, 0], 3), (self.enterfactor_rev[:, 1], 3),
            (self.discountenter[:, self.jsize], 4), ]
        rslts = self.interp(varpairs)
        self.ratediff_fac[:] = array(rslts[:2]).T
        self.efactor[:] = array(rslts[2:4]).T
        self.efactor_rev[:] = array(rslts[4:6]).T
        self.disenter[:] = rslts[6]

    def interp(self, varpairs):
        """
        Interpolate (or extrapolate up) by nearest cover values to effcov, then round.
        """
        cov, effcov = self.cover, self.effcov
        gap = cov[1] - cov[0]
        js, jps, jms = self.get_indices()
        rslts = []
        for var, ro in varpairs:
            # handle general case with possible extrapolation
            vdiff = np.where(js < 7,
                             var[jps] - var[js], var[js] - var[jms])
            rslt = (var[js] + vdiff * (effcov - cov[js]) / gap).round(ro)
            # modify result by three special cases
            rslt = np.where(
                np.logical_and(effcov > 0.75, self.ratediff[6, 0] == 0),
                (var[5] + (var[5] - var[4]) * (effcov - cov[5]) / gap).round(ro),
                rslt)
            rslt = np.where(effcov < cov[0], round(var[0], ro), rslt)
            rslt = np.where(not self.tause, var, rslt)
            rslts.append(rslt)
        return rslts

    def get_indices(self):
        """
        Get indices needed for interpolation
        """
        bignum = 10  # dummy value large enough to never be the minimum
        diff = np.empty((8, 8))
        for i in range(8):
            diff[i, :] = self.effcov[i] - self.cover
        js = np.argmin(np.where(diff >= 0,
                                diff, np.ones_like(diff)*bignum), axis=1)
        jps, jms = js + 1, js - 1
        jps = np.where(jps > 7, np.ones_like(jps)*7, jps)
        jms = np.where(jms < 0, np.zeros_like(jms), jms)
        return js, jps, jms

    def make_ye_adj(self):
        """
        Adjust factors for YE (vectorized)
        """
        jjhigh = 5 if self.ratediff[6, 0] == 0 else 7
        yeadj = np.where(np.logical_and(self.effcov > 0.85, self.yieldexcl > 0.5),
                         (self.effcov - 0.85) / 0.15, np.zeros_like(self.effcov))
        yeadj = np.where(self.effcov > 0.85,
                         1 + (np.minimum(1, yeadj) ** 3).round(7) * 0.05, yeadj)
        self.ratediff_fac[:, 0] = np.where(self.effcov > 0.85,
                                           self.ratediff_fac[:, 0] * yeadj,
                                           self.ratediff_fac[:, 0])
        self.efactor = np.where(self.effcov.reshape(8, 1) > 0.85,
                                np.minimum(self.efactor,
                                           self.enterprisefactor[jjhigh, :]),
                                self.efactor)

    def make_rev_liab(self):
        """
        Set the revised yield, the revised cover and the liability
        """
        self.revyield = self.tayield if self.tause else self.appryield
        self.revcov = self.effcov if self.tause else self.cover
        self.liab = ((self.revyield * self.cover + 0.001).round(1) *
                     self.aphprice * self.acres).round(0)

    def set_base_rates(self):
        """
        Set and limit vector (current/prior) base rates from RMA data
        """
        refyield, refrate, exponent, fixedrate = zeros(2), zeros(2), zeros(2), zeros(2)

        rkey = self.rates_key[self.code]
        (refyield[0], refrate[0], exponent[0], fixedrate[0],
         refyield[1], refrate[1], exponent[1], fixedrate[1]) = self.rates[rkey]

        self.baserate = np.minimum(np.maximum(
            (self.aphyield / refyield).round(2), 0.5), 1.5)
        self.baserate = (self.baserate ** exponent).round(8)
        self.baserate = (self.highrisk + self.baserate * refrate + fixedrate).round(8)
        if self.rtype > 1.5:
            self.baserate[:] = self.highrisk

    def set_base_prem_rates(self):
        """
        Set vector adjusted base premium rates
        """
        prod = self.baserate * self.ratediff_fac
        self.basepremrate = array((prod * self.efactor,
                                   prod * self.efactor_rev)).round(8)

    def limit_base_prem_rates(self):
        """
        Limit base premium rates min of cur and 1.2*prior (unpacking vectors)
        """
        bpr = self.basepremrate
        bpr[:, :, 0] = np.where(bpr[:, :, 0] > bpr[:, :, 1] * 1.2,
                                (bpr[:, :, 1] * 1.2).round(8), bpr[:, :, 0])
        bpr[:, :, 0] = np.where(bpr[:, :, 0] > 0.99,
                                zeros(2).reshape(2, 1), bpr[:, :, 0])

    def limit_baserate(self):
        """
        Limit base rate based on previous (unpacking vectors)
        and set revlook as min of baserate and 0.9999
        """
        if self.baserate[0] > self.baserate[1] * 1.2:
            self.baserate[0] = round(self.baserate[1] * 1.2, 8)
        self.revlook = round(min(self.baserate[0], 0.9999), 4)

    def set_qtys(self):
        """
        Compute mqty, stdqty and adjusted quantities
        """
        revLookup = int(
            self.revlook * 10000 * self.discountenter[3, self.jsize] + 0.5)
        self.mqty, self.stdqty = self.rev_lookup[revLookup]
        self.adjmeanqty = round(self.revyield * self.mqty / 100, 8)
        self.adjstdqty = round(self.revyield * self.stdqty / 100, 8)

    def simulate_losses(self):
        """
        Simulate losses for 500 (yield_draw, price_draw) pairs
        for cases (yp, rp, rphpe)
        """
        self.lnmean = round(log(self.aphprice) - (self.pvol ** 2 / 2), 8)
        simloss = zeros((500, 8, 3))
        draws = self.selected_draws
        yld = np.maximum(0, draws[:, 0] * self.adjstdqty + self.adjmeanqty)
        yld = np.repeat(yld[:, np.newaxis], 8, axis=1)
        simloss[:, :, 0] = np.maximum(0, self.revyield * self.revcov - yld)
        harprice = np.minimum(2 * self.aphprice,
                              exp(draws[:, 1] * self.pvol + self.lnmean))
        harprice = np.repeat(harprice[:, np.newaxis], 8, axis=1)
        guarprice = np.maximum(harprice, self.aphprice)
        simloss[:, :, 1] = np.maximum(0, (self.revyield * guarprice * self.revcov -
                                          yld * harprice))
        simloss[:, :, 2] = np.maximum(0, (self.revyield * self.aphprice * self.revcov -
                                          yld * harprice))
        self.simloss = simloss.mean(0)
        self.simloss[:, 0] = (self.simloss[:, 0] /
                              (self.revyield * self.revcov)).round(8)
        self.simloss[:, 1] = (self.simloss[:, 1] /
                              (self.revyield * self.revcov * self.aphprice)).round(8)
        self.simloss[:, 2] = (self.simloss[:, 2] /
                              (self.revyield * self.revcov * self.aphprice)).round(8)

    def set_rates(self):
        """
        Set the premium rates
        """
        self.rp_rateuse = (
            np.maximum(0.01 * self.basepremrate[1, :,  0],
                       self.simloss[:, 1] - self.simloss[:, 0])).round(8)
        self.rphpe_rateuse = (
            np.maximum(-0.5 * self.basepremrate[1, :, 0],
                       self.simloss[:, 2] - self.simloss[:, 0])).round(8)
        self.premrate[:] = (self.basepremrate[:, :, 0].T *
                            self.multfactor * self.disenter.reshape(8, 1))

    def set_prems(self):
        """
        Set the pre-subsidy premiums
        """
        self.prem_ent[:] = array((self.liab[:], self.liab[:], self.liab[:])).T
        self.prem_ent[:, 0] = (
            self.prem_ent[:, 0] *
            (self.premrate[:, 1] + self.rp_rateuse).round(8)).round(0)     # RP
        self.prem_ent[:, 1] = (
            self.prem_ent[:, 1] *
            (self.premrate[:, 1] + self.rphpe_rateuse).round(8)).round(0)  # RP-HPE
        self.prem_ent[:, 2] = (self.prem_ent[:, 2] *
                               self.premrate[:, 0].round(8)).round(0)      # YP

    def apply_subsidy(self):
        """
        Apply the subsidy
        """
        self.prem_ent[:] -= (self.prem_ent[:] *
                             self.subsidy_ent[:].reshape(8, 1)).round(0)
        self.prem_ent[:] = (self.prem_ent[:] / self.acres).round(2)

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
        self.fcode = self.code * 10 + 1 + self.risk
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
        self.ratediff_fac = zeros((8, 2))
        self.efactor = zeros((8, 2))
        self.efactor_rev = zeros((8, 2))
        self.disenter = zeros(8)
        self.baserate = zeros(2)

        # Initialize array to hold premiums
        self.prem_ent = zeros((8, 3))

        # Intermediate keys
        enterId = self.enter_id[self.code]
        betaId = self.beta_id[self.code]
        rd_key = self.rate_diff_key[self.fcode]
        prd_key = self.prate_diff_key[self.fcode]
        ef_key = self.enterprise_factor_key[self.fcode]
        pef_key = self.penterprise_factor_key[self.fcode]
        efr_key = self.enter_factor_rev_key[self.fcode]
        pefr_key = self.penter_factor_rev_key[self.fcode]

        self.premrate = zeros((8, 2))  # Premium rates array (YP, RP/RPHPE)
        self.simloss = zeros((8, 3))   # Simulated losses array (YP, RP, RPHPE)

        # Look up info from the dicts created when the object was constructed
        self.highrisk, self.rtype = ((0, 0) if self.risk == 0 else
                                     self.high_risk[str(self.code)+self.riskname])
        self.discountenter = self.discount_enter[enterId]
        self.ratediff = array((self.rate_diff[rd_key],
                               self.prate_diff[prd_key])).T
        self.enterprisefactor = array((self.enterprise_factor[ef_key],
                                       self.penterprise_factor[pef_key])).T
        self.enterfactor_rev = array((self.enter_factor_rev[efr_key],
                                     self.penter_factor_rev[pefr_key])).T
        self.selected_draws = np.array(self.draws[betaId])

    # -----------------------
    # ARC PREMIUMS
    # -----------------------
    def compute_prems_arc(self, county='Champaign, IL', crop='Corn',
                          practice='Non-irrigated', croptype='Grain',
                          prot_factor=1):
        """
        Get values for each area type and level 70, 75, ..., 90
        """

        county = int(self.counties[county]) if isinstance(county, str) else county
        state = self.rev_states[f'{county:02d}'[:-3]]
        if state in 'AL FL PA VA WV GA'.split():
            raise ValueError(f'Cannot calculate ARC premiums for {state}.')

        self.prem_arc = zeros((5, 3))
        self.store_user_settings_arc(county, crop, practice, croptype, prot_factor)
        subsidies = (self.subsidy_grip, self.subsidy_grip, self.subsidy_grp)
        if (self.acode not in self.arc_rp_key or
                self.acode not in self.arc_rphpe_key or
                self.ccode not in self.arc_yp_key):
            raise ValueError('No ARC data for specified county/crop/type/practice')

        dictvals = (self.arc_rp[self.arc_rp_key[self.acode]],
                    self.arc_rphpe[self.arc_rphpe_key[self.acode]],
                    self.arc_yp[self.arc_yp_key[self.ccode]])
        for i, subsidy in enumerate(subsidies):
            self.compute_prem_arc(subsidy, dictvals[i], i)
        return self.prem_arc

    def compute_prem_arc(self, subsidy, ardictval, idx):
        """
        Compute premiums for the given unit info
        """
        rate = zeros(5)
        self.expyield, rate[:] = ardictval
        self.maxliab = round(self.expyield * self.aphprice * 1.2, 2)
        self.prem_arc[:, idx] = (self.maxliab * 100 * rate).round(0)
        self.prem_arc[:, idx] -= (self.prem_arc[:, idx] * subsidy).round(0)
        self.prem_arc[:, idx] = (self.prem_arc[:, idx] / 100 *
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
        # int code used to key into dicts
        self.acode = self.ccode * 100 + int(100 * self.pvol)

    # -----------------------
    # SCO PREMIUMS
    # -----------------------
    def compute_prems_sco(self, aphyield=180, tayield=190, tause=1,
                          county='Champaign, IL', crop='Corn',
                          practice='Non-irrigated', croptype='Grain'):
        """ Compute all SCO premiums """

        self.store_user_settings_sco(aphyield, tayield, tause, county,
                                     crop, practice, croptype)

        vals = (self.sco_rp[self.sco_rp_key[self.ccode]],
                self.sco_rphpe[self.sco_rphpe_key[self.ccode]],
                self.sco_yp[self.sco_yp_key[self.ccode]])
        self.prem_sco = zeros((8, 3))
        for i, val in enumerate(vals):
            self.compute_prem_sco(val, i)
        return self.prem_sco

    def compute_prem_sco(self, rate, unit):
        """
        Compute the sco premium for the given dict and unit index
        """
        if unit < 2:
            idx = int((self.pvol - 0.05)*100)
            rate = rate[idx, :]
        self.prem_sco[:, unit] = (self.aliab * (0.86 - self.cover) * rate).round(2)
        self.prem_sco[:, unit] -= (self.subsidy_sco * self.prem_sco[:, unit]).round(2)

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

    # ------------
    # ECO PREMIUMS
    # ------------
    def compute_prems_eco(self, aphyield=180, tayield=190, tause=1,
                          county='Champaign, IL', crop='Corn',
                          practice='Non-irrigated', croptype='Grain'):
        """ Compute all ECO premiums """
        self.store_user_settings_eco(aphyield, tayield, tause, county,
                                     crop, practice, croptype)
        mult = array([[0.04, 0.09]]).T  # 90% - 86%, 95% - 86%
        self.prem_eco = zeros((2, 3))
        rate = zeros((2, 3))
        idx = int((self.pvol - 0.05)*100)
        if self.ccode not in self.eco_key:
            return
        key = self.eco_key[self.ccode]
        if key not in self.eco:
            return
        rate = self.eco[key][idx][::-1, :].T  # reorder colums as (RP, RP-HPE, YP)
        self.prem_eco = (self.aliab * mult * rate * (1 - self.subsidy_eco)).round(2)
        return self.prem_eco

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
        self.croptypes = {'Grain': 16, 'No Type Specified': 997, 'Winter': 11,
                          'Spring': 12}

        # County products have some different practices and croptypes
        self.cpractices = {'Nfac (non-irrigated)': 53,
                           'Nfac (Irrigated)': 53,
                           'Fac (non-irrigated)': 53,
                           'Fac (Irrigated)': 53,
                           'Non-irrigated': 3,
                           'Irrigated': 3}

        self.risk_classes = {'None': 0, 'AAA': 1, 'BBB': 2, 'CCC': 3, 'DDD': 4}
        self.rev_risk_classes = {v: k for k, v in self.risk_classes.items()}
        self.states = {
            'IL': '17', 'AL': '01', 'AR': '05', 'FL': '12', 'GA': '13', 'IN': '18',
            'IA': '19', 'KS': '20', 'KY': '21', 'LA': '22', 'MD': '24', 'MI': '26',
            'MN': '27', 'MS': '28', 'MO': '29', 'NE': '31', 'NC': '37', 'ND': '38',
            'OH': '39', 'PA': '42', 'SC': '45', 'SD': '46', 'TN': '47', 'VA': '51',
            'WV': '54', 'WI': '55', 'OK': '40', 'TX': '48'}
        self.rev_states = {v: k for k, v in self.states.items()}
        self.counties = get_counties()
        self.rev_counties = {v: k for k, v in self.counties.items()}
        self.enter_id = get_enter_id()
        self.beta_id = get_beta_id()
        self.options_key = get_options_key()
        self.options = get_options()
        self.discount_enter = get_discount_enter()
        self.rates_key = get_rates_key()
        self.rates = get_rates()
        self.rate_diff_key = get_rate_diff_key()
        self.rate_diff = get_rate_diff()
        self.prate_diff_key = get_prate_diff_key()
        self.prate_diff = get_prate_diff()
        self.enterprise_factor_key = get_enterprise_factor_key()
        self.enterprise_factor = get_enterprise_factor()
        self.penterprise_factor_key = get_penterprise_factor_key()
        self.penterprise_factor = get_penterprise_factor()
        self.enter_factor_rev_key = get_enter_factor_rev_key()
        self.enter_factor_rev = get_enter_factor_rev()
        self.penter_factor_rev_key = get_penter_factor_rev_key()
        self.penter_factor_rev = get_penter_factor_rev()
        self.rev_lookup = get_rev_lookup()
        self.draws = get_draws()
        self.high_risk = get_high_risk()
        self.parameters = get_parameters()
        # dicts with float key and value tuple(1, tuple(5))
        self.arc_rp_key = get_arc_rp_key()
        self.arc_rp = get_arc_rp()
        self.arc_rphpe_key = get_arc_rphpe_key()
        self.arc_rphpe = get_arc_rphpe()
        self.arc_yp_key = get_arc_yp_key()
        self.arc_yp = get_arc_yp()
        # dict with key code, value array(36, 8) (ivol, cover)
        self.sco_rp_key = get_sco_rp_key()
        self.sco_rp = get_sco_rp()
        self.sco_rphpe_key = get_sco_rphpe_key()
        self.sco_rphpe = get_sco_rphpe()
        # dict with key code, value array(8) (cover)
        self.sco_yp_key = get_sco_yp_key()
        self.sco_yp = get_sco_yp()
        # dict with key code, value array(36, 3, 2) (ivol, unit, cov)
        self.eco_key = get_eco_key()
        self.eco = get_eco()

    def make_code(self, county, crop, croptype, practice):
        """
        Construct an integer code used to key in some tabular data
        """
        cty = int(self.counties[county]) if isinstance(county, str) else county
        if f'{cty:05d}' not in self.rev_counties:
            raise ValueError('Cannot compute premiums for county; no data available')
        crp = self.crops[crop] if isinstance(crop, str) else crop
        crptype = self.croptypes[croptype] if isinstance(croptype, str) else croptype
        prac = self.practices[practice] if isinstance(practice, str) else practice
        return int(f'{cty:05d}{crp:02d}{crptype:03d}{prac:03d}')

    def make_ccode(self, county, crop, croptype, practice):
        """
        Construct a COUNTY integer code used to key in some tabular data
        """
        cty = int(self.counties[county]) if isinstance(county, str) else county
        crp = self.crops[crop] if isinstance(crop, str) else crop
        crptype = self.croptypes[croptype] if isinstance(croptype, str) else croptype
        prac = self.cpractices[practice] if isinstance(practice, str) else practice
        return int(f'{cty:05d}{crp:02d}{crptype:03d}{prac:03d}')

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
                values['base'] = prems[arclevel_idx(d['level']), d['protection']]
            if d['sco_level'] > Lvl.NONE:
                d1 = {k: d[k] for k in
                      ('aphyield', 'tayield', 'tause', 'county', 'crop',
                       'practice', 'croptype')}
                prems = self.compute_prems_sco(**d1)
                sco_level = d['level'] if d['sco_level'] == Lvl.DFLT else d['sco_level']
                values['sco'] = prems[entlevel_idx(sco_level), d['protection']]
            if d['eco_level'] > Lvl.NONE:
                d1 = {k: d[k] for k in
                      ('aphyield', 'tayield', 'tause', 'county', 'crop',
                       'practice', 'croptype')}
                prems = self.compute_prems_eco(**d1)
                values['eco'] = prems[0 if d['eco_level'] == 90 else 1, d['protection']]
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


def get_file_items(filename):
    """
    Get file contents then return a nested list of the tab separated
    values for each line.
    """
    with open(filename, 'r') as f:
        contents = f.read()
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
    return {f'{cty}, {st}': (f'{int(stcode):02}{int(ctycode):03}')
            for stcode, ctycode, cty, st in items}


def special_high_risk(items):
    return {itm[0]+itm[1]: (float(itm[2]), int(itm[3])) for itm in items}


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


def get_options_key():
    return load('options_key', int_key_int_value)


def get_options():
    return load('options', int_key_float_tuple)


def get_rates_key():
    return load('rates_key', int_key_int_value)


def get_rates():
    return load('rates', int_key_float_tuple)


def get_rate_diff_key():
    return load('rateDiff_key', int_key_int_value)


def get_rate_diff():
    return load('rateDiff', float_key_float_tuple)


def get_prate_diff_key():
    return load('prateDiff_key', int_key_int_value)


def get_prate_diff():
    return load('prateDiff', float_key_float_tuple)


def get_enterprise_factor_key():
    return load('enterpriseFactor_key', int_key_int_value)


def get_enterprise_factor():
    return load('enterpriseFactor', float_key_float_tuple)


def get_penterprise_factor_key():
    return load('penterpriseFactor_key', int_key_int_value)


def get_penterprise_factor():
    return load('penterpriseFactor', float_key_float_tuple)


def get_enter_factor_rev_key():
    return load('enterFactorRev_key', int_key_int_value)


def get_enter_factor_rev():
    return load('enterFactorRev', float_key_float_tuple)


def get_penter_factor_rev_key():
    return load('pEnterFactorRev_key', int_key_int_value)


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


def get_arc_rp_key():
    return load('griphr_key', int_key_int_value)


def get_arc_rp():
    return load('griphr', float_pair_float_float_tuple)


def get_arc_rphpe_key():
    return load('grip_key', int_key_int_value)


def get_arc_rphpe():
    return load('grip', float_pair_float_float_tuple)


def get_arc_yp_key():
    return load('grp_key', int_key_int_value)


def get_arc_yp():
    """
    The first rate column is 65 coverage, which is not used.
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


def get_sco_yp_key():
    return load('scoYp_key', int_key_int_value)


def get_sco_yp():
    return load('scoYp', int_key_float_array)


def get_eco_key():
    return load('eco_key', int_key_int_value)


def get_eco():
    return load('eco', int_key_float_array, shape=(36, 3, 2))
