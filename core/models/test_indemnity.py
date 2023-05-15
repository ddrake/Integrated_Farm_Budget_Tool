import numpy as np
from django.test import TestCase

from core.models.indemnity import Indemnity


class IndemnityTestCase(TestCase):
    def setUp(self):
        # Somthing like Grandview corn
        self.indemnity = Indemnity(
            tayield=164, projected_price=5.91, harvest_futures_price=5.3475,
            cty_expected_yield=191.9, farm_expected_yield=210, prot_factor=1,
            farm_yield_premium_to_county=0.0929550)

    def test_with_default_values(self):
        indem = self.indemnity.compute_indems()
        expected = (
            np.array(
                [[0.,  0.,  0.,  0.,  0.,  0., 0., 0.],
                 [0.,  0.,  0.,  0.,  0.,  0., 0., 0.],
                 [0.,  0.,  0.,  0.,  0.,  0., 0., 0.]]).T,
            np.array(
                [[0.,  0., 0., 0., 0.],
                 [0.,  0., 0., 0., 0.],
                 [0.,  0., 0., 0., 0.]]).T,
            np.array(
                [[0., 0., 0., 0., 0., 0., 0., 0.],
                 [0., 0., 0., 0., 0., 0., 0., 0.],
                 [0., 0., 0., 0., 0., 0., 0., 0.]]).T,
            np.array(
                [[0., 0., 0.],
                 [42.69 , 42.69, 0.]]))

        for idm, exp in zip(indem, expected):
            self.assertTrue(np.allclose(idm, exp))

    def test_with_pf_0_7(self):
        indem = self.indemnity.compute_indems(pf=0.7)
        expected = (
            np.array(
                [[0.,  0.,  0.,  0.,  0.,  0., 0., 37.77],
                 [0.,  0.,  0.,  0.,  0.,  0., 0., 37.77],
                 [0.,  0.,  0.,  0.,  0.,  0., 0., 0.]]).T,
            np.array(
                [[143.58,  230.47, 303.35, 365.35, 418.74],
                 [143.58,  230.47, 303.35, 365.35, 418.74],
                 [0.,  0., 0., 0., 0.]]).T,
            np.array(
                [[218.89, 218.89, 218.89, 203.54, 155.08, 106.62, 58.15, 9.69],
                 [218.89, 218.89, 218.89, 203.54, 155.08, 106.62, 58.15, 9.69],
                 [0., 0., 0., 0., 0., 0., 0., 0.]]).T,
            np.array(
                [[38.77, 38.77, 0.],
                 [87.23, 87.23, 0.]]))

        for idm, exp in zip(indem, expected):
            self.assertTrue(np.allclose(idm, exp))

    def test_with_yf_0_75(self):
        indem = self.indemnity.compute_indems(yf=0.75)
        expected = (
            np.array(
                [[0.,  0.,  0.,  0.,  0.,  0., 0., 0.],
                 [0.,  0.,  0.,  0.,  0.,  0., 0., 0.],
                 [0.,  0.,  0.,  0.,  0.,  0., 0., 0.]]).T,
            np.array(
                [[44.79, 140.34, 220.49, 288.67, 347.38],
                 [44.79, 140.34, 220.49, 288.67, 347.38],
                 [00.,     0.,    89.75, 167.69, 234.80]]).T,
            np.array(
                [[174.98, 174.98, 174.98, 174.98, 155.08, 106.62, 58.15, 9.69],
                 [174.98, 174.98, 174.98, 174.98, 155.08, 106.62, 58.15, 9.69],
                 [105.71, 105.71, 105.71, 105.71, 105.71, 105.71, 58.15, 9.69]]).T,
            np.array(
                [[38.77, 38.77, 38.77],
                 [87.23, 87.23, 87.23]]))

        for idm, exp in zip(indem, expected):
            self.assertTrue(np.allclose(idm, exp))

    def test_with_pf_2_5(self):
        indem = self.indemnity.compute_indems(pf=2.5)
        expected = (
            np.array(
                [[0, 0, 0, 0, 0, 0, 0, 0],
                 [0, 0, 0, 0, 0, 0, 0, 0],
                 [0, 0, 0, 0, 0, 0, 0, 0]]).T,
            np.array(
                [[0, 0, 0, 0, 0],
                 [0, 0, 0, 0, 0],
                 [0, 0, 0, 0, 0]]).T,
            np.array(
                [[0, 0, 0, 0, 0, 0, 0, 0],
                 [0, 0, 0, 0, 0, 0, 0, 0],
                 [0, 0, 0, 0, 0, 0, 0, 0]]).T,
            np.array(
                [[0, 0, 0],
                 [0, 0, 0]]))

        for idm, exp in zip(indem, expected):
            self.assertTrue(np.allclose(idm, exp))

    def test_with_pf_2_5_yf_0_7(self):
        indem = self.indemnity.compute_indems(pf=2.5, yf=0.7)
        expected = (
            np.array(
                [[0, 0, 0, 0, 0, 0, 0, 0],
                 [0, 0, 0, 0, 0, 0, 0, 0],
                 [0, 0, 0, 0, 0, 0, 0, 0]]).T,
            np.array(
                [[0, 195.49, 362.65, 504.86, 627.32],
                 [0, 0, 0, 0, 0],
                 [0, 97.75, 181.32, 252.43, 313.66]]).T,
            np.array(
                [[308.46, 308.46, 308.46, 308.46, 308.46, 213.23, 116.31, 19.38],
                 [0, 0, 0, 0, 0, 0, 0, 0],
                 [154.23, 154.23, 154.23, 154.23, 154.23, 106.62, 58.15, 9.69]]).T,
            np.array(
                [[77.54, 0, 38.77],
                 [174.46, 0, 87.23]]))

        for idm, exp in zip(indem, expected):
            self.assertTrue(np.allclose(idm, exp))

    def test_with_pf_1_5_yf_0_6(self):
        indem = self.indemnity.compute_indems(pf=1.5, yf=0.6)
        expected = (
            np.array(
                [[0, 0, 0, 0, 0, 0, 41.71, 107.48],
                 [0, 0, 0, 0, 0, 0, 0, 0],
                 [0, 0, 0, 0, 0, 0, 30.73, 79.19]]).T,
            np.array(
                [[293.8, 403.05, 494.68, 572.64, 639.76],
                 [0, 0, 0, 58.64, 133.33],
                 [216.47, 296.96, 364.48, 421.91, 471.37]]).T,
            np.array(
                [[341.04, 341.04, 341.04, 276.25, 210.48, 144.7, 78.93, 13.15],
                 [43.27, 43.27, 43.27, 43.27, 43.27, 43.27, 43.27, 9.69],
                 [251.28, 251.28, 251.28, 203.54, 155.08, 106.62, 58.15, 9.69]]).T,
            np.array(
                [[52.62, 38.77, 38.77],
                 [118.39, 87.23, 87.23]]))

        for idm, exp in zip(indem, expected):
            self.assertTrue(np.allclose(idm, exp))

    def test_with_pf_0_6_yf_0_6(self):
        indem = self.indemnity.compute_indems(pf=0.6, yf=0.6)

        expected = (
            np.array(
                [[80.35, 128.81, 177.27, 225.73, 274.2, 322.66, 371.12, 419.58],
                 [80.35, 128.81, 177.27, 225.73, 274.2, 322.66, 371.12, 419.58],
                 [0, 0, 0, 0, 0, 0, 30.73, 79.19]]).T,
            np.array(
                [[815.39, 843.35, 866.8, 886.75, 903.93],
                 [815.39, 843.35, 866.8, 886.75, 903.93],
                 [216.47, 296.96, 364.48, 421.91, 471.37]]).T,
            np.array(
                [[348.93, 300.46, 252, 203.54, 155.08, 106.62, 58.15, 9.69],
                 [348.93, 300.46, 252, 203.54, 155.08, 106.62, 58.15, 9.69],
                 [251.28, 251.28, 251.28, 203.54, 155.08, 106.62, 58.15, 9.69]]).T,
            np.array(
                [[38.77, 38.77, 38.77],
                 [87.23, 87.23, 87.23]]))

        for idm, exp in zip(indem, expected):
            self.assertTrue(np.allclose(idm, exp))
