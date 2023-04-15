import os
import pickle

DATADIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../data')

CROP = {'Corn': 0, 'Soybeans': 1, 'Wheat': 2}
ARC_PRAC = {'All': 0, 'Irrigated': 1, 'Nonirrigated': 2}
STATES = {
    'IL': '17', 'AL': '01', 'AR': '05', 'FL': '12', 'GA': '13', 'IN': '18',
    'IA': '19', 'KS': '20', 'KY': '21', 'LA': '22', 'MD': '24', 'MI': '26',
    'MN': '27', 'MS': '28', 'MO': '29', 'NE': '31', 'NC': '37', 'ND': '38',
    'OH': '39', 'PA': '42', 'SC': '45', 'SD': '46', 'TN': '47', 'VA': '51',
    'WV': '54', 'WI': '55', 'OK': '40', 'TX': '48'}


def clean_benchmark_revenue(crop_year=2023):
    """
    Preparations:
    Open the file 'arcco_2023_data_2023-02-16.xlsx' in LibreCalc, delete all columns
    except ST_Cty, Crop Name, ARC-CO Yield Designation, and 2023 Benchmark Revenue.
    Delete header rows, format the benchmark revenue column as basic number without
    dollar sign or comma separator.  Then 'Save As' csv format with tab separator.
    """
    filename = f'{DATADIR}/benchmark_revenue_{crop_year}'
    with open(f'{filename}.csv', 'r') as f:
        contents = f.read()
    items = (line.split('\t') for line in contents.strip().split('\n'))
    crops = CROP.keys()
    states = STATES.values()
    result = {}
    for item in items:
        statecty = item[0]
        state = statecty[:2]
        cropname = item[1]
        if cropname in crops and state in states:
            crop = CROP[cropname]
            prac = ARC_PRAC[item[2]]
            rev = float(item[3])
            result[f'{statecty}{crop:d}{prac:d}'] = rev
    with open(f'{filename}.pkl', 'wb') as f:
        pickle.dump(result, f)


if __name__ == '__main__':
    clean_benchmark_revenue()
