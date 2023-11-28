from numpy import zeros, array, log, exp
import numpy as np

from core.models.util import Crop, call_postgres_func, get_postgres_row

np.set_printoptions(precision=8)
np.set_printoptions(suppress=True)


class Premium:
    """
    Class for computing Enterprise and ARC premiums for RP, RP-HPE, YO
    Section and page numbers in docstrings refer to the relevant RMA premium calculation
    handbooks.
    """
    def __init__(self):
        self.load_lookups()
        self.cover = array([x/100 for x in range(50, 86, 5)])  # coverage levels
        self.arc_cover = array([x/100 for x in range(70, 91, 5)])  # arc coverage levels
        self.sco_top_level = 0.86
        self.eco_cover = array([x/100 for x in [90, 95]])

        # User inputs
        # -----------
        # The state: an integer code, e.g. 1 for AL, 17 for IL.
        self.state = None
        # The county: an integer code, unique for the state (usually an odd number)
        self.county = None
        # The crop: an integer code, always 41 for corn, 81 for soy, 11 for wheat.
        self.crop = None
        # The crop type: an integer commodity_id, always 16 for corn and 997 for soy,
        # 11 for winter wheat, 12 for spring wheat
        self.croptype = None
        # The practice: an integer code for e.g. irrigated, fac non-irrigated, etc.
        self.practice = None
        # The RMA projected harvest price Feb (lookup in ext_price, fallback futprice)
        self.projected_price = None
        # The RMA price volatility factor (lookup in ext_price, fallback prev year vol)
        self.price_volatility_factor = None
        # RMA expected_yield (lookup in ext_price)
        self.expected_yield = None
        # Either None or a 3-letter high risk code like 'AAA'
        self.subcounty = None
        # acres to insure for given county, crop, croptype and practice.
        self.acres = None
        # 1: deduction for hail/fire exclusion
        self.hailfire = False
        # 1: premium for 5% prevent plant buyup
        self.prevplant = False
        # 1: quality loss
        self.ql = False
        # 1: use trend-adjusted yields
        self.ta = False
        # 1: yield adjustment (60%)
        self.ya = False
        # 1: yield cup
        self.yc = False
        # 1: allow replacement of past year yield data (2012) by an alternative yield.
        self.ye = False
        # Rate yield (RMA rate yield)
        self.rateyield = None
        # Adjusted yield (RMA adjusted yield)
        self.adjyield = None
        # user-specified RMA approved yield
        self.appryield = None

        # External data
        # -------------
        # values pulled from database via get_crop_ins_data
        # attribute values set via setattr in compute_premiums
        self.ayp_base_rate = None
        self.arp_base_rate = None
        self.arphpe_base_rate = None
        self.ecoyp_base_rate = None
        self.ecorp_base_rate = None
        self.ecorphpe_base_rate = None
        self.scoyp_base_rate = None
        self.scorp_base_rate = None
        self.scorphpe_base_rate = None
        self.subsidy_ay = None
        self.subsidy_ar = None
        self.subsidy_ey = None
        self.subsidy_er = None
        self.subsidy_s = None

        self.draw = None
        self.enterprise_discount_factor = None
        self.enterprise_residual_factor_r = None
        self.enterprise_residual_factor_y = None
        self.option_rate = None
        self.rate_differential_factor = None

        self.refyield = None
        self.refrate = None
        self.exponent = None
        self.fixedrate = None

        self.subcounty_rate = None
        self.rate_method_id = None
        self.subsidy_ent = None

        # scalar variables
        # -------------------------
        # computed from appryield and mqty, stdqty, which are looked up based on
        # (revlook and # discountentr[cov65idx, sizeidx]).  Used in loss simulation
        self.adjmeanqty = None
        self.adjstdqty = None
        # Unit Structure Discount Factor
        # interpolated lookup used to set RP, RP-HPE premium rates
        self.disenter = None
        # effective cover: coverage level times ratio of appryield/rateyield
        # used in intepolation and several other calculations.
        self.sizeidx = None  # index based on acres
        # liability dollar amount based on appryield, aphprice, acres and cover.
        # dollar amount used in county options (SCO, ECO)
        self.aliab = None
        # log(aphprice) - pvol**2/2, used to compute harvest price in loss simulation.
        self.lnmean = None
        # multiplies in the hail/fire and prev plant rates in premium rate calc.
        self.multfactor = None

        # Arrays sized (8)
        self.effcov = None
        self.liab = None
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
        # Interpolated from enterprise_discount_factor_y,
        # used to compute basepremrate for YP
        self.efactor_y = None
        # Interpolated from enterprise_discount_factor_r,
        # used to compute basepremrate for RP, RP-HPE
        self.efactor_r = None
        # Current and Prior Year Rate Differential Factor
        self.ratediff_fac = None

        # Array sized (2, 8, 2) ('YP', 'RP/RP-HPE') by levels by (cur, prior)
        self.basepremrate = None

        # Premium arrays
        self.prem_ent = None
        self.prem_arc = None
        self.prem_sco = None
        self.prem_eco = None

    # -----------------------------
    # MAIN METHOD: COMPUTE PREMIUMS
    # -----------------------------
    def compute_prems(self, rateyield=180, adjyield=180, appryield=190, acres=100,
                      hailfire=False, prevplant=False, ql=False, ta=False, ya=False,
                      yc=False, ye=False, state=17, county=19, crop=41, croptype=16,
                      practice=3, projected_price=None, price_volatility_factor=None,
                      subcounty=None, expected_yield=None):
        """
        With farm-specific inputs, compute premiums for optional, basic and enterprise,
        units with RP, RP-HPE or YO protection for all coverage levels.
        Notes: (1) If specified, price_volatility_factor must be an integer.
          (2) If is_post_discovery is true, any provided values for
          price_volatility_factor and projected_price will simply be ignored.
        """
        self.store_user_settings(
            rateyield, adjyield, appryield, acres, hailfire,
            prevplant, ql, ta, ya, yc, ye, state, county,
            crop, croptype, practice, projected_price, price_volatility_factor,
            subcounty, expected_yield)

        # pass user-specified estimate of price_volatility_factor
        data = get_crop_ins_data(
            self.state, self.county, self.crop, self.croptype, self.practice,
            self.price_volatility_factor, self.subcounty)

        for name, val in data:
            setattr(self, name, val)

        if self.projected_price is None:
            self.prem_ent = self.prem_arc = self.prem_sco = self.prem_eco = None
        else:
            self.compute_prems_ent()
            if (self.arp_base_rate is None
                    or self.arphpe_base_rate is None
                    or self.ayp_base_rate is None):
                self.prem_arc = None
            else:
                self.compute_prems_arc()
            self.make_aliab()  # aliab used in SCO and ECO calculations
            if (self.scorp_base_rate is None
                    or self.scorphpe_base_rate is None
                    or self.scoyp_base_rate is None):
                self.prem_sco = None
            else:
                self.compute_prems_sco()
            if (self.ecorp_base_rate is None
                    or self.ecorphpe_base_rate is None
                    or self.ecoyp_base_rate is None):
                self.prem_eco = None
            else:
                self.compute_prems_eco()

        return (self.prem_ent, self.prem_arc, self.prem_sco, self.prem_eco,
                self.projected_price, self.expected_yield)

    # -------------------
    # ENTERPRISE PREMIUMS
    # -------------------
    def compute_prems_ent(self):
        """
        With farm-specific inputs, compute premiums for optional, basic and enterprise,
        units with RP, RP-HPE or YO protection for all coverage levels.
        """
        self.initialize_arrays()
        self.set_multfactor()
        self.set_effcov()
        self.set_factors()
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
        self.prem_ent = np.where(self.rate_differential_factor[:, 0].reshape(8, 1) < 0,
                                 np.inf, self.prem_ent)
        return self.prem_ent

    def set_multfactor(self):
        """
        Set Multiplicative Factor used to scale rates for hailfire, prevplant (p 16.)
        """
        # Hack based on current data to work around no pfrate for some counties/crops
        # TODO: revisit this if we ever decide to allow users to select these options.
        if len(self.option_rate) == 2:
            hfrate, pfrate = self.option_rate
        elif len(self.option_rate) == 1:
            pfrate = self.option_rate
            self.hailfire = False
        else:
            self.hailfire = self.prevplant = False

        self.multfactor = 1
        if self.hailfire:
            self.multfactor *= hfrate
        if self.prevplant:
            self.multfactor *= pfrate

    def set_effcov(self):
        """
        Set the effective coverage level
        Note: depends on appryield regardless of ta
        (Section 13, p. 44) (1.01 in TA/YE case)
        """
        self.effcov = (self.cover * self.appryield / self.adjyield).round(2)
        # print(f'{self.effcov=}')

    def clamp_maxcov(self, interpolated, base):
        """
        Step 3.05 in worksheet.  If the interpolated value exceeds the maximum of the
        corresponding set of base enterprise unit residual factors, we clamp it to that
        maxiumum
        """
        interpolated[:] = np.where(interpolated > np.max(base, axis=0),
                                   base, interpolated)

    def adjust_cy_ratediff_fac(self):
        covmax = self.cover[-1]
        ans1 = np.where(self.effcov > covmax, self.effcov, covmax) - covmax
        ans2 = np.where(ans1 / 0.15 > 1, 1, ans1 / 0.15).round(7)
        ans3 = (ans2 ** 3).round(7)
        ans4 = (1 + (ans3 * 0.05)).round(9)
        self.ratediff_fac[:, 0] = (self.ratediff_fac[:, 0] * ans4).round(9)
        # print(f'{ans4=}')
        # print(f'{self.ratediff_fac=}')

    def set_factors(self):
        """
        Interpolate current and previous rate differential, enterprise residual, and
        enterprise discount factors based on effective coverage. (section 15, p. 65-75)

        """
        varpairs = [
            (self.rate_differential_factor[:, 0], 9, 'rdf'),
            (self.rate_differential_factor[:, 1], 9, 'rdfp'),
            (self.enterprise_residual_factor_y[:, 0], 3, 'erfy'),
            (self.enterprise_residual_factor_y[:, 1], 3, 'erfyp'),
            (self.enterprise_residual_factor_r[:, 0], 3, 'erfr'),
            (self.enterprise_residual_factor_r[:, 1], 3, 'erfrp'),
            (self.enterprise_discount_factor[:, self.sizeidx], 4, 'edf'), ]
        rslts = self.interp(varpairs)
        self.ratediff_fac[:] = array(rslts[:2]).T  # 3.04
        self.efactor_y[:] = array(rslts[2:4]).T
        self.efactor_r[:] = array(rslts[4:6]).T    # 3.05
        if self.ql or self.yc or self.ye or self.ta:
            self.clamp_maxcov(self.efactor_y, self.enterprise_residual_factor_y)
            # print(f'before lim: {self.efactor_r=}')
            self.clamp_maxcov(self.efactor_r, self.enterprise_residual_factor_r)
            # print(f'after lim: {self.efactor_r=}')
        self.disenter[:] = rslts[6]                # 2.01
        if self.ql or self.yc or self.ye:
            # print('adjusting cy ratediff fac')
            self.adjust_cy_ratediff_fac()
        # print(f'{self.ratediff_fac=}')
        # print(f'{self.enterprise_residual_factor_r=}')
        # print(f'{self.efactor_y=}')
        # print(f'{self.efactor_r=}')
        # print(f'{self.disenter=}')

    def interp(self, varpairs):
        """
        Interpolate (or extrapolate up) by nearest cover values to effcov, then round.
        (section 15, p. 65-75)
        """
        cov, effcov = self.cover, self.effcov
        gap = cov[1] - cov[0]
        js, jps, jms = self.get_indices()
        rslts = []
        for var, ro, name in varpairs:
            if self.ql or self.ta or self.yc or self.ye:
                # handle general case with possible extrapolation
                vdiff = np.where(js < 7,
                                 var[jps] - var[js], var[js] - var[jms])
                rslt = (var[js] + vdiff * (effcov - cov[js]) / gap).round(ro)
                # modify result in special case which should never happen.
                rslt = np.where(effcov < cov[0], round(var[0], ro), rslt)
            else:
                rslt = var
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

    def make_rev_liab(self):
        """
        We assume the Guarantee Adjustment Factor and Insured Share Pct are 1
        Set the revised yield and the liability amount  (~ p. 1-4)
        (step 1.04/1.07)
        """
        self.liab = ((self.appryield * self.cover).round(1) *
                     self.projected_price * self.acres).round(0)
        # print(f'{self.liab=}')

    def set_base_rates(self):
        """
        Set and limit vector (current/prior) base rates from RMA data (~ p. 10-12)
        """
        yieldratio = np.minimum(np.maximum(
            (self.rateyield / self.refyield).round(2), 0.5), 1.5)  # 3.01
        ratemultiplier = (yieldratio ** self.exponent).round(8)    # 3.02
        term = ratemultiplier * self.refrate + self.fixedrate      # 3.03
        if self.subcounty_rate is not None:
            if self.rate_method_id == 'F':    # Not used in 2023 data
                self.baserate[:] = self.subcounty_rate
            elif self.rate_method_id == 'A':  # Commonly used in 2023 data
                self.baserate[:] = (self.subcounty_rate + term).round(8)
            elif self.rate_method_id == 'M':  # used by North Dakota
                self.baserate[:] = (self.subcounty_rate * term).round(8)
        else:
            self.baserate[:] = term.round(8)
        # print(f'{self.baserate=}')

    def get_curyr_base_prem_rate_effcov_gt_85(self, ix):
        """
        Additional steps in case effcov > cover[-1]
        array(2, 8-ix) rows: (y, r)
        """
        cybase = self.baserate[0]
        enterfactor = np.array([self.enterprise_residual_factor_y[-1, 0],
                                self.enterprise_residual_factor_r[-1, 0]]).reshape(2, 1)
        rate_differential_factor = self.rate_differential_factor[-1, 0]
        enterprise_discount_factor = self.enterprise_discount_factor[-1, self.sizeidx]

        efactor = np.array([self.efactor_y[-1, 0], self.efactor_r[-1, 0]]).reshape(2, 1)
        ratediff_fac = self.ratediff_fac[ix:, 0]

        unadjliab = ((self.cover[ix:] / self.effcov[ix:]).round(10) *
                     self.liab[ix:]).round()  # 3.06
        ans1 = (1 / cybase).round(8)  # start 3.07
        ans2 = (unadjliab / (cybase * self.liab[ix:])).round(8)  # array(8-ix)
        ans3 = (rate_differential_factor * enterfactor *
                enterprise_discount_factor * unadjliab).round(8)  # array(2, 8-ix)
        ans4 = (ans3 / self.liab[ix:]).round(8)  # array(2, 8-ix) y, r
        maxcovlvl_adjfactor = ans1 - ans2 + ans4  # array(2, 8-ix), y, r
        marginalrate_adjfactor = (
            maxcovlvl_adjfactor / (ratediff_fac * efactor *
                                   self.disenter[ix:])).round(8)  # array(2, 8-ix) y, r)
        curyr_base_prem_rate = (cybase * ratediff_fac * efactor *
                                np.where(marginalrate_adjfactor < 1,
                                         marginalrate_adjfactor, 1)).round(8)
        # print(f'{cybase=}')
        # print(f'{enterfactor=}')
        # print(f'{efactor=}')
        # print(f'{ratediff_fac=}')
        # print(f'{rate_differential_factor=}')
        # print(f'{enterprise_discount_factor=}')
        # print(f'{unadjliab=}')
        # print(f'{ans1=}')
        # print(f'{ans2=}')
        # print(f'{ans3=}')
        # print(f'{ans4=}')
        # print(f'{maxcovlvl_adjfactor=}')
        # print(f'{marginalrate_adjfactor=}')
        # print(f'{curyr_base_prem_rate=}')

        return curyr_base_prem_rate

    def set_base_prem_rates(self):
        """
        Set vector adjusted base premium rates (p. 13)
        """
        prod = (self.baserate * self.ratediff_fac *
                array((self.efactor_y, self.efactor_r)))

        exceeds = self.effcov > self.cover[-1]
        if (self.ql or self.ta or self.yc or self.ye) and np.any(exceeds):
            ix = np.argmax(exceeds)  # the smallest index for which effcov > 0.85
            prod[:, ix:, 0] = self.get_curyr_base_prem_rate_effcov_gt_85(ix)
        self.basepremrate = prod.round(8)
        # print(f'{self.basepremrate=}')
        # print(f'{self.basepremrate.shape=}')

    def limit_base_prem_rates(self):
        """
        Limit base premium rates min of cur and 1.2*prior (unpacking vectors)
        (bottom p. 15. 3.07 of worksheet)
        """
        bpr = self.basepremrate
        bpr[:, :, 0] = np.where(bpr[:, :, 0] > bpr[:, :, 1] * 1.2,
                                (bpr[:, :, 1] * 1.2).round(8), bpr[:, :, 0])

        bpr[:, :, 0] = np.where(bpr[:, :, 0] > 0.999,
                                np.ones(2).reshape(2, 1)*0.999, bpr[:, :, 0])
        # print(f'{bpr=}')

    def limit_baserate(self):
        """
        Limit base rate based on previous (unpacking vectors) (bottom p. 15, 3.08)
        """
        if self.baserate[0] > self.baserate[1] * 1.2:
            self.baserate[0] = round(self.baserate[1] * 1.2, 8)
        # print(f'in limit_baserate: {self.baserate=}')

    def set_qtys(self):
        """
        Compute mqty, stdqty and adjusted quantities (p. 7,8, bottom p. 15, p. 18,
        bottom p. 5.)
        """
        cov65idx = 3
        revenue_lookup_rate = round(min(self.baserate[0], 0.9999), 4)  # 3.08
        # print(f'{revenue_lookup_rate=}')
        rev_look_key = int(
           revenue_lookup_rate *
           10000 * self.enterprise_discount_factor[cov65idx, self.sizeidx] + 0.5)
        self.stdqty, self.mqty = get_combo_rev_std_mean(rev_look_key)
        self.adjmeanqty = round(self.appryield * self.mqty / 100, 8)
        self.adjstdqty = round(self.appryield * self.stdqty / 100, 8)
        # print(f'{self.adjmeanqty=}')
        # print(f'{self.adjstdqty=}')

    def simulate_losses(self):
        """
        Simulate losses for 500 (yield_draw, price_draw) pairs
        for cases (yp, rp, rphpe) (p. 19)
        """
        revcov = (self.effcov if self.ql or self.ta or self.yc or self.ye else
                  self.cover)
        self.lnmean = round(log(self.projected_price) -
                            ((self.price_volatility_factor/100) ** 2 / 2), 8)
        # print(f'{self.lnmean=}')
        simloss = zeros((500, 8, 3))
        yld = np.maximum(0, self.draw[:, 0] * self.adjstdqty + self.adjmeanqty)
        yld = np.repeat(yld[:, np.newaxis], 8, axis=1)
        simloss[:, :, 0] = np.maximum(0, self.appryield * revcov - yld)
        harprice = np.minimum(2 * self.projected_price,
                              exp(self.draw[:, 1] *
                                  (self.price_volatility_factor/100) + self.lnmean))
        harprice = np.repeat(harprice[:, np.newaxis], 8, axis=1)
        guarprice = np.maximum(harprice, self.projected_price)
        simloss[:, :, 1] = np.maximum(0, (self.appryield * guarprice * revcov -
                                          yld * harprice))
        simloss[:, :, 2] = np.maximum(0, (self.appryield * self.projected_price *
                                          revcov - yld * harprice))
        self.simloss = simloss.mean(0)
        self.simloss[:, 0] = (self.simloss[:, 0] /
                              (self.appryield * revcov)).round(8)
        self.simloss[:, 1:] = (self.simloss[:, 1:] /
                               (self.appryield * revcov *
                                self.projected_price).reshape(8, 1)).round(8)

    def set_rates(self):
        """
        Set the premium rates (p. 38)
        """
        self.rp_rateuse = (
            np.maximum(0.01 * self.basepremrate[1, :, 0],
                       self.simloss[:, 1] - self.simloss[:, 0])).round(8)
        self.rphpe_rateuse = (
            np.maximum(-0.5 * self.basepremrate[1, :, 0],
                       self.simloss[:, 2] - self.simloss[:, 0])).round(8)
        self.premrate[:] = (self.basepremrate[:, :, 0].T *
                            self.multfactor * self.disenter.reshape(8, 1))
        # print(f'{self.simloss[:, 1]=}')
        # print(f'{self.simloss[:, 0]=}')
        # print(f'{self.rp_rateuse=}')
        # print(f'{self.rphpe_rateuse=}')

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
        Apply the subsidy (section 17, p. 73)
        """
        self.prem_ent[:] -= (self.prem_ent[:] *
                             self.subsidy_ent[:].reshape(8, 1)).round(0)
        # print(f'{self.prem_ent}')
        self.prem_ent[:] = normal_round(self.prem_ent[:] / self.acres, 2)

    def initialize_arrays(self):
        """
        Initialize arrays for premium calculation
        """
        # Initialize current/prev arrays
        self.ratediff_fac = zeros((8, 2))
        self.efactor_y = zeros((8, 2))
        self.efactor_r = zeros((8, 2))
        self.disenter = zeros(8)
        self.baserate = zeros(2)

        # Initialize array to hold premiums
        self.prem_ent = zeros((8, 3))
        self.premrate = zeros((8, 2))  # Premium rates array (YP, RP/RPHPE)
        self.simloss = zeros((8, 3))   # Simulated losses array (YP, RP, RPHPE)

    # ------------
    # ARC PREMIUMS
    # ------------
    def compute_prems_arc(self):
        """
        Get values for each area type and level 70, 75, ..., 90
        Can't calculate ARC premiums for AL FL PA VA WV GA using 2023 data
        We return None in this case without raising error.
        """
        rates = np.array((self.arp_base_rate, self.arphpe_base_rate,
                          self.ayp_base_rate))
        subs = np.array((self.subsidy_ar, self.subsidy_ar, self.subsidy_ay))
        maxliab = round(self.expected_yield * self.projected_price * 1.2, 2)
        self.prem_arc = (maxliab * 100 * rates.T).round(0)
        self.prem_arc[:] -= (self.prem_arc * subs.T).round(0)
        self.prem_arc[:] = (self.prem_arc / 100 / 1.2).round(2)

    # ------------
    # SCO PREMIUMS
    # ------------
    def compute_prems_sco(self):
        """ Compute all SCO premiums """
        rates = array([self.scorp_base_rate, self.scorphpe_base_rate,
                       self.scoyp_base_rate])
        self.prem_sco = (self.aliab * rates.T *
                         (self.sco_top_level - self.cover).reshape(8, 1)).round(2)
        self.prem_sco[:] -= (self.subsidy_s * self.prem_sco).round(2)
        return self.prem_sco

    # ------------
    # ECO PREMIUMS
    # ------------
    def compute_prems_eco(self):
        """ Compute all ECO premiums """
        # Note: these don't match the UI tool because it applies the revenue subsidy
        # to all products, instead of using the higher yield subsidy for YP.
        rate = np.array([self.ecorp_base_rate, self.ecorphpe_base_rate,
                         self.ecoyp_base_rate])
        subsidy = np.array([self.subsidy_er, self.subsidy_er, self.subsidy_ey])
        self.prem_eco = ((self.eco_cover - self.sco_top_level).reshape(2, 1) *
                         self.aliab * rate.T * (1 - subsidy)).round(2)
        return self.prem_eco

    def make_aliab(self):
        arevyield = self.appryield if self.ta else self.rateyield
        self.aliab = arevyield * self.projected_price

    # -------------------
    # STORE USER SETTINGS
    # -------------------
    def store_user_settings(self, rateyield, adjyield, appryield, acres, hailfire,
                            prevplant, ql, ta, ya, yc, ye, state, county,
                            crop, croptype, practice, projected_price,
                            price_volatility_factor, subcounty, expected_yield):
        """
        Store settings provide by user when calling calc_premiums, and calculate
        some values derived from them.
        """
        self.rateyield = rateyield
        # override adjyield in cases no option or ya (adjyield not used)
        self.adjyield = (adjyield if self.ql or self.ta or self.yc or self.ye else
                         rateyield)
        self.appryield = appryield
        self.acres = acres
        self.hailfire = hailfire
        self.prevplant = prevplant
        self.ql = ql
        self.ta = ta
        self.ya = ya
        self.yc = yc
        self.ye = ye
        self.state = state
        self.county = county
        self.subcounty = subcounty
        self.crop = crop
        self.croptype = croptype
        self.practice = practice
        self.projected_price = projected_price
        self.price_volatility_factor = price_volatility_factor
        self.expected_yield = expected_yield

        # Set index based on acreage
        self.sizeidx = (0 if self.acres < 50 else 1 if self.acres < 100 else
                        2 if self.acres < 200 else 3 if self.acres < 400 else
                        4 if self.acres < 800 else 5)

    # ------------------------
    # Setup and Initialization
    # ------------------------
    def load_lookups(self):
        """
        Define dicts for lookups.  No longer needed for computation, but
        handy for reference.
        """
        self.crops = {Crop.CORN: 41, Crop.SOY: 81, Crop.WHEAT: 11}
        self.croptypes = {'Grain': 16, 'No Type Specified': 997, 'Winter': 11,
                          'Spring': 12}
        self.practices = {'Nfac (non-irrigated)': 53,
                          'Nfac (Irrigated)': 94,
                          'Fac (non-irrigated)': 43,
                          'Fac (Irrigated)': 95,
                          'Non-irrigated': 3,
                          'Irrigated': 2}
        self.states = {
            'IL': '17', 'AL': '01', 'AR': '05', 'FL': '12', 'GA': '13', 'IN': '18',
            'IA': '19', 'KS': '20', 'KY': '21', 'LA': '22', 'MD': '24', 'MI': '26',
            'MN': '27', 'MS': '28', 'MO': '29', 'NE': '31', 'NC': '37', 'ND': '38',
            'OH': '39', 'PA': '42', 'SC': '45', 'SD': '46', 'TN': '47', 'VA': '51',
            'WV': '54', 'WI': '55', 'OK': '40', 'TX': '48', 'WA': '53', 'MT': '30',
            'ID': '16', 'OR': '41', 'CO': '08'}


# ----------------
# Helper functions
# ----------------
def get_combo_rev_std_mean(lookupid):
    """
    Get the std_deviation_qty and mean_qty values from comborevenuefactor
    for the given lookupid
    """
    query = '''SELECT std_deviation_qty, mean_qty
               FROM public.ext_comborevenuefactor WHERE id=%s;'''
    record = get_postgres_row(query, lookupid)
    return record[0], record[1]


def get_crop_ins_data(state_id, county_code, commodity_id, commodity_type_id,
                      practice, price_volatility_factor, subcounty_id=None):
    """
    Get data needed to compute crop insurance from a postgreSQL user-defined function
    """
    names = ('''ayp_base_rate arp_base_rate arphpe_base_rate scoyp_base_rate
             scorp_base_rate scorphpe_base_rate ecoyp_base_rate ecorp_base_rate
             ecorphpe_base_rate subcounty_rate rate_method_id
             refyield refrate exponent fixedrate enterprise_residual_factor_r
             enterprise_residual_factor_y rate_differential_factor
             enterprise_discount_factor option_rate draw subsidy_ent subsidy_ay
             subsidy_ar subsidy_s subsidy_ey subsidy_er''').split()

    shapes = [(5,), (5,), (5,), (8,), (8,), (8,), (2,), (2,), (2,),
              (1,), (1,), (2,), (2,), (2,), (2,), (8, 2), (8, 2), (8, 2), (8, 6),
              (2,), (500, 2), (8,), (5,), (5,), (1,), (1,), (1,)]

    cmd = 'SELECT ' + ', '.join(names) + """
              FROM
              prem_data(%s, %s, %s, %s, %s, %s, %s)
              AS (ayp_base_rate real[], arp_base_rate real[],
                  arphpe_base_rate real[], scoyp_base_rate real[],
                  scorp_base_rate real[], scorphpe_base_rate real[],
                  ecoyp_base_rate real[], ecorp_base_rate real[],
                  ecorphpe_base_rate real[],
                  subcounty_rate real, rate_method_id char(1), refyield real[],
                  refrate real[], exponent real[], fixedrate real[],
                  enterprise_residual_factor_r real[],
                  enterprise_residual_factor_y real[],
                  rate_differential_factor real[],
                  enterprise_discount_factor real[],
                  option_rate real[], draw real[], subsidy_ent real[],
                  subsidy_ay real[], subsidy_ar real[], subsidy_s real,
                  subsidy_ey real, subsidy_er real);
          """
    record = call_postgres_func(cmd, state_id, county_code, commodity_id,
                                commodity_type_id, practice,
                                price_volatility_factor, subcounty_id)

    converted = (None if it is None else
                 it if name == 'rate_method_id' else
                 np.array(it).reshape(shp) if len(shp) == 2 else
                 np.array(it) if shp[0] > 1 else
                 float(it)
                 for it, shp, name in zip(record, shapes, names))

    return zip(names, converted)


def normal_round(num, places=0):
    return np.floor(num * 10**places + 0.5) / 10**places
