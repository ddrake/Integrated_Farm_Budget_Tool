from numpy import zeros, array, log, exp
import numpy as np

from core.models.util import Crop, call_postgres_func, get_postgres_row

np.set_printoptions(precision=6)
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
        # The county practice corresponding to the practice
        self.cpractice = None
        # Protection factor (aka payment factor) for ARC
        self.prot_factor = None
        # The user-provided or RMA computed avg harvest price for Feb
        self.projected_price = None
        # The user-provided or RMA computed volatility
        self.price_volatility_factor = None
        # Either None or a 3-letter high risk code like 'AAA'
        self.subcounty = None
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
        # Rate yield (RMA rate yield)
        self.rateyield = None
        # Adjusted yield (RMA adjusted yield)
        self.adjyield = None
        # user-specified Trend-Adjusted APY yield (RMA 'approved yield')
        self.tayield = None
        self.tayield_adj = None  # possibly modified tayield

        # External data
        # -------------
        # values pulled from database via get_crop_ins_data[_pre_pvol]
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
        # Needed to compute ARC premiums (missing for some counties)
        self.expected_yield = None

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
        # computed from revyield and mqty, stdqty, which are looked up based on
        # (revlook and # discountentr[cov65idx, sizeidx]).  Used in loss simulation
        self.adjmeanqty = None
        self.adjstdqty = None
        # interpolated lookup used to set RP, RP-HPE premium rates
        self.disenter = None
        # effective cover: coverage level times ratio of tayield/rateyield
        # used in intepolation and several other calculations.
        self.effcov = None
        self.sizeidx = None  # index based on acres
        # dollar amount based on revyield, aphprice, acres and cover.
        self.liab = None
        # dollar amount used in county options (SCO, ECO)
        self.aliab = None
        # revised yield: tayield if tause else adjyield
        self.revyield = None
        # log(aphprice) - pvol**2/2, used to compute harvest price in loss simulation.
        self.lnmean = None
        # multiplies in the hail/fire and prev plant rates in premium rate calc.
        self.multfactor = None
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
        # Interpolated from enterprise_discount_factor_r,
        # used to compute basepremrate for YP
        self.efactor_y = None
        # Interpolated from enterprise_discount_factor_r,
        # used to compute basepremrate for RP, RP-HPE
        self.efactor_r = None
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
    def compute_prems(self, rateyield=180, adjyield=180, tayield=190, acres=100,
                      hailfire=0, prevplant=0, tause=1, yieldexcl=0,
                      state=17, county=19, crop=41, croptype=16, practice=3,
                      prot_factor=1, projected_price=None,
                      price_volatility_factor=None, subcounty=None):
        """
        With farm-specific inputs, compute premiums for optional, basic and enterprise,
        units with RP, RP-HPE or YO protection for all coverage levels.
        Note: If specified, price_volatility_factor must be an integer.
        """
        self.store_user_settings(
            rateyield, adjyield, tayield, acres, hailfire, prevplant, tause,
            yieldexcl, state, county, crop, croptype, practice, prot_factor,
            projected_price, price_volatility_factor, subcounty)

        data = None
        if self.price_volatility_factor is None or self.projected_price is None:
            # assume these values are present in the RMA data
            data = get_crop_ins_data(
                self.state, self.county, self.crop, self.croptype,
                self.practice, self.subcounty)
        else:
            # pass user-specified estimate of price_volatility_factor
            data = get_crop_ins_data_pre_pvol(
                self.state, self.county, self.crop, self.croptype, self.practice,
                self.price_volatility_factor, self.subcounty)

        for name, val in data:
            setattr(self, name, val)
            # print(f'self.{name} = {val}')

        if self.projected_price is None:
            # print("Projected Price is missing.",
            #       "Can't compute any premiums.")
            self.prem_ent = self.prem_arc = self.prem_sco = self.prem_eco = None
        else:
            self.compute_prems_ent()
            if self.expected_yield is None:
                # print("Expected Yield is not available for county/crop",
                #       "Can't compute Area premiums")
                self.prem_arc = None
            else:
                self.compute_prems_arc()
            self.make_aliab()  # aliab used in SCO and ECO calculations
            if (self.scorp_base_rate is None
                    or self.scorphpe_base_rate is None
                    or self.scoyp_base_rate is None):
                # print("SCO Base rates are not available for county/crop",
                #       "Can't compute SCO premiums",
                #       "Try specifying the county practice (cpractice)")
                self.prem_sco = None
            else:
                self.compute_prems_sco()
            if (self.ecorp_base_rate is None
                    or self.ecorphpe_base_rate is None
                    or self.ecoyp_base_rate is None):
                # print("ECO Base rates are not available for county/crop",
                #       "Can't compute ECO premiums",
                #       "Try specifying the county practice (cpractice)")
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
        # The orig code sets the premiums to zero in cases where it can't compute them.
        # I think a better value is np.inf since zero implies 'cost free'.
        self.prem_ent = np.where(self.rate_differential_factor[:, 0].reshape(8, 1) < 0,
                                 np.inf, self.prem_ent)
        return self.prem_ent

    def set_multfactor(self):
        """
        Set Multiplicative Factor used to scale rates for hailfire, prevplant (p 16.)
        """
        hfrate, pfrate = self.option_rate
        self.multfactor = 1
        if self.hailfire > 0:
            self.multfactor *= hfrate
        if self.prevplant == 1:
            self.multfactor *= pfrate

    def set_effcov(self):
        """
        Set the effective coverage level (Note: depends on tayield regardless of tause)
        (Section 13, p. 44)
        """
        self.effcov = (0.0001 + self.cover * self.tayield_adj / self.adjyield).round(2)

    def set_factors(self):
        """
        Interpolate current and previous rate differential, enterprise residual, and
        enterprise discount factors based on effective coverage. (section 15, p. 65-75)
        """
        varpairs = [
            (self.rate_differential_factor[:, 0], 9),
            (self.rate_differential_factor[:, 1], 9),
            (self.enterprise_residual_factor_y[:, 0], 3),
            (self.enterprise_residual_factor_y[:, 1], 3),
            (self.enterprise_residual_factor_r[:, 0], 3),
            (self.enterprise_residual_factor_r[:, 1], 3),
            (self.enterprise_discount_factor[:, self.sizeidx], 4), ]
        rslts = self.interp(varpairs)
        self.ratediff_fac[:] = array(rslts[:2]).T
        self.efactor_y[:] = array(rslts[2:4]).T
        self.efactor_r[:] = array(rslts[4:6]).T
        self.disenter[:] = rslts[6]

    def interp(self, varpairs):
        """
        Interpolate (or extrapolate up) by nearest cover values to effcov, then round.
        (section 15, p. 65-75)
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
                np.logical_and(effcov > 0.75, self.rate_differential_factor[6, 0] == 0),
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
        Adjust factors for YE (vectorized) (section 19, p. 74)
        """
        jjhigh = 5 if self.rate_differential_factor[6, 0] == 0 else 7
        yeadj = np.where(np.logical_and(self.effcov > 0.85, self.yieldexcl == 1),
                         (self.effcov - 0.85) / 0.15, np.zeros_like(self.effcov))
        yeadj = np.where(self.effcov > 0.85,
                         1 + (np.minimum(1, yeadj) ** 3).round(7) * 0.05, yeadj)
        self.ratediff_fac[:, 0] = np.where(self.effcov > 0.85,
                                           self.ratediff_fac[:, 0] * yeadj,
                                           self.ratediff_fac[:, 0])
        self.efactor_y = np.where(self.effcov.reshape(8, 1) > 0.85,
                                  np.minimum(
                                    self.efactor_y,
                                    self.enterprise_residual_factor_y[jjhigh, :]),
                                  self.efactor_y)

    def make_rev_liab(self):
        """
        Set the revised yield, the revised cover and the liability (~ p. 1-4)
        """
        # Per page 1, I think this should be:
        #   self.revyield = max(self.tayield, self.adjyield)
        self.revyield = self.tayield_adj if self.tause else self.adjyield
        self.liab = ((self.revyield * self.cover + 0.001).round(1) *
                     self.projected_price * self.acres).round(0)

    def set_base_rates(self):
        """
        Set and limit vector (current/prior) base rates from RMA data (~ p. 10-12)
        """
        self.baserate = np.minimum(np.maximum(
            (self.rateyield / self.refyield).round(2), 0.5), 1.5)
        self.baserate = (self.baserate ** self.exponent).round(8)
        term = self.baserate * self.refrate + self.fixedrate
        if self.subcounty_rate is not None:
            if self.rate_method_id == 'F':    # Not used in 2023 data
                self.baserate[:] = self.subcounty_rate
            elif self.rate_method_id == 'A':  # Commonly used in 2023 data
                self.baserate[:] = (self.subcounty_rate + term).round(8)
            elif self.rate_method_id == 'M':  # used by North Dakota
                self.baserate[:] = (self.subcounty_rate * term).round(8)
        else:
            self.baserate[:] = term.round(8)

    def set_base_prem_rates(self):
        """
        Set vector adjusted base premium rates (p. 13)
        """
        prod = self.baserate * self.ratediff_fac
        self.basepremrate = array((prod * self.efactor_y,
                                   prod * self.efactor_r)).round(8)

    def limit_base_prem_rates(self):
        """
        Limit base premium rates min of cur and 1.2*prior (unpacking vectors)
        (bottom p. 15)
        """
        bpr = self.basepremrate
        bpr[:, :, 0] = np.where(bpr[:, :, 0] > bpr[:, :, 1] * 1.2,
                                (bpr[:, :, 1] * 1.2).round(8), bpr[:, :, 0])

        # Note: I cannot find this step in the handbook.  It always felt wrong.
        bpr[:, :, 0] = np.where(bpr[:, :, 0] > 0.99,
                                zeros(2).reshape(2, 1), bpr[:, :, 0])

    def limit_baserate(self):
        """
        Limit base rate based on previous (unpacking vectors) (bottom p. 15)
        """
        if self.baserate[0] > self.baserate[1] * 1.2:
            self.baserate[0] = round(self.baserate[1] * 1.2, 8)

    def set_qtys(self):
        """
        Compute mqty, stdqty and adjusted quantities (p. 7,8, bottom p. 15, p. 18,
        bottom p. 5.)
        """
        cov65idx = 3
        revenue_lookup_rate = round(min(self.baserate[0], 0.9999), 4)
        rev_look_key = int(
           revenue_lookup_rate *
           10000 * self.enterprise_discount_factor[cov65idx, self.sizeidx] + 0.5)
        self.stdqty, self.mqty = get_combo_rev_std_mean(rev_look_key)
        self.adjmeanqty = round(self.revyield * self.mqty / 100, 8)
        self.adjstdqty = round(self.revyield * self.stdqty / 100, 8)

    def simulate_losses(self):
        """
        Simulate losses for 500 (yield_draw, price_draw) pairs
        for cases (yp, rp, rphpe) (p. 19)
        """
        revcov = self.effcov if self.tause else self.cover
        self.lnmean = round(log(self.projected_price) -
                            ((self.price_volatility_factor/100) ** 2 / 2), 8)
        simloss = zeros((500, 8, 3))
        yld = np.maximum(0, self.draw[:, 0] * self.adjstdqty + self.adjmeanqty)
        yld = np.repeat(yld[:, np.newaxis], 8, axis=1)
        simloss[:, :, 0] = np.maximum(0, self.revyield * revcov - yld)
        harprice = np.minimum(2 * self.projected_price,
                              exp(self.draw[:, 1] *
                                  (self.price_volatility_factor/100) + self.lnmean))
        harprice = np.repeat(harprice[:, np.newaxis], 8, axis=1)
        guarprice = np.maximum(harprice, self.projected_price)
        simloss[:, :, 1] = np.maximum(0, (self.revyield * guarprice * revcov -
                                          yld * harprice))
        simloss[:, :, 2] = np.maximum(0, (self.revyield * self.projected_price *
                                          revcov - yld * harprice))
        self.simloss = simloss.mean(0)
        self.simloss[:, 0] = (self.simloss[:, 0] /
                              (self.revyield * revcov)).round(8)
        self.simloss[:, 1] = (self.simloss[:, 1] /
                              (self.revyield * revcov *
                               self.projected_price)).round(8)
        self.simloss[:, 2] = (self.simloss[:, 2] /
                              (self.revyield * revcov *
                               self.projected_price)).round(8)

    def set_rates(self):
        """
        Set the premium rates (p. 38)
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
        Apply the subsidy (section 17, p. 73)
        """
        self.prem_ent[:] -= (self.prem_ent[:] *
                             self.subsidy_ent[:].reshape(8, 1)).round(0)
        self.prem_ent[:] = (self.prem_ent[:] / self.acres).round(2)

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
        self.prem_arc[:] = (self.prem_arc / 100 *
                            self.prot_factor / 1.2).round(2)

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
        arevyield = self.tayield if self.tause else self.rateyield
        self.aliab = arevyield * self.projected_price

    # -------------------
    # STORE USER SETTINGS
    # -------------------
    def store_user_settings(self, rateyield, adjyield, tayield, acres, hailfire,
                            prevplant, tause, yieldexcl, state, county,
                            crop, croptype, practice, prot_factor, projected_price,
                            price_volatility_factor, subcounty):
        """
        Store settings provide by user when calling calc_premiums, and calculate
        some values derived from them.
        """
        self.rateyield = rateyield
        self.adjyield = adjyield
        self.tayield = tayield
        self.acres = acres
        self.hailfire = hailfire
        self.prevplant = prevplant
        self.tause = tause
        self.yieldexcl = yieldexcl
        self.state = state
        self.county = county
        self.subcounty = subcounty
        self.crop = crop
        self.croptype = croptype
        self.practice = practice
        self.prot_factor = prot_factor
        self.projected_price = projected_price
        self.price_volatility_factor = price_volatility_factor

        self.tayield_adj = max(self.tayield,  self.rateyield)

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


