"""
Script remove_unused_states_crops

Remove items from combo premium data files which reference crops not in CROPS or
states not in STATES

Before running this script with new data, do the following steps:
1. unprotect the corresponding spreadsheet tab
2. move the tab to a new workbook
3. export as tab-separated values
4. delete the header row(s)
5. for some tabs, additional processing may be needed.
"""
from os import path
from pathlib import Path
import shutil


STATES = set(
    {'IL': '17', 'AL': '01', 'AR': '05', 'FL': '12', 'GA': '13', 'IN': '18',
     'IA': '19', 'KS': '20', 'KY': '21', 'LA': '22', 'MD': '24', 'MI': '26',
     'MN': '27', 'MS': '28', 'MO': '29', 'NE': '31', 'NC': '37', 'ND': '38',
     'OH': '39', 'PA': '41', 'SC': '45', 'SD': '46', 'TN': '47', 'VA': '51',
     'WV': '54', 'WI': '55', 'OK': '40', 'TX': '48'}.values())

CROPS = set(
    {'Corn': '41', 'Soybeans': '81', 'Wheat': '11'}.values())

FILES = ('options rates rateDiff prateDiff UnitFactor punitFactor enterpriseFactor ' +
         'penterpriseFactor enterFactorRev pEnterFactorRev highRisk enterId betaid ' +
         'eco grip griphr grp scoArp scoArpw scoYp').split()

BETA_FILES = 'draws'.split()
ENTER_FILES = 'discountEnter'.split()
OTHER_FILES = 'counties'.split()
DATADIR = path.join(path.dirname(path.abspath(__file__)), '../data')
Path(f'{DATADIR}/old').mkdir(exist_ok=True)
OLDDIR = f'{DATADIR}/old'


def filter_items_std(items):
    return [it for it in items if it[0][:2] in STATES and it[0][5:7] in CROPS]


def filter_items_counties(items):
    return [it for it in items if f'{int(it[0]):02d}' in STATES]


def filter_items_beta(items):
    with open(f'{DATADIR}/betaid.txt', 'r') as f:
        contents = f.read()
    bitems = (line.strip().split() for line in contents.strip().split('\n'))
    betas = set(it[1] for it in bitems)
    return [it for it in items if it[0] in betas]


def filter_items_enter(items):
    with open(f'{DATADIR}/enterId.txt', 'r') as f:
        contents = f.read()
    eitems = (line.strip().split() for line in contents.strip().split('\n'))
    enters = set(it[1] for it in eitems)
    return [it for it in items if it[0] in enters]


def process_file_list(files, processor):
    for file in files:
        src = f'{DATADIR}/{file}.txt'
        dest = f'{OLDDIR}/{file}.txt'
        shutil.copy(src, dest)
        with open(src, 'r') as f:
            contents = f.read()
            items = [line.strip().split() for line in contents.strip().split('\n')]
            print(f'Orig file {file} has {len(items)} lines')
            print('first code is', items[0][0])
            items = processor(items)
            print(f'New file {file} has {len(items)} lines')
            contents = '\n'.join('\t'.join(it) for it in items)
        with open(f'{DATADIR}/{file}.txt', 'w') as f:
            f.write(contents)


process_file_list(FILES, filter_items_std)
process_file_list(OTHER_FILES, filter_items_counties)
process_file_list(BETA_FILES, filter_items_beta)
process_file_list(ENTER_FILES, filter_items_enter)
