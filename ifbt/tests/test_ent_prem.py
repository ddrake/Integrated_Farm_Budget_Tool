import numpy as np
from ifbt import EntPrems

# This loads all data (expensive), so only do it once!
# Note: 'expected' arrays marked 'verified' have been checked against excel
ep = EntPrems()


def test_with_default_values():
    # Premiums for Default settings (verified)
    prem = ep.compute_premiums()
    print(prem)

    expected = np.array(
        [[02.27,  1.49,  0.9 ,  1.66,  1.17,  0.71,  1.86,  1.21,  0.73],
         [03.46,  2.34,  1.28,  2.22,  1.61,  0.87,  2.69,  1.79,  0.99],
         [04.81,  3.41,  1.79,  2.92,  2.02,  1.01,  3.63,  2.46,  1.37],
         [07.96,  5.85,  2.62,  4.69,  3.26,  1.36,  5.79,  4.01,  1.96],
         [11.36,  8.54,  3.79,  6.56,  4.69,  1.91,  7.89,  5.57,  2.69],
         [17.83, 13.9 ,  6.38, 10.39,  7.52,  3.12, 11.86,  8.53,  4.22],
         [28.75, 23.23, 12.72, 17.34, 12.94,  6.39, 18.53, 13.57,  7.90],
         [46.85, 39.29, 26.97, 28.59, 22.35, 14.13, 28.72, 21.48, 15.34]])

    assert np.all((prem - expected) == 0), "values don't all match"


def test_3000_acres_corn_in_champaign():
    # Premiums for 3000 acres corn (verified)
    settings = {
        'aphyield': 180,
        'apprYield': 180,
        'tayield': 190,
        'acre': 3000,
        'aphPrice': 5.91,
        'pvol': 0.18,
        'hf': 0,        # possibly harvest factor
        'pf': 0,        # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'highRisk': 0,  # only visible option is None -> 0
        'rtype': 0,     # only visible option is None -> 0
        'tause': 1,     # 0 if K7 is 'No' else 1
        'ye': 0,        # 1 if K7 is 'YE' or 'TA/YE' else 0
        'county': 'Champaign, IL',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'atype': 'Grain'
    }
    prem = ep.compute_premiums(**settings)
    expected = np.array(
      [[02.27,  1.37,  0.83,  1.66,  1.11,  0.67,  1.86,  1.12,  0.68],
       [03.46,  2.11,  1.16,  2.22,  1.49,  0.81,  2.69,  1.62,  0.90],
       [04.81,  3.1 ,  1.62,  2.92,  1.86,  0.94,  3.63,  2.21,  1.23],
       [07.96,  5.35,  2.4 ,  4.69,  2.92,  1.22,  5.79,  3.62,  1.76],
       [11.36,  7.87,  3.5 ,  6.55,  4.26,  1.74,  7.89,  5.03,  2.42],
       [17.83, 12.92,  5.95, 10.38,  6.86,  2.85, 11.86,  7.71,  3.81],
       [28.75, 21.8 , 11.99, 17.34, 11.85,  5.87, 18.53, 12.29,  7.15],
       [46.85, 37.22, 25.66, 28.59, 20.64, 13.09, 28.72, 19.5 , 13.92]])

    assert np.all((prem - expected) == 0), "values don't all match"


def test_3000_acres_champaign_full_soy():
    # Premiums for 3000 acres full season soybeans in Champaign (verified)
    settings = {
        'aphyield': 58.0,
        'apprYield': 58.0,
        'tayield': 60,
        'acre': 3000,
        'aphPrice': 13.76,
        'pvol': 0.13,
        'hf': 0,        # possibly harvest factor
        'pf': 0,        # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'highRisk': 0,  # only visible option is None -> 0
        'rtype': 0,     # only visible option is None -> 0
        'tause': 1,     # 0 if K7 is 'No' else 1
        'ye': 0,        # 1 if K7 is 'YE' or 'TA/YE' else 0
        'county': 'Champaign, IL',
        'crop': 'Soybeans',
        'practice': 'Nfac (non-irrigated)',
        'atype': 'No Type Specified'
    }
    prem = ep.compute_premiums(**settings)
    print(prem)
    expected = np.array(
      [[00.41,  0.27,  0.16,  0.35,  0.23,  0.14,  0.38,  0.25,  0.15],
       [00.64,  0.43,  0.24,  0.46,  0.31,  0.17,  0.52,  0.36,  0.20],
       [00.89,  0.66,  0.37,  0.58,  0.42,  0.23,  0.69,  0.49,  0.27],
       [01.53,  1.18,  0.58,  0.84,  0.64,  0.31,  1.06,  0.8 ,  0.39],
       [02.45,  1.99,  0.97,  1.22,  0.97,  0.47,  1.44,  1.13,  0.55],
       [04.32,  3.73,  1.9 ,  1.91,  1.64,  0.83,  2.24,  1.83,  0.93],
       [07.12,  6.38,  3.9 ,  2.96,  2.61,  1.58,  3.49,  2.94,  1.78],
       [11.82, 10.92,  8.23,  4.59,  4.16,  3.1 ,  5.36,  4.64,  3.45]])

    assert np.all((prem - expected) == 0), "values don't all match"