def get_crop_ins_data_pre_pvol(state_id, county_code, commodity_id, commodity_type_id,
                               practice, price_volatility_factor, subcounty_id=None):
    """
    Get data needed to compute crop insurance from a postgreSQL user-defined function
    """
    names = ('''ayp_base_rate arp_base_rate arphpe_base_rate scoyp_base_rate
             scorp_base_rate scorphpe_base_rate ecoyp_base_rate ecorp_base_rate
             ecorphpe_base_rate expected_yield subcounty_rate rate_method_id
             refyield refrate exponent fixedrate enterprise_residual_factor_r
             enterprise_residual_factor_y rate_differential_factor
             enterprise_discount_factor option_rate draw subsidy_ent subsidy_ay
             subsidy_ar subsidy_s subsidy_ey subsidy_er''').split()

    shapes = [(5,), (5,), (5,), (8,), (8,), (8,), (2,), (2,), (2,), (1,),
              (1,), (1,), (2,), (2,), (2,), (2,), (8, 2), (8, 2), (8, 2), (8, 6),
              (2,), (500, 2), (8,), (5,), (5,), (1,), (1,), (1,)]

    cmd = 'SELECT ' + ', '.join(names) + """
              FROM
              public.prem_data_pre_pvol(%s, %s, %s, %s, %s, %s, %s)
              AS (ayp_base_rate real[], arp_base_rate real[],
                  arphpe_base_rate real[], scoyp_base_rate real[],
                  scorp_base_rate real[], scorphpe_base_rate real[],
                  ecoyp_base_rate real[], ecorp_base_rate real[],
                  ecorphpe_base_rate real[], expected_yield real,
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


def get_crop_ins_data(state_id, county_code, commodity_id, commodity_type_id,
                      practice, subcounty_id=None):
    """
    Get data needed to compute crop insurance from a postgreSQL user-defined function
    """
    names = ('''ayp_base_rate arp_base_rate arphpe_base_rate scoyp_base_rate
             scorp_base_rate scorphpe_base_rate ecoyp_base_rate ecorp_base_rate
             ecorphpe_base_rate expected_yield projected_price
             price_volatility_factor subcounty_rate rate_method_id refyield refrate
             exponent fixedrate enterprise_residual_factor_r
             enterprise_residual_factor_y rate_differential_factor
             enterprise_discount_factor option_rate draw subsidy_ent subsidy_ay
             subsidy_ar subsidy_s subsidy_ey subsidy_er''').split()

    shapes = [(5,), (5,), (5,), (8,), (8,), (8,), (2,), (2,), (2,), (1,),
              (1,), (1,), (1,), (1,), (2,), (2,), (2,), (2,), (8, 2), (8, 2), (8, 2),
              (8, 6), (2,), (500, 2), (8,), (5,), (5,), (1,), (1,), (1,)]

    cmd = """ SELECT """ + ', '.join(names) + """
              FROM
              public.prem_data(%s, %s, %s, %s, %s, %s)
              AS (ayp_base_rate real[], arp_base_rate real[],
                  arphpe_base_rate real[], scoyp_base_rate real[],
                  scorp_base_rate real[], scorphpe_base_rate real[],
                  ecoyp_base_rate real[], ecorp_base_rate real[],
                  ecorphpe_base_rate real[], expected_yield real,
                  projected_price real, price_volatility_factor smallint,
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
                                commodity_type_id, practice, subcounty_id)

    converted = (None if it is None else
                 it if name == 'rate_method_id' else
                 int(it) if name == 'price_volatility_factor' else
                 np.array(it).reshape(shp) if len(shp) == 2 else
                 np.array(it) if shp[0] > 1 else
                 float(it)
                 for it, shp, name in zip(record, shapes, names))

    return zip(names, converted)
