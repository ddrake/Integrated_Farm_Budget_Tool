import numpy as np
import pytest
from ifbt import Premiums

TOL = .01
# Note: 'expected' arrays marked 'verified' have been checked against excel
# Note: When verifying against the Excel file, note that the APH Yield and
#       Rate Yield are reversed on the premiums tab.
# Abbreviations
# 'hailfire'             # hail and fire protection
# 'prevplant'             # prevent plant factor: std=0, Plus5%=1, Plus10%=2
# 'riskname': 'BBB',  # {'None', 'AAA', 'BBB', 'CCC', 'DDD'}
# 'tause': 1,          # 1 to use trend-adjusted yields 0 else
# 'yieldexcl': 0,             # 1 to use yield-exclusion 0 else
#
# Note: An premium array of zeros means no premiums are avaiable for the product
# Note: arc premiums use the 120% protection factor to match an Excel column.

# This loads all data from textfiles (expensive), so we only do it once!
p = Premiums()


def test_with_default_values():
    # Premiums for Default settings (verified)
    prem = p.compute_prems_ent()
    print(prem)

    expected = np.array(
        [[00.9 ,  0.71,  0.73],
         [01.28,  0.87,  0.99],
         [01.79,  1.01,  1.37],
         [02.62,  1.36,  1.96],
         [03.79,  1.91,  2.69],
         [06.38,  3.12,  4.22],
         [12.72,  6.39,  7.90],
         [26.97, 14.13, 15.34]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_arc(prot_factor=1.2)
    print(prem)

    expected = np.array(
        [[05.35,  9.77, 18.84, 34.91, 58.87],
         [04.71,  7.58, 14.16, 24.88, 39.92],
         [04.58,  6.26, 11.26, 15.93, 23.98]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_sco()
    print(prem)

    expected = np.array(
        [[12.66, 12.65, 12.59, 11.94, 11.01,  9.61,  6.36,  1.39],
         [08.9 ,  8.88,  8.83,  8.19,  7.45,  6.54,  4.21,  0.92],
         [06.34,  6.32,  6.26,  5.64,  4.92,  4.2 ,  2.64,  0.61]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_eco()
    print(prem)

    expected = np.array(
        [[11.28, 30.70],
         [07.55, 20.66],
         [05.24, 15.18]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"


def test_3000_acres_corn_in_champaign():
    # Premiums for 3000 acres corn (verified)
    settings_ent = {
        'aphyield': 180,
        'apprYield': 180,
        'tayield': 190,
        'acres': 3000,
        'hailfire': 0,
        'prevplant': 0,
        'riskname': 'None',
        'tause': 1,
        'yieldexcl': 0,
        'county': 'Champaign, IL',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'croptype': 'Grain'
    }
    settings_arc = {
        'county': 'Champaign, IL',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'croptype': 'Grain',
        'prot_factor': 1.2,
    }
    settings_opt = {
        'aphyield': 180,
        'tayield': 190,
        'tause': 1,
        'county': 'Champaign, IL',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'croptype': 'Grain'
    }
    prem = p.compute_prems_ent(**settings_ent)
    expected = np.array(
      [[00.83,  0.67,  0.68],
       [01.16,  0.81,  0.90],
       [01.62,  0.94,  1.23],
       [02.4 ,  1.22,  1.76],
       [03.5 ,  1.74,  2.42],
       [05.95,  2.85,  3.81],
       [11.99,  5.87,  7.15],
       [25.66, 13.09, 13.92]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_arc(**settings_arc)
    print(prem)

    expected = np.array(
        [[05.35,  9.77, 18.84, 34.91, 58.87],
         [04.71,  7.58, 14.16, 24.88, 39.92],
         [04.58,  6.26, 11.26, 15.93, 23.98]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_sco(**settings_opt)
    print(prem)

    expected = np.array(
        [[12.66, 12.65, 12.59, 11.94, 11.01,  9.61,  6.36,  1.39],
         [08.9 ,  8.88,  8.83,  8.19,  7.45,  6.54,  4.21,  0.92],
         [06.34,  6.32,  6.26,  5.64,  4.92,  4.2 ,  2.64,  0.61]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_eco(**settings_opt)
    print(prem)

    expected = np.array(
        [[11.28, 30.70],
         [07.55, 20.66],
         [05.24, 15.18]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"


def test_3000_acres_champaign_full_soy():
    # Premiums for 3000 acres full season soybeans in Champaign (verified)
    settings_ent = {
        'aphyield': 58.0,
        'apprYield': 58.0,
        'tayield': 60,
        'acres': 3000,
        'hailfire': 0,
        'prevplant': 0,
        'riskname': 'None',
        'tause': 1,
        'yieldexcl': 0,
        'county': 'Champaign, IL',
        'crop': 'Soybeans',
        'practice': 'Nfac (non-irrigated)',
        'croptype': 'No Type Specified'
    }
    settings_arc = {
        'county': 'Champaign, IL',
        'crop': 'Soybeans',
        'practice': 'Nfac (non-irrigated)',
        'croptype': 'No Type Specified',
        'prot_factor': 1.2,
    }
    settings_opt = {
        'aphyield': 58.0,
        'tayield': 60,
        'tause': 1,
        'county': 'Champaign, IL',
        'crop': 'Soybeans',
        'practice': 'Nfac (non-irrigated)',
        'croptype': 'No Type Specified'
    }
    prem = p.compute_prems_ent(**settings_ent)
    print(prem)
    expected = np.array(
      [[0.16, 0.14, 0.15],
       [0.24, 0.17, 0.20],
       [0.37, 0.23, 0.27],
       [0.58, 0.31, 0.39],
       [0.97, 0.47, 0.55],
       [1.9 , 0.83, 0.93],
       [3.9 , 1.58, 1.78],
       [8.23, 3.1 , 3.45]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_arc(**settings_arc)
    print(prem)

    expected = np.array(
        [[01.89,  3.33,  5.91, 13.52, 26.91],
         [01.2 ,  2.17,  5.31, 11.68, 22.32],
         [01.34,  1.57,  2.43,  4.09,  8.64]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_sco(**settings_opt)
    print(prem)

    expected = np.array(
        [[5.23, 5.23, 5.24, 5.23, 5.11, 4.6 , 3.15, 0.70],
         [4.46, 4.46, 4.47, 4.46, 4.35, 3.86, 2.59, 0.56],
         [1.76, 1.76, 1.76, 1.76, 1.73, 1.5 , 0.99, 0.24]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_eco(**settings_opt)
    print(prem)

    expected = np.array(
        [[05.99, 17.34],
         [04.78, 13.64],
         [02.51,  8.55]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"


def test_300_acres_wheat_champaign():
    # Premiums for 300 acres wheat in Champaign (verified)
    # NOTE: The ARP premiums are not available for this case.
    # NOTE: The sco and eco premiums in the excel tool are incorrect in this case.
    #   The rates were verified against the RMA tool.
    settings_ent = {
        'aphyield': 39.0,
        'apprYield': 39.0,
        'tayield': 38.5,
        'acres': 300,
        'hailfire': 0,
        'prevplant': 0,
        'riskname': 'None',
        'tause': 1,
        'yieldexcl': 0,
        'county': 'Champaign, IL',
        'crop': 'Wheat',
        'practice': 'Non-irrigated',
        'croptype': 'Winter'
    }
    settings_arc = {
        'county': 'Champaign, IL',
        'crop': 'Wheat',
        'practice': 'Non-irrigated',
        'croptype': 'Winter',
        'prot_factor': 1.2,
    }
    settings_opt = {
        'aphyield': 39.0,
        'tayield': 38.5,
        'tause': 1,
        'county': 'Champaign, IL',
        'crop': 'Wheat',
        'practice': 'Non-irrigated',
        'croptype': 'Winter'
    }
    prem = p.compute_prems_ent(**settings_ent)
    expected = np.array(
      [[02.75,  2.34,  2.12],
       [03.36,  2.86,  2.57],
       [04.05,  3.44,  3.08],
       [04.84,  4.12,  3.67],
       [05.99,  5.14,  4.60],
       [08.77,  7.58,  6.84],
       [15.2 , 13.24, 12.02],
       [27.46, 24.05, 21.98]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_arc(**settings_arc)
    print(prem)

    expected = np.array(
        [[0., 0., 0., 0., 0.],
         [0., 0., 0., 0., 0.],
         [0., 0., 0., 0., 0.]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_sco(**settings_opt)
    print(prem)

    expected = np.array(
        [[8.88, 8.53, 7.98, 7.2 , 6.1 , 4.65, 2.8 , 0.51],
         [7.23, 6.95, 6.5 , 5.85, 4.93, 3.74, 2.23, 0.41],
         [4.5 , 4.36, 4.13, 3.81, 3.31, 2.59, 1.6 , 0.30]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_eco(**settings_opt)
    print(prem)

    expected = np.array(
        [[3.54, 8.47],
         [2.86, 6.88],
         [2.14, 5.32]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"


def test_100_acres_madison_corn():
    # Premiums for Madison County corn (verified)
    settings_ent = {
        'aphyield': 154,
        'apprYield': 154,
        'tayield': 164,
        'acres': 100,
        'hailfire': 0,
        'prevplant': 0,
        'riskname': 'None',
        'tause': 1,
        'yieldexcl': 0,
        'county': 'Madison, IL',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'croptype': 'Grain'
    }
    settings_arc = {
        'county': 'Madison, IL',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'croptype': 'Grain',
        'prot_factor': 1.2,
    }
    settings_opt = {
        'aphyield': 154,
        'tayield': 164,
        'tause': 1,
        'county': 'Madison, IL',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'croptype': 'Grain'
    }
    prem = p.compute_prems_ent(**settings_ent)
    expected = np.array(
      [[01.92,  1.34,  1.58],
       [02.6 ,  1.71,  2.07],
       [03.42,  2.16,  2.66],
       [04.55,  2.77,  3.42],
       [06.47,  3.87,  4.59],
       [10.02,  6.11,  6.87],
       [18.47, 11.45, 12.34],
       [36.25, 23.17, 22.92]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_arc(**settings_arc)
    print(prem)

    expected = np.array(
        [[18.8 , 25.96, 33.8 , 49.35, 70.50],
         [15.9 , 20.7 , 25.54, 35.47, 49.01],
         [16.01, 18.02, 22.54, 25.84, 34.21]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_sco(**settings_opt)
    print(prem)

    expected = np.array(
        [[15.2 , 14.83, 14.61, 14.09, 12.96, 10.86,  7.12,  1.40],
         [10.23,  9.87,  9.82,  9.58,  8.92,  7.56,  5.  ,  0.99],
         [08.  ,  7.64,  7.51,  7.23,  6.65,  5.62,  3.79,  0.77]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_eco(**settings_opt)
    print(prem)

    expected = np.array(
        [[10.54, 27.25],
         [07.47, 19.85],
         [05.94, 15.80]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"


def test_3000_acres_full_soybeans_madison():
    # Premiums for 3000 acres full season soybeans in Madison (verified)
    settings_ent = {
        'aphyield': 47.0,
        'apprYield': 47.0,
        'tayield': 50,
        'acres': 3000,
        'hailfire': 0,
        'prevplant': 0,
        'riskname': 'None',
        'tause': 1,
        'yieldexcl': 0,
        'county': 'Madison, IL',
        'crop': 'Soybeans',
        'practice': 'Nfac (non-irrigated)',
        'croptype': 'No Type Specified'
    }
    settings_arc = {
        'county': 'Madison, IL',
        'crop': 'Soybeans',
        'practice': 'Nfac (non-irrigated)',
        'croptype': 'No Type Specified',
        'prot_factor': 1.2,
    }
    settings_opt = {
        'aphyield': 47.0,
        'tayield': 50,
        'tause': 1,
        'county': 'Madison, IL',
        'crop': 'Soybeans',
        'practice': 'Nfac (non-irrigated)',
        'croptype': 'No Type Specified'
    }
    prem = p.compute_prems_ent(**settings_ent)
    expected = np.array(
      [[00.91,  0.69,  0.79],
       [01.26,  0.88,  1.05],
       [01.79,  1.2 ,  1.41],
       [02.51,  1.67,  1.91],
       [03.44,  2.29,  2.58],
       [05.59,  3.7 ,  4.18],
       [10.42,  6.97,  7.76],
       [19.98, 13.58, 14.52]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_arc(**settings_arc)
    print(prem)

    expected = np.array(
        [[01.44,  2.91,  5.83, 13.63, 26.67],
         [00.95,  1.71,  4.08,  9.67, 19.31],
         [01.06,  1.82,  3.2 ,  5.7 , 11.96]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_sco(**settings_opt)
    print(prem)

    expected = np.array(
        [[5.36, 5.35, 5.35, 5.34, 5.13, 4.58, 3.27, 0.70],
         [3.81, 3.81, 3.82, 3.81, 3.69, 3.33, 2.4 , 0.52],
         [2.58, 2.58, 2.57, 2.57, 2.47, 2.22, 1.61, 0.37]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_eco(**settings_opt)
    print(prem)

    expected = np.array(
        [[05.71, 15.63],
         [04.23, 11.76],
         [03.21,  9.30]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"


def test_300_acres_wheat_madison():
    # Premiums for 300 acres wheat in Madison (verified)
    settings_ent = {
        'aphyield': 58.0,
        'apprYield': 58.0,
        'tayield': 61.0,
        'acres': 300,
        'hailfire': 0,
        'prevplant': 0,
        'riskname': 'None',
        'tause': 1,
        'yieldexcl': 0,
        'county': 'Madison, IL',
        'crop': 'Wheat',
        'practice': 'Non-irrigated',
        'croptype': 'Winter'
    }
    settings_arc = {
        'county': 'Madison, IL',
        'crop': 'Wheat',
        'practice': 'Non-irrigated',
        'croptype': 'Winter',
        'prot_factor': 1.2,
    }
    settings_opt = {
        'aphyield': 58.0,
        'tayield': 61.0,
        'tause': 1,
        'county': 'Madison, IL',
        'crop': 'Wheat',
        'practice': 'Non-irrigated',
        'croptype': 'Winter'
    }
    prem = p.compute_prems_ent(**settings_ent)
    expected = np.array(
      [[03.27,  2.76,  2.41],
       [04.03,  3.39,  2.88],
       [04.9 ,  4.1 ,  3.42],
       [06.05,  5.03,  4.22],
       [07.85,  6.59,  5.60],
       [11.38,  9.61,  8.21],
       [19.56, 16.58, 14.28],
       [35.2 , 29.92, 25.51]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_arc(**settings_arc)
    print(prem)

    expected = np.array(
        [[14.93, 21.27, 26.57, 36.74, 48.33],
         [13.05, 18.22, 22.42, 30.29, 38.97],
         [08.  ,  9.6 , 12.57, 14.87, 19.36]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_sco(**settings_opt)
    print(prem)

    expected = np.array(
        [[12.58, 12.03, 11.12, 10.18,  8.83,  6.87,  4.23,  0.78],
         [10.3 ,  9.82,  8.99,  8.2 ,  7.12,  5.52,  3.36,  0.61],
         [05.73,  5.36,  4.83,  4.54,  4.07,  3.32,  2.14,  0.42]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_eco(**settings_opt)
    print(prem)

    expected = np.array(
        [[05.54, 13.44],
         [04.37, 10.62],
         [03.05,  7.81]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"


def test_300_acres_fac_soy_madison():
    # Premiums for 300 acres Fac soybeans in Madison (verified)
    settings_ent = {
        'aphyield': 47.0,
        'apprYield': 47.0,
        'tayield': 49.0,
        'acres': 300,
        'hailfire': 0,
        'prevplant': 0,
        'riskname': 'None',
        'tause': 1,
        'yieldexcl': 0,
        'county': 'Madison, IL',
        'crop': 'Soybeans',
        'practice': 'Fac (non-irrigated)',
        'croptype': 'No Type Specified'
    }
    settings_arc = {
        'county': 'Madison, IL',
        'crop': 'Soybeans',
        'practice': 'Fac (non-irrigated)',
        'croptype': 'No Type Specified',
        'prot_factor': 1.2,
    }
    settings_opt = {
        'aphyield': 47.0,
        'tayield': 49.0,
        'tause': 1,
        'county': 'Madison, IL',
        'crop': 'Soybeans',
        'practice': 'Fac (non-irrigated)',
        'croptype': 'No Type Specified'
    }
    prem = p.compute_prems_ent(**settings_ent)
    expected = np.array(
      [[01.7 ,  1.28,  1.47],
       [02.26,  1.66,  1.90],
       [03.11,  2.26,  2.53],
       [04.05,  2.94,  3.24],
       [05.16,  3.72,  4.11],
       [07.57,  5.47,  6.01],
       [13.34,  9.66, 10.56],
       [25.34, 18.62, 19.73]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_arc(**settings_arc)
    print(prem)

    expected = np.array(
        [[01.44,  2.91,  5.83, 13.63, 26.67],
         [00.95,  1.71,  4.08,  9.67, 19.31],
         [01.06,  1.82,  3.2 ,  5.7 , 11.96]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_sco(**settings_opt)
    print(prem)

    expected = np.array(
        [[5.25, 5.25, 5.25, 5.23, 5.03, 4.49, 3.2 , 0.68],
         [3.74, 3.74, 3.74, 3.73, 3.62, 3.26, 2.36, 0.51],
         [2.52, 2.52, 2.52, 2.52, 2.43, 2.18, 1.58, 0.36]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_eco(**settings_opt)
    print(prem)

    expected = np.array(
        [[05.6 , 15.32],
         [04.15, 11.53],
         [03.15,  9.12]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"


def test_100_acres_corn_st_charles_mo_risk_BBB():
    # Premiums for 100 acres corn in St. Charles, MO (verified)
    settings_ent = {
        'aphyield': 147.0,
        'apprYield': 147.0,
        'tayield': 156.0,
        'acres': 100,
        'hailfire': 0,
        'prevplant': 0,
        'riskname': 'BBB',
        'tause': 1,
        'yieldexcl': 0,
        'county': 'St._Charles, MO',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'croptype': 'Grain'
    }
    settings_arc = {
        'county': 'St._Charles, MO',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'croptype': 'Grain',
        'prot_factor': 1.2,
    }
    settings_opt = {
        'aphyield': 147.0,
        'tayield': 156.0,
        'tause': 1,
        'county': 'St._Charles, MO',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'croptype': 'Grain'
    }
    prem = p.compute_prems_ent(**settings_ent)
    expected = np.array(
      [[08.41,  6.62, 6.91],
       [10.31,  8.14, 8.47],
       [12.79, 10.2 , 10.45],
       [15.44, 12.4 , 12.47],
       [18.61, 14.99, 14.94],
       [26.19, 21.27, 21.08],
       [43.3 , 35.39, 34.99],
       [75.04, 61.75, 59.29]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_arc(**settings_arc)
    print(prem)

    expected = np.array(
        [[15.94, 25.  , 33.7 , 49.47, 71.28],
         [11.55, 18.03, 23.63, 33.68, 48.45],
         [13.32, 18.05, 24.63, 29.45, 40.23]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_sco(**settings_opt)
    print(prem)

    expected = np.array(
        [[18.83, 18.31, 17.46, 15.99, 13.65, 11.02,  7.13,  1.39],
         [12.65, 12.28, 11.71, 10.67,  8.98,  7.26,  4.75,  0.93],
         [12.45, 11.97, 11.22, 10.02,  8.17,  6.44,  4.2 ,  0.84]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_eco(**settings_opt)
    print(prem)

    expected = np.array(
        [[10.35, 26.48],
         [07.25, 19.07],
         [06.13, 15.91]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"


def test_100_acres_madison_corn_NO_TA():
    # Premiums for Madison County corn without trend adjustment (verified)
    settings_ent = {
        'aphyield': 154,
        'apprYield': 154,
        'tayield': 164,
        'acres': 100,
        'hailfire': 0,
        'prevplant': 0,
        'riskname': 'None',
        'tause': 0,
        'yieldexcl': 0,
        'county': 'Madison, IL',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'croptype': 'Grain'
    }
    settings_arc = {
        'county': 'Madison, IL',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'croptype': 'Grain',
        'prot_factor': 1.2,
    }
    settings_opt = {
        'aphyield': 154,
        'tayield': 164,
        'tause': 0,
        'county': 'Madison, IL',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'croptype': 'Grain'
    }
    prem = p.compute_prems_ent(**settings_ent)
    expected = np.array(
      [[01.62,  1.2 ,  1.37],
       [02.11,  1.42,  1.72],
       [02.76,  1.8 ,  2.18],
       [03.61,  2.27,  2.79],
       [04.8 ,  2.9 ,  3.57],
       [07.49,  4.48,  5.31],
       [13.97,  8.51,  9.58],
       [27.06, 16.78, 18.09]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_arc(**settings_arc)
    print(prem)

    expected = np.array(
        [[18.8 , 25.96, 33.8 , 49.35, 70.50],
         [15.9 , 20.7 , 25.54, 35.47, 49.01],
         [16.01, 18.02, 22.54, 25.84, 34.21]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_sco(**settings_opt)
    print(prem)

    expected = np.array(
        [[14.28, 13.92, 13.72, 13.23, 12.17, 10.2 ,  6.69,  1.32],
         [09.61,  9.27,  9.23,  9.  ,  8.38,  7.1 ,  4.69,  0.93],
         [07.51,  7.18,  7.06,  6.79,  6.25,  5.28,  3.56,  0.72]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"

    prem = p.compute_prems_eco(**settings_opt)
    print(prem)

    expected = np.array(
        [[09.9 , 25.59],
         [07.02, 18.64],
         [05.58, 14.84]])

    assert np.all((prem - expected) == pytest.approx(0, TOL)), "values don't all match"
