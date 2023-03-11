import numpy as np
from ifbt import EntPrems

# This loads all data (expensive), so only do it once!
# Note: 'expected' arrays marked 'verified' have been checked against excel
# Note: When verifying against the Excel file, note that the APH Yield and
#       Rate Yield are reversed on the premiums tab.
ep = EntPrems()


def test_with_default_values():
    # Premiums for Default settings (verified)
    prem = ep.compute_premiums()
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

    assert np.all((prem - expected) == 0), "values don't all match"


def test_3000_acres_corn_in_champaign():
    # Premiums for 3000 acres corn (verified)
    settings = {
        'aphyield': 180,
        'apprYield': 180,
        'tayield': 190,
        'acre': 3000,
        'hf': 0,             # hail and fire protection
        'pf': 0,             # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'riskname': 'None',  # {'None', 'AAA', 'BBB', 'CCC', 'DDD'}
        'tause': 1,          # 1 to use trend-adjusted yields 0 else
        'ye': 0,             # 1 to use yield-exclusion 0 else
        'county': 'Champaign, IL',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'atype': 'Grain'
    }
    prem = ep.compute_premiums(**settings)
    expected = np.array(
      [[00.83,  0.67,  0.68],
       [01.16,  0.81,  0.90],
       [01.62,  0.94,  1.23],
       [02.4 ,  1.22,  1.76],
       [03.5 ,  1.74,  2.42],
       [05.95,  2.85,  3.81],
       [11.99,  5.87,  7.15],
       [25.66, 13.09, 13.92]])

    assert np.all((prem - expected) == 0), "values don't all match"


def test_3000_acres_champaign_full_soy():
    # Premiums for 3000 acres full season soybeans in Champaign (verified)
    settings = {
        'aphyield': 58.0,
        'apprYield': 58.0,
        'tayield': 60,
        'acre': 3000,
        'hf': 0,             # hail and fire protection
        'pf': 0,             # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'riskname': 'None',  # {'None', 'AAA', 'BBB', 'CCC', 'DDD'}
        'tause': 1,          # 1 to use trend-adjusted yields 0 else
        'ye': 0,             # 1 to use yield-exclusion 0 else
        'county': 'Champaign, IL',
        'crop': 'Soybeans',
        'practice': 'Nfac (non-irrigated)',
        'atype': 'No Type Specified'
    }
    prem = ep.compute_premiums(**settings)
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

    assert np.all((prem - expected) == 0), "values don't all match"


def test_300_acres_wheat_champaign():
    # Premiums for 300 acres wheat in Champaign (verified)
    settings = {
        'aphyield': 39.0,
        'apprYield': 39.0,
        'tayield': 38.5,
        'acre': 300,
        'hf': 0,             # hail and fire protection
        'pf': 0,             # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'riskname': 'None',  # {'None', 'AAA', 'BBB', 'CCC', 'DDD'}
        'tause': 1,          # 1 to use trend-adjusted yields 0 else
        'ye': 0,             # 1 to use yield-exclusion 0 else
        'county': 'Champaign, IL',
        'crop': 'Wheat',
        'practice': 'Non-irrigated',
        'atype': 'Winter'
    }
    prem = ep.compute_premiums(**settings)
    expected = np.array(
      [[02.75,  2.34,  2.12],
       [03.36,  2.86,  2.57],
       [04.05,  3.44,  3.08],
       [04.84,  4.12,  3.67],
       [05.99,  5.14,  4.60],
       [08.77,  7.58,  6.84],
       [15.2 , 13.24, 12.02],
       [27.46, 24.05, 21.98]])

    assert np.all((prem - expected) == 0), "values don't all match"


def test_100_acres_madison_corn():
    # Premiums for Madison County corn (verified)
    settings = {
        'aphyield': 154,
        'apprYield': 154,
        'tayield': 164,
        'acre': 100,
        'hf': 0,             # hail and fire protection
        'pf': 0,             # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'riskname': 'None',  # {'None', 'AAA', 'BBB', 'CCC', 'DDD'}
        'tause': 1,          # 1 to use trend-adjusted yields 0 else
        'ye': 0,             # 1 to use yield-exclusion 0 else
        'county': 'Madison, IL',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'atype': 'Grain'
    }
    prem = ep.compute_premiums(**settings)
    expected = np.array(
      [[01.92,  1.34,  1.58],
       [02.6 ,  1.71,  2.07],
       [03.42,  2.16,  2.66],
       [04.55,  2.77,  3.42],
       [06.47,  3.87,  4.59],
       [10.02,  6.11,  6.87],
       [18.47, 11.45, 12.34],
       [36.25, 23.17, 22.92]])

    assert np.all((prem - expected) == 0), "values don't all match"


