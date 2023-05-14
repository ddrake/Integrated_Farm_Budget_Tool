import numpy as np
from django.test import TestCase

from core.models.indemnity import Indemnity


class IndemnityTestCase(TestCase):
    def setUp(self):
        # Somthing like Grandview corn
        self.indemnity = Indemnity(164, 5.91, 5.3475, 191.9, 210, 1, 0.0929550)

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
        # TODO: seems wrong...
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
        # TODO: seems wrong...
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
            print(idm.T)
            self.assertTrue(np.allclose(idm, exp))