def test_300_acres_wheat_champaign():
    # Premiums for 300 acres wheat in Champaign (verified)
    settings = {
        'aphyield': 39.0,
        'apprYield': 39.0,
        'tayield': 38.5,
        'acre': 300,
        'aphPrice': 7.25,
        'pvol': 0.24,
        'hf': 0,        # possibly harvest factor
        'pf': 0,        # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'highRisk': 0,  # only visible option is None -> 0
        'rtype': 0,     # only visible option is None -> 0
        'tause': 1,     # 0 if K7 is 'No' else 1
        'ye': 0,        # 1 if K7 is 'YE' or 'TA/YE' else 0
        'county': 'Champaign, IL',
        'crop': 'Wheat',
        'practice': 'Non-irrigated',
        'atype': 'Winter'
    }
    prem = ep.compute_premiums(**settings)
    expected = np.array(
      [[06.88,  4.54,  2.75,  5.98,  3.87,  2.34,  5.59,  3.5 ,  2.12],
       [09.05,  6.04,  3.36,  7.89,  5.15,  2.86,  7.38,  4.63,  2.57],
       [10.75,  7.29,  4.05,  9.35,  6.2 ,  3.44,  8.8 ,  5.54,  3.08],
       [14.59,  9.92,  4.84, 12.7 ,  8.45,  4.12, 11.93,  7.52,  3.67],
       [17.9 , 12.53,  5.99, 15.7 , 10.79,  5.14, 14.78,  9.68,  4.60],
       [23.85, 17.78,  8.77, 21.01, 15.45,  7.58, 19.81, 14.01,  6.84],
       [33.15, 26.01, 15.2 , 29.35, 22.83, 13.24, 27.71, 20.84, 12.02],
       [47.28, 38.74, 27.46, 42.14, 34.24, 24.05, 39.89, 31.51, 21.98]])

    assert np.all((prem - expected) == 0), "values don't all match"


def test_100_acres_madison_corn():
    # Premiums for Madison County corn (verified)
    settings = {
        'aphyield': 154,
        'apprYield': 154,
        'tayield': 164,
        'acre': 100,
        'aphPrice': 5.91,
        'pvol': 0.18,
        'hf': 0,        # possibly harvest factor
        'pf': 0,        # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'highRisk': 0,  # only visible option is None -> 0
        'rtype': 0,     # only visible option is None -> 0
        'tause': 1,     # 0 if K7 is 'No' else 1
        'ye': 0,        # 1 if K7 is 'YE' or 'TA/YE' else 0
        'county': 'Madison, IL',
        'crop': 'Corn',
        'practice': 'Non-irrigated',
        'atype': 'Grain'
    }
    prem = ep.compute_premiums(**settings)
    expected = np.array(
      [[04.88,  3.16,  1.92,  3.43,  2.21,  1.34,  4.06,  2.61,  1.58],
       [06.98,  4.69,  2.6 ,  4.75,  3.07,  1.71,  5.67,  3.73,  2.07],
       [08.91,  6.16,  3.42,  5.92,  3.89,  2.16,  7.14,  4.79,  2.66],
       [13.27,  9.32,  4.55,  8.62,  5.67,  2.77, 10.25,  7.01,  3.42],
       [18.29, 13.4 ,  6.47, 11.99,  8.08,  3.87, 13.66,  9.55,  4.59],
       [26.58, 20.12, 10.02, 17.74, 12.46,  6.11, 19.62, 13.96,  6.87],
       [40.08, 31.25, 18.47, 27.45, 19.85, 11.45, 29.37, 21.3 , 12.34],
       [60.49, 48.81, 36.25, 42.24, 31.56, 23.17, 43.35, 32.1 , 22.92]])

    assert np.all((prem - expected) == 0), "values don't all match"


