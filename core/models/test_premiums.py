import numpy as np
import pytest
from core.models.premium import Premium

TOL = .01
# Note: 'expected' arrays marked 'verified' have been checked against excel
# Note: When verifying against the Excel file, note that the APH Yield and
#       Rate Yield are reversed on the premiums tab.
# Abbreviations
# 'hailfire'      # hail and fire protection
# 'prevplant'     # prevent plant factor: std=0, Plus5%=1, Plus10%=2
# 'risk': 'BBB',  # {'None', 'AAA', 'BBB', 'CCC', 'DDD'}
# 'tause': 1,     # 1 to use trend-adjusted yields 0 else
# 'yieldexcl': 0, # 1 to use yield-exclusion 0 else
#
# Note: None is returned if premiums cannot be computed for a product
# Note: arc premiums use the 120% protection factor to match an Excel column.
# Note: If price_volatility_factor is specified, it must be an integer value.


def test_with_default_values():
    # Premiums for Default settings; prot_factor 1.2 to match UI (verified)
    # except for ECO YP (UI uses incorrect subsidy)
    p = Premium()
    prem = p.compute_prems(prot_factor=1.2)
    print(prem)

    expected = (
        np.array(
            [[0.9 ,  1.28,  1.79,  2.62,  3.79,  6.38, 12.72, 26.97],
             [0.71,  0.87,  1.01,  1.36,  1.91,  3.12,  6.39, 14.13],
             [0.73,  0.99,  1.37,  1.96,  2.69,  4.22,  7.9 , 15.34]]).T,
        np.array(
            [[05.35,  9.77, 18.84, 34.91, 58.87],
             [04.71,  7.58, 14.16, 24.88, 39.92],
             [04.58,  6.26, 11.26, 15.93, 23.98]]).T,
        np.array(
            [[12.66, 12.65, 12.59, 11.94, 11.01,  9.61,  6.36,  1.39],
             [08.9 ,  8.88,  8.83,  8.19,  7.45,  6.54,  4.21,  0.92],
             [06.34,  6.32,  6.26,  5.64,  4.92,  4.2 ,  2.64,  0.61]]).T,
        np.array(
            [[11.28,  7.55,  4.59],
             [30.7 , 20.66, 13.29]]))

    for prm, exp in zip(prem[:4], expected):
        assert np.all((prm - exp) == pytest.approx(0, TOL)), "values don't all match"


def test_3000_acres_corn_in_champaign():
    # Premiums for 3000 acres corn (verified)
    settings = {
        'rateyield': 180,
        'adjyield': 180,
        'tayield': 190,
        'acres': 3000,
        'hailfire': 0,
        'prevplant': 0,
        'tause': 1,
        'yieldexcl': 0,
        'state': 17,
        'county': 19,
        'crop': 41,
        'croptype': 16,
        'practice': 3,
        'prot_factor': 1.2
    }
    p = Premium()
    prem = p.compute_prems(**settings)
    expected = (
        np.array(
            [[0.83,  1.16,  1.62,  2.4 ,  3.5 ,  5.95, 11.99, 25.66],
             [0.67,  0.81,  0.94,  1.22,  1.74,  2.85,  5.87, 13.09],
             [0.68,  0.9 ,  1.23,  1.76,  2.42,  3.81,  7.15, 13.92]]).T,
        np.array(
            [[05.35,  9.77, 18.84, 34.91, 58.87],
             [04.71,  7.58, 14.16, 24.88, 39.92],
             [04.58,  6.26, 11.26, 15.93, 23.98]]).T,
        np.array(
            [[12.66, 12.65, 12.59, 11.94, 11.01,  9.61,  6.36,  1.39],
             [08.9 ,  8.88,  8.83,  8.19,  7.45,  6.54,  4.21,  0.92],
             [06.34,  6.32,  6.26,  5.64,  4.92,  4.2 ,  2.64,  0.61]]).T,
        np.array(
            [[11.28,  7.55,  4.59],
             [30.7 , 20.66, 13.29]]))

    for prm, exp in zip(prem[:4], expected):
        assert np.all((prm - exp) == pytest.approx(0, TOL)), "values don't all match"