def test_3000_acres_full_soybeans_madison():
    # Premiums for 3000 acres full season soybeans in Madison (verified)
    settings = {
        'aphyield': 47.0,
        'apprYield': 47.0,
        'tayield': 50,
        'acre': 3000,
        'hf': 0,             # hail and fire protection
        'pf': 0,             # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'riskname': 'None',  # {'None', 'AAA', 'BBB', 'CCC', 'DDD'}
        'tause': 1,          # 1 to use trend-adjusted yields 0 else
        'ye': 0,             # 1 to use yield-exclusion 0 else
        'county': 'Madison, IL',
        'crop': 'Soybeans',
        'practice': 'Nfac (non-irrigated)',
        'atype': 'No Type Specified'
    }
    prem = ep.compute_premiums(**settings)
    expected = np.array(
      [[00.91,  0.69,  0.79],
       [01.26,  0.88,  1.05],
       [01.79,  1.2 ,  1.41],
       [02.51,  1.67,  1.91],
       [03.44,  2.29,  2.58],
       [05.59,  3.7 ,  4.18],
       [10.42,  6.97,  7.76],
       [19.98, 13.58, 14.52]])

    assert np.all((prem - expected) == 0), "values don't all match"


def test_300_acres_wheat_madison():
    # Premiums for 300 acres wheat in Madison (verified)
    settings = {
        'aphyield': 58.0,
        'apprYield': 58.0,
        'tayield': 61.0,
        'acre': 300,
        'hf': 0,             # hail and fire protection
        'pf': 0,             # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'riskname': 'None',  # {'None', 'AAA', 'BBB', 'CCC', 'DDD'}
        'tause': 1,          # 1 to use trend-adjusted yields 0 else
        'ye': 0,             # 1 to use yield-exclusion 0 else
        'county': 'Madison, IL',
        'crop': 'Wheat',
        'practice': 'Non-irrigated',
        'atype': 'Winter'
    }
    prem = ep.compute_premiums(**settings)
    expected = np.array(
      [[03.27,  2.76,  2.41],
       [04.03,  3.39,  2.88],
       [04.9 ,  4.1 ,  3.42],
       [06.05,  5.03,  4.22],
       [07.85,  6.59,  5.60],
       [11.38,  9.61,  8.21],
       [19.56, 16.58, 14.28],
       [35.2 , 29.92, 25.51]])

    assert np.all((prem - expected) == 0), "values don't all match"


def test_300_acres_fac_soy_madison():
    # Premiums for 300 acres Fac soybeans in Madison (verified)
    settings = {
        'aphyield': 47.0,
        'apprYield': 47.0,
        'tayield': 49.0,
        'acre': 300,
        'hf': 0,             # hail and fire protection
        'pf': 0,             # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'riskname': 'None',  # {'None', 'AAA', 'BBB', 'CCC', 'DDD'}
        'tause': 1,          # 1 to use trend-adjusted yields 0 else
        'ye': 0,             # 1 to use yield-exclusion 0 else
        'county': 'Madison, IL',
        'crop': 'Soybeans',
        'practice': 'Fac (non-irrigated)',
        'atype': 'No Type Specified'
    }
    prem = ep.compute_premiums(**settings)
    expected = np.array(
      [[01.7 ,  1.28,  1.47],
       [02.26,  1.66,  1.90],
       [03.11,  2.26,  2.53],
       [04.05,  2.94,  3.24],
       [05.16,  3.72,  4.11],
       [07.57,  5.47,  6.01],
       [13.34,  9.66, 10.56],
       [25.34, 18.62, 19.73]])

    assert np.all((prem - expected) == 0), "values don't all match"


def test_100_acres_corn_st_charles_mo_risk_BBB():
    # Premiums for 100 acres corn in St. Charles, MO (verified)
    settings = {
        'aphyield': 147.0,
        'apprYield': 147.0,
        'tayield': 156.0,
        'acre': 100,
        'hf': 0,             # hail and fire protection
        'pf': 0,             # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'riskname': 'BBB',  # {'None', 'AAA', 'BBB', 'CCC', 'DDD'}
        'tause': 1,          # 1 to use trend-adjusted yields 0 else
        'ye': 0,             # 1 to use yield-exclusion 0 else
        'county': 'St._Charles, MO',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'atype': 'Grain'
    }
    prem = ep.compute_premiums(**settings)
    expected = np.array(
      [[08.41,  6.62, 6.91],
       [10.31,  8.14, 8.47],
       [12.79, 10.2 , 10.45],
       [15.44, 12.4 , 12.47],
       [18.61, 14.99, 14.94],
       [26.19, 21.27, 21.08],
       [43.3 , 35.39, 34.99],
       [75.04, 61.75, 59.29]])

    assert np.all((prem - expected) == 0), "values don't all match"


def test_100_acres_madison_corn_NO_TA():
    # Premiums for Madison County corn without trend adjustment (verified)
    settings = {
        'aphyield': 154,
        'apprYield': 154,
        'tayield': 164,
        'acre': 100,
        'hf': 0,             # hail and fire protection
        'pf': 0,             # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'riskname': 'None',  # {'None', 'AAA', 'BBB', 'CCC', 'DDD'}
        'tause': 0,          # 1 to use trend-adjusted yields 0 else
        'ye': 0,             # 1 to use yield-exclusion 0 else
        'county': 'Madison, IL',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'atype': 'Grain'
    }
    prem = ep.compute_premiums(**settings)
    expected = np.array(
      [[01.62,  1.2 ,  1.37],
       [02.11,  1.42,  1.72],
       [02.76,  1.8 ,  2.18],
       [03.61,  2.27,  2.79],
       [04.8 ,  2.9 ,  3.57],
       [07.49,  4.48,  5.31],
       [13.97,  8.51,  9.58],
       [27.06, 16.78, 18.09]])

    assert np.all((prem - expected) == 0), "values don't all match"
