import numpy as np
from django.test import TestCase

from core.models.premium import Premium

# Note: We initially 'verified' against Excel, but there are too many errors there.
# All future verifications will be against RMA worksheets.
# Verification is critical for the farm-based premiums.  For other premiums, the
#     code is simple and well-tested.

# A question regarding the 85% coverage level for Champaign is pending a response.
#     No verification will be done on that County until a response is received.

# Abbreviations
# 'hailfire'      # hail and fire protection
# 'prevplant'     # prevent plant factor: std=0, Plus5%=1, Plus10%=2
# 'risk': 'BBB',  # {'None', 'AAA', 'BBB', 'CCC', 'DDD'}
# 'tause': 1,     # 1 to use trend-adjusted yields 0 else
# 'yieldexcl': 0, # 1 to use yield-exclusion 0 else
#
# Note: None is returned if premiums cannot be computed for a product
# Note: price_volatility_factor must be specified as an integer value.


class PremiumTestCase(TestCase):
    def setUp(self):
        self.premium = Premium()

    def test_800_acres_corn_in_champaign_ta_no_ye(self):
        # farm-based verified with RMA worksheets
        settings = {
            'rateyield': 220,
            'adjyield': 220,
            'appryield': 230,
            'acres': 800,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 1,
            'yieldexcl': 0,
            'state': 17,
            'county': 19,
            'crop': 41,
            'croptype': 16,
            'practice': 3,
            'projected_price': 5.91,
            'price_volatility_factor': 18,
            'expected_yield': 221.9,
        }
        prem = self.premium.compute_prems(**settings)
        expected = (
            np.array(
                [[0.84,  1.22,  1.75,  2.47,  3.59,  6.16, 13.43, 27.64],
                 [0.71,  0.88,  1.03,  1.23,  1.74,  2.88,  6.32, 13.42],
                 [0.69,  0.95,  1.29,  1.78,  2.44,  3.84,  7.54, 14.19]]).T,
            np.array(
                [[4.46,  8.14, 15.7,  29.09, 49.06],
                 [3.92,  6.32, 11.8,  20.73, 33.27],
                 [3.82,  5.22,  9.38, 13.28, 19.98]]).T,
            np.array(
                [[15.33, 15.31, 15.24, 14.46, 13.33, 11.63,  7.7,   1.68],
                 [10.77, 10.75, 10.69,  9.91,  9.02,  7.91,  5.1,   1.11],
                 [7.67,  7.65,  7.58,  6.82,  5.96,  5.08,  3.19,  0.73]]).T,
            np.array(
                [[13.66,  9.14,  5.55],
                 [37.17, 25.01, 16.08]])
        )

        for prm, exp in zip(prem[:4], expected):
            self.assertTrue(np.allclose(prm, exp))

    def test_800_acres_corn_in_champaign_ye_no_ta(self):
        # farm-based verified with RMA worksheets
        settings = {
            'rateyield': 220,
            'adjyield': 220,
            'appryield': 230,
            'acres': 800,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 0,
            'yieldexcl': 1,
            'state': 17,
            'county': 19,
            'crop': 41,
            'croptype': 16,
            'practice': 3,
            'projected_price': 5.91,
            'price_volatility_factor': 18,
            'expected_yield': 221.9,
        }
        prem = self.premium.compute_prems(**settings)
        expected = (
            np.array(
                [[0.84,  1.22,  1.75,  2.47,  3.59,  6.16, 13.43, 27.65],
                 [0.71,  0.88,  1.03,  1.23,  1.74,  2.88,  6.32, 13.43],
                 [0.69,  0.95,  1.29,  1.78,  2.44,  3.84,  7.54, 14.2]]).T,
            np.array(
                [[4.46,  8.14, 15.7,  29.09, 49.06],
                 [3.92,  6.32, 11.8,  20.73, 33.27],
                 [3.82,  5.22,  9.38, 13.28, 19.98]]).T,
            np.array(
                [[14.66, 14.64, 14.58, 13.83, 12.75, 11.12,  7.36,  1.61],
                 [10.3,  10.28, 10.22,  9.48,  8.63,  7.57,  4.88,  1.06],
                 [7.34,  7.32,  7.25,  6.53,  5.7,   4.86,  3.05,  0.7]]).T,
            np.array(
                [[13.06,  8.74,  5.31],
                 [35.55, 23.93, 15.38]])
        )

        for prm, exp in zip(prem[:4], expected):
            self.assertTrue(np.allclose(prm, exp))

    def test_800_acres_corn_in_champaign_ta_ya(self):
        # farm-based verified with RMA worksheets
        settings = {
            'rateyield': 220,
            'adjyield': 220,
            'appryield': 230,
            'acres': 800,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 1,
            'yieldexcl': 1,
            'state': 17,
            'county': 19,
            'crop': 41,
            'croptype': 16,
            'practice': 3,
            'projected_price': 5.91,
            'price_volatility_factor': 18,
            'expected_yield': 221.9,
        }
        prem = self.premium.compute_prems(**settings)
        expected = (
            np.array(
                [[0.84,  1.22,  1.75,  2.47,  3.59,  6.16, 13.43, 27.65],
                 [0.71,  0.88,  1.03,  1.23,  1.74,  2.88,  6.32, 13.43],
                 [0.69,  0.95,  1.29,  1.78,  2.44,  3.84,  7.54, 14.2]]).T,
            np.array(
                [[4.46,  8.14, 15.7,  29.09, 49.06],
                 [3.92,  6.32, 11.8,  20.73, 33.27],
                 [3.82,  5.22,  9.38, 13.28, 19.98]]).T,
            np.array(
                [[15.33, 15.31, 15.24, 14.46, 13.33, 11.63,  7.7,   1.68],
                 [10.77, 10.75, 10.69,  9.91,  9.02,  7.91,  5.1,   1.11],
                 [7.67,  7.65,  7.58,  6.82,  5.96,  5.08,  3.19,  0.73]]).T,
            np.array(
                [[13.66,  9.14,  5.55],
                 [37.17, 25.01, 16.08]])
        )

        for prm, exp in zip(prem[:4], expected):
            self.assertTrue(np.allclose(prm, exp))

    def test_800_acres_corn_in_champaign_no_ta_no_ye(self):
        # farm-based verified with RMA worksheets
        settings = {
            'rateyield': 220,
            'adjyield': 220,
            'appryield': 220,
            'acres': 800,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 0,
            'yieldexcl': 0,
            'state': 17,
            'county': 19,
            'crop': 41,
            'croptype': 16,
            'practice': 3,
            'projected_price': 5.91,
            'price_volatility_factor': 18,
            'expected_yield': 221.9,
        }
        prem = self.premium.compute_prems(**settings)
        expected = (
            np.array(
                [[0.74,  1.01,  1.42,  1.99,  2.85,  4.8,   9.97, 21.25],
                 [0.66,  0.79,  0.95,  1.07,  1.38,  2.29,  4.6,  10.04],
                 [0.62,  0.8,   1.07,  1.47,  2.,    3.15,  5.97, 11.76]]).T,
            np.array(
                [[4.46,  8.14, 15.7,  29.09, 49.06],
                 [3.92,  6.32, 11.8,  20.73, 33.27],
                 [3.82,  5.22,  9.38, 13.28, 19.98]]).T,
            np.array(
                [[14.66, 14.64, 14.58, 13.83, 12.75, 11.12,  7.36,  1.61],
                 [10.3,  10.28, 10.22,  9.48,  8.63,  7.57,  4.88,  1.06],
                 [7.34,  7.32,  7.25,  6.53,  5.7,   4.86,  3.05,  0.7]]).T,
            np.array(
                [[13.06,  8.74,  5.31],
                 [35.55, 23.93, 15.38]])
        )

        for prm, exp in zip(prem[:4], expected):
            self.assertTrue(np.allclose(prm, exp))

    def test_3000_acres_champaign_full_soy(self):
        settings = {
            'rateyield': 58,
            'adjyield': 58,
            'appryield': 60,
            'acres': 3000,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 1,
            'yieldexcl': 0,
            'state': 17,
            'county': 19,
            'crop': 81,
            'croptype': 997,
            'practice': 53,
            'projected_price': 13.76,
            'price_volatility_factor': 13,
            'expected_yield': 68,
        }
        prem = self.premium.compute_prems(**settings)
        expected = (
            np.array(
                [[0.16, 0.24, 0.37, 0.58, 0.97, 1.9 , 3.90, 8.2],
                 [0.14, 0.17, 0.23, 0.31, 0.47, 0.83, 1.58, 3.08],
                 [0.15, 0.2 , 0.27, 0.39, 0.55, 0.93, 1.78, 3.45]]).T,
            np.array(
                [[1.58,  2.78,  4.93, 11.27, 22.42],
                 [1.,    1.81,  4.42,  9.73, 18.6],
                 [1.12,  1.31,  2.03,  3.41,  7.2]]).T,
            np.array(
                [[5.23, 5.23, 5.24, 5.23, 5.11, 4.6 , 3.15, 0.7],
                 [4.46, 4.46, 4.47, 4.46, 4.35, 3.86, 2.59, 0.56],
                 [1.76, 1.76, 1.76, 1.76, 1.73, 1.5 , 0.99, 0.24]]).T,
            np.array(
                [[05.99,  4.78,  2.20],
                 [17.34, 13.64,  7.48]]))

        for prm, exp in zip(prem[:4], expected):
            self.assertTrue(np.allclose(prm, exp))

    def test_300_acres_wheat_champaign(self):
        # NOTE: The county premiums are not available for this case.
        settings = {
            'rateyield': 39,
            'adjyield': 39,
            'appryield': 40.5,
            'acres': 300,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 1,
            'yieldexcl': 0,
            'state': 17,
            'county': 19,
            'crop': 11,
            'croptype': 11,
            'practice': 3,
            'projected_price': 8.45,
            'price_volatility_factor': 31,
            'expected_yield': 70.7,
        }
        prem = self.premium.compute_prems(**settings)
        expected = (
            np.array(
                [[3.81,  4.67,  5.61,  6.97,  8.79, 12.65, 21.72, 38.48],
                 [3.18,  3.9,   4.67,  5.84,  7.44, 10.79, 18.66, 33.21],
                 [2.67,  3.23,  3.87,  4.86,  6.25,  9.17, 16.01, 28.67]]).T,
            None,  # No ARC data for county/crop
            np.array(
                [[13.05, 12.4,  11.49, 10.27,  8.61,  6.47,  3.85,  0.69],
                 [10.74, 10.18,  9.43,  8.4,   7.,    5.2,   3.07,  0.55],
                 [5.52,  5.35,  5.07,  4.67,  4.06,  3.18,  1.96,  0.37]]).T,
            np.array(
                [[4.73,  3.76,  2.3],
                 [11.25,  8.93,  5.71]]))

        for prm, exp in zip(prem[:4], expected):
            if exp is None:
                self.assertIsNone(prm)
            else:
                self.assertTrue(np.allclose(prm, exp))

    def test_100_acres_madison_corn(self):
        settings = {
            'rateyield': 154,
            'adjyield': 154,
            'appryield': 164,
            'acres': 100,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 1,
            'yieldexcl': 0,
            'state': 17,
            'county': 119,
            'crop': 41,
            'croptype': 16,
            'practice': 3,
            'projected_price': 5.91,
            'price_volatility_factor': 18,
            'expected_yield': 191.9,
        }
        prem = self.premium.compute_prems(**settings)
        expected = (
            np.array(
                [[1.92,  2.6 ,  3.42,  4.55,  6.47,  10.02, 18.47, 35.58],
                 [1.34,  1.71,  2.16,  2.77,  3.87,  6.11, 11.45, 22.5],
                 [1.58,  2.07,  2.66,  3.42,  4.59,  6.87, 12.34, 22.92]]).T,
            np.array(
                [[15.67, 21.63, 28.17, 41.12, 58.75],
                 [13.25, 17.25, 21.28, 29.56, 40.84],
                 [13.34, 15.02, 18.78, 21.53, 28.51]]).T,
            np.array(
                [[15.2 , 14.83, 14.61, 14.09, 12.96, 10.86,  7.12,  1.4],
                 [10.23,  9.87,  9.82,  9.58,  8.92,  7.56,  5.  ,  0.99],
                 [8.  ,  7.64,  7.51,  7.23,  6.65,  5.62,  3.79,  0.77]]).T,
            np.array(
                [[10.54,  7.47,  5.2],
                 [27.25, 19.85, 13.83]]))

        for prm, exp in zip(prem[:4], expected):
            self.assertTrue(np.allclose(prm, exp))

    def test_3000_acres_full_soybeans_madison(self):
        settings = {
            'rateyield': 47,
            'adjyield': 47,
            'appryield': 50,
            'acres': 3000,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 1,
            'yieldexcl': 0,
            'state': 17,
            'county': 119,
            'crop': 81,
            'croptype': 997,
            'practice': 53,
            'projected_price': 13.76,
            'price_volatility_factor': 13,
            'expected_yield': 56,
        }
        prem = self.premium.compute_prems(**settings)
        expected = (
            np.array(
                [[0.91,  1.26,  1.79,  2.51,  3.44,  5.59, 10.42, 19.82],
                 [0.69,  0.88,  1.2 ,  1.67,  2.29,  3.70,  6.97, 13.42],
                 [0.79,  1.05,  1.41,  1.91,  2.58,  4.18,  7.76, 14.52]]).T,
            np.array(
                [[1.2,   2.43,  4.86, 11.36, 22.22],
                 [0.79,  1.42,  3.4,   8.06, 16.09],
                 [0.88,  1.52,  2.67,  4.75,  9.97]]).T,
            np.array(
                [[5.36, 5.35, 5.35, 5.34, 5.13, 4.58, 3.27, 0.7],
                 [3.81, 3.81, 3.82, 3.81, 3.69, 3.33, 2.4 , 0.52],
                 [2.58, 2.58, 2.57, 2.57, 2.47, 2.22, 1.61, 0.37]]).T,
            np.array(
                [[05.71,  4.23,  2.81],
                 [15.63, 11.76,  8.14]]))

        for prm, exp in zip(prem[:4], expected):
            self.assertTrue(np.allclose(prm, exp))

    def test_300_acres_wheat_madison(self):
        settings = {
            'rateyield': 58,
            'adjyield': 58,
            'appryield': 61,
            'acres': 300,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 1,
            'yieldexcl': 0,
            'state': 17,
            'county': 119,
            'crop': 11,
            'croptype': 11,
            'practice': 3,
            'projected_price': 8.45,
            'price_volatility_factor': 31,
            'expected_yield': 70.1,
        }
        prem = self.premium.compute_prems(**settings)
        expected = (
            np.array(
                [[4.32,  5.35,  6.48,  7.93, 10.27, 14.84, 25.44, 44.91],
                 [3.59,  4.44,  5.36,  6.52,  8.49, 12.35, 21.27, 37.53],
                 [2.8 ,  3.36,  3.99,  4.9,  6.52,  9.57, 16.65, 29.67]]).T,
            np.array(
                [[19.48, 27.13, 33.22, 44.82, 57.62],
                 [17.44, 23.81, 28.6,  37.68, 47.3],
                 [7.78,  9.32, 12.21, 14.45, 18.81]]).T,
            np.array(
                [[18.17, 17.19, 15.74, 14.25, 12.15,  9.27,  5.6 ,  1.02],
                 [15.14, 14.26, 12.92, 11.62,  9.86,  7.49,  4.46,  0.8],
                 [6.68,  6.25,  5.63,  5.29,  4.75,  3.87,  2.49,  0.49]]).T,
            np.array(
                [[07.11,  5.57,  3.11],
                 [17.12, 13.39,  7.97]]))

        for prm, exp in zip(prem[:4], expected):
            self.assertTrue(np.allclose(prm, exp))

    def test_300_acres_fac_soy_madison(self):
        settings = {
            'rateyield': 47,
            'adjyield': 47,
            'appryield': 49,
            'acres': 300,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 1,
            'yieldexcl': 0,
            'state': 17,
            'county': 119,
            'crop': 81,
            'croptype': 997,
            'practice': 43,
            'projected_price': 13.76,
            'price_volatility_factor': 13,
            'expected_yield': 56,
        }
        p = Premium()
        prem = p.compute_prems(**settings)
        expected = (
            np.array(
                [[1.7 ,  2.26,  3.11,  4.04,  5.16,  7.57, 13.34, 25.1],
                 [1.28,  1.66,  2.26,  2.93,  3.72,  5.47,  9.66, 18.4],
                 [1.47,  1.9 ,  2.53,  3.23,  4.11,  6.01, 10.56, 19.68]]).T,
            np.array(
                [[1.2,   2.43,  4.86, 11.36, 22.22],
                 [0.79,  1.42,  3.4,   8.06, 16.09],
                 [0.88,  1.52,  2.67,  4.75,  9.97]]).T,
            np.array(
                [[5.25, 5.25, 5.25, 5.23, 5.03, 4.49, 3.2 , 0.68],
                 [3.74, 3.74, 3.74, 3.73, 3.62, 3.26, 2.36, 0.51],
                 [2.52, 2.52, 2.52, 2.52, 2.43, 2.18, 1.58, 0.36]]).T,
            np.array(
                [[05.6 ,  4.15,  2.76],
                 [15.32, 11.53,  7.98]]))

        for prm, exp in zip(prem[:4], expected):
            self.assertTrue(np.allclose(prm, exp))

    def test_100_acres_corn_st_charles_mo_risk_BBB_ta_noye(self):
        # farm-based verified with RMA worksheets
        settings = {
            'rateyield': 147,
            'adjyield': 147,
            'appryield': 156,
            'acres': 100,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 1,
            'yieldexcl': 0,
            'state': 29,
            'county': 183,
            'crop': 41,
            'croptype': 16,
            'practice': 3,
            'subcounty': 'BBB',
            'projected_price': 5.91,
            'price_volatility_factor': 18,
            'expected_yield': 164.2,
        }
        prem = self.premium.compute_prems(**settings)
        expected = (
            np.array(
                [[8.41, 10.31, 12.79, 15.44, 18.61, 26.19, 43.3, 73.6],
                 [6.62,  8.14, 10.2 , 12.4 , 14.99, 21.27, 35.39, 60.3],
                 [6.91,  8.47, 10.45, 12.47, 14.94, 21.08, 34.99, 59.29]]).T,
            np.array(
                [[13.28, 20.83, 28.08, 41.22, 59.4],
                 [9.63, 15.03, 19.69, 28.07, 40.38],
                 [11.1,  15.04, 20.52, 24.54, 33.52]]).T,
            np.array(
                [[18.83, 18.31, 17.46, 15.99, 13.65, 11.02,  7.13,  1.39],
                 [12.65, 12.28, 11.71, 10.67,  8.98,  7.26,  4.75,  0.93],
                 [12.45, 11.97, 11.22, 10.02,  8.17,  6.44,  4.2 ,  0.84]]).T,
            np.array(
                [[10.35,  7.25,  5.37],
                 [26.48, 19.07, 13.92]]))

        for prm, exp in zip(prem[:4], expected):
            self.assertTrue(np.allclose(prm, exp))

    def test_100_acres_madison_corn_NO_TA(self):
        settings = {
            'rateyield': 154,
            'adjyield': 154,
            'appryield': 154,
            'acres': 100,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 0,
            'yieldexcl': 0,
            'state': 17,
            'county': 119,
            'crop': 41,
            'croptype': 16,
            'practice': 3,
            'projected_price': 5.91,
            'price_volatility_factor': 18,
            'expected_yield': 191.9,
        }
        prem = self.premium.compute_prems(**settings)
        expected = (
            np.array(
                [[1.62,  2.11,  2.76,  3.61,  4.8 ,  7.49, 13.97, 27.06],
                 [1.2 ,  1.42,  1.8 ,  2.27,  2.9 ,  4.48,  8.51, 16.78],
                 [1.37,  1.72,  2.18,  2.79,  3.57,  5.31,  9.58, 18.09]]).T,
            np.array(
                [[15.67, 21.63, 28.17, 41.12, 58.75],
                 [13.25, 17.25, 21.28, 29.56, 40.84],
                 [13.34, 15.02, 18.78, 21.53, 28.51]]).T,
            np.array(
                [[14.28, 13.92, 13.72, 13.23, 12.17, 10.2 ,  6.69,  1.32],
                 [09.61,  9.27,  9.23,  9.  ,  8.38,  7.1 ,  4.69,  0.93],
                 [07.51,  7.18,  7.06,  6.79,  6.25,  5.28,  3.56,  0.72]]).T,
            np.array(
                [[09.9 ,  7.02,  4.88],
                 [25.59, 18.64, 12.98]]))

        for prm, exp in zip(prem[:4], expected):
            self.assertTrue(np.allclose(prm, exp))

    def test_300_acres_adams_cty_colorado_irrigated_wheat(self):
        settings = {
            'rateyield': 65,
            'adjyield': 65,
            'appryield': 65,
            'acres': 300,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 0,
            'yieldexcl': 0,
            'state': 8,
            'county': 1,
            'crop': 11,
            'croptype': 11,
            'practice': 2,
            'projected_price': 8.77,
            'price_volatility_factor': 30,
            'expected_yield': 65.1,
        }
        prem = self.premium.compute_prems(**settings)
        expected = (
            np.array(
                [[4.03,  5.2 ,  6.51,  8.01, 10.22, 15.1 , 26.3 , 47.4],
                 [3.56,  4.51,  5.53,  6.71,  8.54, 12.66, 22.09, 39.86],
                 [2.9 ,  3.61,  4.41,  5.32,  6.78, 10.19, 17.98, 32.9]]).T,
            None,
            np.array(
                [[16.39, 16.01, 15.3 , 14.11, 12.2 ,  9.4 ,  5.71,  1.06],
                 [14.06, 13.68, 13.01, 11.93, 10.2 ,  7.75,  4.64,  0.84],
                 [04.2 ,  4.2 ,  4.2 ,  4.1 ,  3.78,  3.07,  2.03,  0.42]]).T,

            np.array(
                [[07.5 ,  5.89,  2.90],
                 [18.6 , 14.48,  7.84]]))

        for prm, exp in zip(prem[:4], expected):
            if prm is None:
                self.assertTrue(exp is None)
            else:
                self.assertTrue(np.allclose(prm, exp))

    def test_800_acres_madison_cty_corn_ta_ye(self):
        # farm-based verified with RMA worksheets
        settings = {
            'rateyield': 190,
            'adjyield': 190,
            'appryield': 200,
            'acres': 800,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 1,
            'yieldexcl': 1,
            'state': 17,
            'county': 119,
            'crop': 41,
            'croptype': 16,
            'practice': 3,
            'projected_price': 5.91,
            'price_volatility_factor': 18,
            'expected_yield': 191.9,
        }
        prem = self.premium.compute_prems(**settings)
        expected = (
            np.array(
                [[1.89, 2.48, 3.23, 4.29, 6.18, 9.74, 18.3, 34.93],
                 [1.4, 1.63, 2.02, 2.55, 3.5, 5.55, 10.61, 20.45],
                 [1.58, 1.97, 2.49, 3.18, 4.27, 6.4, 11.53, 21.06]]).T,
            np.array(
                [[15.67, 21.63, 28.17, 41.12, 58.75],
                 [13.25, 17.25, 21.28, 29.56, 40.84],
                 [13.34, 15.02, 18.78, 21.53, 28.51]]).T,
            np.array(
                [[18.54, 18.08, 17.81, 17.18, 15.81, 13.24,  8.69,  1.71],
                 [12.48, 12.04, 11.98, 11.69, 10.87,  9.22,  6.1,   1.21],
                 [9.75,  9.32,  9.16,  8.82,  8.12,  6.85,  4.62,  0.93]]).T,
            np.array(
                [[12.85,  9.11,  6.34],
                 [33.23, 24.2,  16.86]])
        )

        for prm, exp in zip(prem[:4], expected):
            if prm is None:
                self.assertTrue(exp is None)
            else:
                self.assertTrue(np.allclose(prm, exp))

    def test_800_acres_madison_cty_corn_nota_noye(self):
        # farm-based verified with RMA worksheets
        settings = {
            'rateyield': 190,
            'adjyield': 190,
            'appryield': 200,
            'acres': 800,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 0,
            'yieldexcl': 0,
            'state': 17,
            'county': 119,
            'crop': 41,
            'croptype': 16,
            'practice': 3,
            'projected_price': 5.91,
            'price_volatility_factor': 18,
            'expected_yield': 191.9,
        }
        prem = self.premium.compute_prems(**settings)
        expected = (
            np.array(
                [[1.7,   2.22,  2.89,  3.78,  5.06,  7.99, 15.16, 29.86],
                 [1.35,  1.56,  1.86,  2.32,  2.95,  4.5,   8.66, 17.39],
                 [1.48,  1.82,  2.26,  2.86,  3.66,  5.46,  9.86, 18.66]]).T,
            np.array(
                [[15.67, 21.63, 28.17, 41.12, 58.75],
                 [13.25, 17.25, 21.28, 29.56, 40.84],
                 [13.34, 15.02, 18.78, 21.53, 28.51]]).T,
            np.array(
                [[17.62, 17.18, 16.92, 16.32, 15.02, 12.58,  8.25,  1.63],
                 [11.86, 11.44, 11.38, 11.1,  10.33,  8.76,  5.79,  1.15],
                 [9.27,  8.86,  8.7,   8.38,  7.71,  6.51,  4.39,  0.89]]).T,
            np.array(
                [[12.21,  8.66,  6.02],
                 [31.57, 22.99, 16.02]]
                )
        )

        for prm, exp in zip(prem[:4], expected):
            if prm is None:
                self.assertTrue(exp is None)
            else:
                self.assertTrue(np.allclose(prm, exp))

    def test_800_acres_madison_cty_corn_nota_ye(self):
        # farm-based verified with RMA worksheets
        settings = {
            'rateyield': 190,
            'adjyield': 190,
            'appryield': 200,
            'acres': 800,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 0,
            'yieldexcl': 1,
            'state': 17,
            'county': 119,
            'crop': 41,
            'croptype': 16,
            'practice': 3,
            'projected_price': 5.91,
            'price_volatility_factor': 18,
            'expected_yield': 191.9,
        }
        prem = self.premium.compute_prems(**settings)
        expected = (
            np.array(
                [[1.89,  2.48,  3.23,  4.29,  6.18,  9.74, 18.3,  34.93],
                 [1.4,   1.63,  2.02,  2.55,  3.5,   5.55, 10.61, 20.45],
                 [1.58,  1.97,  2.49,  3.18,  4.27,  6.4,  11.53, 21.06]]).T,
            np.array(
                [[15.67, 21.63, 28.17, 41.12, 58.75],
                 [13.25, 17.25, 21.28, 29.56, 40.84],
                 [13.34, 15.02, 18.78, 21.53, 28.51]]).T,
            np.array(
                [[17.62, 17.18, 16.92, 16.32, 15.02, 12.58,  8.25,  1.63],
                 [11.86, 11.44, 11.38, 11.1,  10.33,  8.76,  5.79,  1.15],
                 [9.27,  8.86,  8.7,   8.38,  7.71,  6.51,  4.39,  0.89]]).T,
            np.array(
                [[12.21,  8.66,  6.02],
                 [31.57, 22.99, 16.02]]
                )
        )

        for prm, exp in zip(prem[:4], expected):
            if prm is None:
                self.assertTrue(exp is None)
            else:
                self.assertTrue(np.allclose(prm, exp))

    def test_800_acres_madison_cty_corn_ta_noye(self):
        # farm-based verified with RMA worksheets
        settings = {
            'rateyield': 190,
            'adjyield': 190,
            'appryield': 200,
            'acres': 800,
            'hailfire': 0,
            'prevplant': 0,
            'tause': 1,
            'yieldexcl': 0,
            'state': 17,
            'county': 119,
            'crop': 41,
            'croptype': 16,
            'practice': 3,
            'projected_price': 5.91,
            'price_volatility_factor': 18,
            'expected_yield': 191.9,
        }
        prem = self.premium.compute_prems(**settings)
        expected = (
            np.array(
                [[1.89,  2.48,  3.23,  4.29,  6.18,  9.74, 18.3,  34.91],
                 [1.4,   1.63,  2.02,  2.55,  3.5,   5.55, 10.61, 20.43],
                 [1.58,  1.97,  2.49,  3.18,  4.27,  6.4,  11.53, 21.04]]).T,
            np.array(
                [[15.67, 21.63, 28.17, 41.12, 58.75],
                 [13.25, 17.25, 21.28, 29.56, 40.84],
                 [13.34, 15.02, 18.78, 21.53, 28.51]]).T,
            np.array(
                [[18.54, 18.08, 17.81, 17.18, 15.81, 13.24,  8.69,  1.71],
                 [12.48, 12.04, 11.98, 11.69, 10.87,  9.22,  6.1,   1.21],
                 [9.75,  9.32,  9.16,  8.82,  8.12,  6.85,  4.62,  0.93]]).T,
            np.array(
                [[12.85,  9.11,  6.34],
                 [33.23, 24.2,  16.86]]
                )
        )

        # print(prem[0].T)
        # print(prem[1].T)
        # print(prem[2].T)
        # print(prem[3])
        for prm, exp in zip(prem[:4], expected):
            if prm is None:
                self.assertTrue(exp is None)
            else:
                self.assertTrue(np.allclose(prm, exp))