def test_3000_acres_champaign_full_soy():
    # Premiums for 3000 acres full season soybeans in Champaign (verified)
    settings = {
        'rateyield': 58,
        'adjyield': 58,
        'tayield': 60,
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
        'prot_factor': 1.2
    }
    p = Premium()
    prem = p.compute_prems(**settings)
    print(prem)
    expected = (
        np.array(
            [[0.16, 0.24, 0.37, 0.58, 0.97, 1.9 , 3.9 , 8.23],
             [0.14, 0.17, 0.23, 0.31, 0.47, 0.83, 1.58, 3.10],
             [0.15, 0.2 , 0.27, 0.39, 0.55, 0.93, 1.78, 3.45]]).T,
        np.array(
            [[01.89,  3.33,  5.91, 13.52, 26.91],
             [01.2 ,  2.17,  5.31, 11.68, 22.32],
             [01.34,  1.57,  2.43,  4.09,  8.64]]).T,
        np.array(
            [[5.23, 5.23, 5.24, 5.23, 5.11, 4.6 , 3.15, 0.70],
             [4.46, 4.46, 4.47, 4.46, 4.35, 3.86, 2.59, 0.56],
             [1.76, 1.76, 1.76, 1.76, 1.73, 1.5 , 0.99, 0.24]]).T,
        np.array(
            [[05.99,  4.78,  2.20],
             [17.34, 13.64,  7.48]]))

    for prm, exp in zip(prem[:4], expected):
        assert np.all((prm - exp) == pytest.approx(0, TOL)), "values don't all match"


def test_300_acres_wheat_champaign():
    # Premiums for 300 acres wheat in Champaign (verified)
    # NOTE: The ARP premiums are not available for this case.
    settings = {
        'rateyield': 39,
        'adjyield': 39,
        'tayield': 38.5,
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
        'prot_factor': 1.2
    }
    p = Premium()
    prem = p.compute_prems(**settings)
    expected = (
        np.array(
            [[3.52,  4.32,  5.2 ,  6.2 ,  7.64, 11.12, 19.17, 34.56],
             [2.93,  3.61,  4.33,  5.16,  6.43,  9.44, 16.41, 29.77],
             [2.48,  3.  ,  3.59,  4.27,  5.36,  7.97, 14.01, 25.62]]).T,
        None,  # No ARC data for county/crop
        np.array(
            [[12.4 , 11.79, 10.93,  9.77,  8.19,  6.15,  3.66,  0.65],
             [10.21,  9.68,  8.97,  7.99,  6.65,  4.95,  2.92,  0.52],
             [05.25,  5.08,  4.82,  4.44,  3.86,  3.02,  1.87,  0.35]]).T,
        np.array(
            [[04.5 ,  3.57,  2.19],
             [10.69,  8.49,  5.43]]))

    for prm, exp in zip(prem[:4], expected):
        if prm is None:
            assert exp is None, "Values don't all match"
        else:
            assert np.all((prm - exp) ==
                          pytest.approx(0, TOL)), "values don't all match"


def test_100_acres_madison_corn():
    # Premiums for Madison County corn (verified)
    settings = {
        'rateyield': 154,
        'adjyield': 154,
        'tayield': 164,
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
        'prot_factor': 1.2
    }
    p = Premium()
    prem = p.compute_prems(**settings)
    expected = (
        np.array(
            [[1.92,  2.6 ,  3.42,  4.55,  6.47, 10.02, 18.47, 36.25],
             [1.34,  1.71,  2.16,  2.77,  3.87,  6.11, 11.45, 23.17],
             [1.58,  2.07,  2.66,  3.42,  4.59,  6.87, 12.34, 22.92]]).T,
        np.array(
            [[18.8 , 25.96, 33.8 , 49.35, 70.50],
             [15.9 , 20.7 , 25.54, 35.47, 49.01],
             [16.01, 18.02, 22.54, 25.84, 34.21]]).T,
        np.array(
            [[15.2 , 14.83, 14.61, 14.09, 12.96, 10.86,  7.12,  1.40],
             [10.23,  9.87,  9.82,  9.58,  8.92,  7.56,  5.  ,  0.99],
             [08.  ,  7.64,  7.51,  7.23,  6.65,  5.62,  3.79,  0.77]]).T,
        np.array(
            [[10.54,  7.47,  5.20],
             [27.25, 19.85, 13.83]]))

    for prm, exp in zip(prem[:4], expected):
        assert np.all((prm - exp) == pytest.approx(0, TOL)), "values don't all match"


