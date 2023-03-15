"""
Script check_keyPlength

Designed to handle certain textfiles that came from exporting improperly formatted
spreadsheet tabs where keys which should be int are exported as float yielding some
number of zeros after a decimal place.

After running this script to identify the issues, use visual block mode in vim and
do the replacement ':s/\.00//'
"""
from os import path
import sys

DATADIR = path.join(path.dirname(path.abspath(__file__)), '../data')


def checkmaxmin(textfilename):
    fname = f'{DATADIR}/{textfilename}.txt'
    print(f'checking {fname}')
    with open(fname, 'r') as f:
        contents = f.read()
    items = [line.split() for line in contents.strip().split('\n')]
    first = [item[0] for item in items]
    first_len = [len(item) for item in first]
    maxlen = max(first_len)
    minlen = min(first_len)
    print(f'minlen: {minlen}, maxlen: {maxlen}')
    print()


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print('Give me a list of textfile names to check')
    else:
        for fn in sys.argv[1:]:
            checkmaxmin(fn)