def test_3000_acres_full_soybeans_madison():
    # Premiums for 3000 acres full season soybeans in Madison (verified)
    settings = {
        'aphyield': 47.0,
        'apprYield': 47.0,
        'tayield': 50,
        'acre': 3000,
        'aphPrice': 13.76,
        'pvol': 0.13,
        'hf': 0,        # possibly harvest factor
        'pf': 0,        # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'highRisk': 0,  # only visible option is None -> 0
        'rtype': 0,     # only visible option is None -> 0
        'tause': 1,     # 0 if K7 is 'No' else 1
        'ye': 0,        # 1 if K7 is 'YE' or 'TA/YE' else 0
        'county': 'Madison, IL',
        'crop': 'Soybeans',
        'practice': 'Nfac (non-irrigated)',
        'atype': 'No Type Specified'
    }
    prem = ep.compute_premiums(**settings)
    expected = np.array(
      [[02.21,  1.5 ,  0.91,  1.68,  1.15,  0.69,  1.93,  1.3 ,  0.79],
       [03.26,  2.27,  1.26,  2.32,  1.58,  0.88,  2.72,  1.89,  1.05],
       [04.41,  3.21,  1.79,  3.09,  2.15,  1.2 ,  3.52,  2.54,  1.41],
       [06.77,  5.15,  2.51,  4.7 ,  3.42,  1.67,  5.26,  3.91,  1.91],
       [08.89,  7.06,  3.44,  6.13,  4.69,  2.29,  6.89,  5.29,  2.58],
       [13.41, 11.01,  5.59,  9.33,  7.31,  3.7 , 10.38,  8.26,  4.18],
       [20.36, 17.19, 10.42, 14.31, 11.59,  6.97, 15.72, 12.86,  7.76],
       [30.55, 26.54, 19.98, 21.67, 18.1 , 13.58, 23.27, 19.55, 14.52]])

    assert np.all((prem - expected) == 0), "values don't all match"


def test_300_acres_wheat_madison():
    # Premiums for 300 acres wheat in Madison (verified)
    settings = {
        'aphyield': 58.0,
        'apprYield': 58.0,
        'tayield': 61.0,
        'acre': 300,
        'aphPrice': 7.25,
        'pvol': 0.24,
        'hf': 0,        # possibly harvest factor
        'pf': 0,        # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'highRisk': 0,  # only visible option is None -> 0
        'rtype': 0,     # only visible option is None -> 0
        'tause': 1,     # 0 if K7 is 'No' else 1
        'ye': 0,        # 1 if K7 is 'YE' or 'TA/YE' else 0
        'county': 'Madison, IL',
        'crop': 'Wheat',
        'practice': 'Non-irrigated',
        'atype': 'Winter'
    }
    prem = ep.compute_premiums(**settings)
    expected = np.array(
      [[08.11,  5.4 ,  3.27,  6.95,  4.55,  2.76,  6.32,  3.97,  2.41],
       [10.7 ,  7.25,  4.03,  9.14,  6.1 ,  3.39,  8.25,  5.19,  2.88],
       [12.75,  8.82,  4.9 , 10.9 ,  7.38,  4.1 ,  9.78,  6.16,  3.42],
       [17.63, 12.54,  6.05, 15.14, 10.45,  5.03, 13.61,  8.78,  4.22],
       [22.12, 16.58,  7.85, 19.01, 14.  ,  6.59, 17.18, 11.97,  5.60],
       [29.46, 23.27, 11.38, 25.41, 19.81,  9.61, 22.99, 17.08,  8.21],
       [40.93, 33.73, 19.56, 35.39, 28.89, 16.58, 32.14, 25.15, 14.28],
       [56.73, 48.8 , 35.2 , 49.01, 41.83, 29.92, 44.57, 36.56, 25.51]])

    assert np.all((prem - expected) == 0), "values don't all match"


def test_300_acres_fac_soy_madison():
    # Premiums for 300 acres Fac soybeans in Madison (verified)
    settings = {
        'aphyield': 47.0,
        'apprYield': 47.0,
        'tayield': 49.0,
        'acre': 300,
        'aphPrice': 13.76,
        'pvol': 0.13,
        'hf': 0,        # possibly harvest factor
        'pf': 0,        # prevent plant factor: std=0, Plus5%=1, Plus10%=2
        'highRisk': 0,  # only visible option is None -> 0
        'rtype': 0,     # only visible option is None -> 0
        'tause': 1,     # 0 if K7 is 'No' else 1
        'ye': 0,        # 1 if K7 is 'YE' or 'TA/YE' else 0
        'county': 'Madison, IL',
        'crop': 'Soybeans',
        'practice': 'Fac (non-irrigated)',
        'atype': 'No Type Specified'
    }
    prem = ep.compute_premiums(**settings)
    expected = np.array(
      [[04.06,  2.81,  1.7 ,  3.13,  2.1 ,  1.28,  3.48,  2.42,  1.47],
       [05.75,  4.07,  2.26,  4.38,  2.99,  1.66,  4.83,  3.41,  1.90],
       [07.63,  5.59,  3.11,  5.79,  4.06,  2.26,  6.29,  4.55,  2.53],
       [11.  ,  8.31,  4.05,  8.34,  6.03,  2.94,  9.03,  6.64,  3.24],
       [13.7 , 10.58,  5.16, 10.37,  7.62,  3.72, 11.23,  8.43,  4.11],
       [18.83, 14.86,  7.57, 14.27, 10.75,  5.47, 15.4 , 11.82,  6.01],
       [27.14, 21.95, 13.34, 20.67, 15.97,  9.66, 22.21, 17.43, 10.56],
       [40.52, 33.73, 25.34, 31.25, 24.87, 18.62, 32.94, 26.56, 19.73]])

    assert np.all((prem - expected) == 0), "values don't all match"