def test_3000_acres_full_soybeans_madison():
    # Premiums for 3000 acres full season soybeans in Madison (verified)
    settings = {
        'rateyield': 47,
        'adjyield': 47,
        'tayield': 50,
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
        'prot_factor': 1.2
    }
    p = Premium()
    prem = p.compute_prems(**settings)
    expected = (
        np.array(
            [[0.91,  1.26,  1.79,  2.51,  3.44,  5.59, 10.42, 19.98],
             [0.69,  0.88,  1.2 ,  1.67,  2.29,  3.7 ,  6.97, 13.58],
             [0.79,  1.05,  1.41,  1.91,  2.58,  4.18,  7.76, 14.52]]).T,
        np.array(
            [[01.44,  2.91,  5.83, 13.63, 26.67],
             [00.95,  1.71,  4.08,  9.67, 19.31],
             [01.06,  1.82,  3.2 ,  5.7 , 11.96]]).T,
        np.array(
            [[5.36, 5.35, 5.35, 5.34, 5.13, 4.58, 3.27, 0.70],
             [3.81, 3.81, 3.82, 3.81, 3.69, 3.33, 2.4 , 0.52],
             [2.58, 2.58, 2.57, 2.57, 2.47, 2.22, 1.61, 0.37]]).T,
        np.array(
            [[05.71,  4.23,  2.81],
             [15.63, 11.76,  8.14]]))

    for prm, exp in zip(prem[:4], expected):
        assert np.all((prm - exp) == pytest.approx(0, TOL)), "values don't all match"


def test_300_acres_wheat_madison():
    # Premiums for 300 acres wheat in Madison (verified)
    settings = {
        'rateyield': 58,
        'adjyield': 58,
        'tayield': 61,
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
        'prot_factor': 1.2
    }
    p = Premium()
    prem = p.compute_prems(**settings)
    expected = (
        np.array(
            [[4.32,  5.35,  6.48,  7.95, 10.27, 14.84, 25.44, 45.48],
             [3.59,  4.44,  5.36,  6.54,  8.49, 12.35, 21.27, 38.09],
             [2.8 ,  3.36,  3.99,  4.91,  6.52,  9.57, 16.65, 29.73]]).T,
        np.array(
            [[23.37, 32.56, 39.86, 53.79, 69.14],
             [20.93, 28.57, 34.32, 45.21, 56.76],
             [09.33, 11.19, 14.65, 17.34, 22.57]]).T,
        np.array(
            [[18.17, 17.19, 15.74, 14.25, 12.15,  9.27,  5.6 ,  1.02],
             [15.14, 14.26, 12.92, 11.62,  9.86,  7.49,  4.46,  0.80],
             [06.68,  6.25,  5.63,  5.29,  4.75,  3.87,  2.49,  0.49]]).T,
        np.array(
            [[07.11,  5.57,  3.11],
             [17.12, 13.39,  7.97]]))

    for prm, exp in zip(prem[:4], expected):
        assert np.all((prm - exp) == pytest.approx(0, TOL)), "values don't all match"


def test_300_acres_fac_soy_madison():
    # Premiums for 300 acres Fac soybeans in Madison (verified)
    settings = {
        'rateyield': 47,
        'adjyield': 47,
        'tayield': 49,
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
        'prot_factor': 1.2
    }
    p = Premium()
    prem = p.compute_prems(**settings)
    expected = (
        np.array(
            [[1.7 ,  2.26,  3.11,  4.05,  5.16,  7.57, 13.34, 25.34],
             [1.28,  1.66,  2.26,  2.94,  3.72,  5.47,  9.66, 18.62],
             [1.47,  1.9 ,  2.53,  3.24,  4.11,  6.01, 10.56, 19.73]]).T,
        np.array(
            [[01.44,  2.91,  5.83, 13.63, 26.67],
             [00.95,  1.71,  4.08,  9.67, 19.31],
             [01.06,  1.82,  3.2 ,  5.7 , 11.96]]).T,
        np.array(
            [[5.25, 5.25, 5.25, 5.23, 5.03, 4.49, 3.2 , 0.68],
             [3.74, 3.74, 3.74, 3.73, 3.62, 3.26, 2.36, 0.51],
             [2.52, 2.52, 2.52, 2.52, 2.43, 2.18, 1.58, 0.36]]).T,
        np.array(
            [[05.6 ,  4.15,  2.76],
             [15.32, 11.53,  7.98]]))

    for prm, exp in zip(prem[:4], expected):
        assert np.all((prm - exp) == pytest.approx(0, TOL)), "values don't all match"


