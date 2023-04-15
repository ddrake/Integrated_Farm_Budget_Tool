"""
Script remove_unused_states_crops_croptypes

Remove items from combo premium data files which reference crops not in CROPS or
states not in STATES or croptypes not in CROPTYPES

Before running this script with new data, do the following steps:
1. unprotect the corresponding spreadsheet tab
2. move the tab to a new workbook
3. export as tab-separated values
4. delete the header row(s)

The files parameters.txt and counties.txt were processed using a text editor
"""
from os import path
from pathlib import Path
import shutil

STATES = set(
    {'IL': '17', 'AL': '1', 'AR': '5', 'FL': '12', 'GA': '13', 'IN': '18',
     'IA': '19', 'KS': '20', 'KY': '21', 'LA': '22', 'MD': '24', 'MI': '26',
     'MN': '27', 'MS': '28', 'MO': '29', 'NE': '31', 'NC': '37', 'ND': '38',
     'OH': '39', 'PA': '42', 'SC': '45', 'SD': '46', 'TN': '47', 'VA': '51',
     'WV': '54', 'WI': '55', 'OK': '40', 'TX': '48'}.values())

CROPS = set(
    {'Corn': '41', 'Soybeans': '81', 'Wheat': '11'}.values())

CROPTYPES = set({'Grain': '016', 'No crop specified': '997', 'Winter': '011'}.values())

# These have the standard integer code or ccode in the first column
FILES = ('options rates highRisk enterId betaid ' +
         'eco grp scoArp scoArpw scoYp').split()

# These have a one-digit risk level appended to the code with a decimal point
RISK_FILES = ('rateDiff prateDiff UnitFactor punitFactor enterpriseFactor ' +
              'penterpriseFactor enterFactorRev pEnterFactorRev').split()

# These have a two-digit pvol value appended to the code with a decimal point
REV_OPT_FILES = ('grip griphr').split()

BETA_FILES = 'draws'.split()
ENTER_FILES = 'discountEnter'.split()
OTHER_FILES = 'counties'.split()
DATADIR = path.join(path.dirname(path.abspath(__file__)), '../data')
Path(f'{DATADIR}/old').mkdir(exist_ok=True)
OLDDIR = f'{DATADIR}/old'


def filter_items_std(items):
    items = ([str(int(float(it[0])))] + it[1:] for it in items)
    return [it for it in items if it[0][:-11] in STATES and it[0][-8:-6] in CROPS
            and it[0][-6:-3] in CROPTYPES]


def filter_items_risk(items):
    items = ([f'{float(it[0]):.1f}'] + it[1:] for it in items)
    return [it for it in items if it[0][:-13] in STATES and it[0][-10:-8] in CROPS
            and it[0][-8:-5] in CROPTYPES]


def filter_items_rev_opt(items):
    items = ([f'{float(it[0]):.2f}'] + it[1:] for it in items)
    return [it for it in items if it[0][:-14] in STATES and it[0][-11:-9] in CROPS
            and it[0][-9:-6] in CROPTYPES]


def filter_items_counties(items):
    return [it for it in items if it[0] in STATES]


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
process_file_list(RISK_FILES, filter_items_risk)
process_file_list(REV_OPT_FILES, filter_items_rev_opt)