def test_100_acres_corn_st_charles_mo_risk_BBB():
    # Premiums for 100 acres corn in St. Charles, MO (verified)
    settings = {
        'rateyield': 147,
        'adjyield': 147,
        'tayield': 156,
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
        'prot_factor': 1.2,
        'subcounty': 'BBB'
    }
    p = Premium()
    prem = p.compute_prems(**settings)
    expected = (
        np.array(
            [[8.41, 10.31, 12.79, 15.44, 18.61, 26.19, 43.3 , 75.04],
             [6.62,  8.14, 10.2 , 12.4 , 14.99, 21.27, 35.39, 61.75],
             [6.91,  8.47, 10.45, 12.47, 14.94, 21.08, 34.99, 59.29]]).T,
        np.array(
            [[15.94, 25.  , 33.7 , 49.47, 71.28],
             [11.55, 18.03, 23.63, 33.68, 48.45],
             [13.32, 18.05, 24.63, 29.45, 40.23]]).T,
        np.array(
            [[18.83, 18.31, 17.46, 15.99, 13.65, 11.02,  7.13,  1.39],
             [12.65, 12.28, 11.71, 10.67,  8.98,  7.26,  4.75,  0.93],
             [12.45, 11.97, 11.22, 10.02,  8.17,  6.44,  4.2 ,  0.84]]).T,
        np.array(
            [[10.35,  7.25,  5.37],
             [26.48, 19.07, 13.92]]))

    for prm, exp in zip(prem[:4], expected):
        assert np.all((prm - exp) == pytest.approx(0, TOL)), "values don't all match"


def test_100_acres_madison_corn_NO_TA():
    # Premiums for Madison County corn without trend adjustment (verified)
    settings = {
        'rateyield': 154,
        'adjyield': 154,
        'tayield': 164,
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
        'prot_factor': 1.2
    }
    p = Premium()
    prem = p.compute_prems(**settings)
    expected = (
        np.array(
            [[1.62,  2.11,  2.76,  3.61,  4.8 ,  7.49, 13.97, 27.06],
             [1.2 ,  1.42,  1.8 ,  2.27,  2.9 ,  4.48,  8.51, 16.78],
             [1.37,  1.72,  2.18,  2.79,  3.57,  5.31,  9.58, 18.09]]).T,
        np.array(
            [[18.8 , 25.96, 33.8 , 49.35, 70.50],
             [15.9 , 20.7 , 25.54, 35.47, 49.01],
             [16.01, 18.02, 22.54, 25.84, 34.21]]).T,
        np.array(
            [[14.28, 13.92, 13.72, 13.23, 12.17, 10.2 ,  6.69,  1.32],
             [09.61,  9.27,  9.23,  9.  ,  8.38,  7.1 ,  4.69,  0.93],
             [07.51,  7.18,  7.06,  6.79,  6.25,  5.28,  3.56,  0.72]]).T,
        np.array(
            [[09.9 ,  7.02,  4.88],
             [25.59, 18.64, 12.98]]))

    for prm, exp in zip(prem[:4], expected):
        assert np.all((prm - exp) == pytest.approx(0, TOL)), "values don't all match"


# To get SCO and ECO rates, we must specify the county practice directly
def test_300_acres_adams_cty_colorado_irrigated_wheat():
    settings = {
        'rateyield': 65,
        'adjyield': 65,
        'tayield': 70,
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
        'prot_factor': 1,
    }
    p = Premium()
    prem = p.compute_prems(**settings)
    expected = (
        np.array(
            [[4.03,  5.2 ,  6.51,  8.03, 10.22, 15.1 , 26.3 , 47.49],
             [3.56,  4.51,  5.53,  6.73,  8.54, 12.66, 22.09, 39.94],
             [2.9 ,  3.61,  4.41,  5.34,  6.78, 10.19, 17.98, 32.96]]).T,
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
            assert exp is None, "Values don't all match"
        else:
            assert np.all((prm - exp) ==
                          pytest.approx(0, TOL)), "values don't all match"
