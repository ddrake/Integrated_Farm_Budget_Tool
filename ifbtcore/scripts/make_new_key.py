"""
Script make_new_key

Run this script AFTER running remove_unused_states_crops.py on the exported data
with column heads removed.

This script performs 3 operations:
1. It removes duplicate rows by introducing a new intermediate key.
2. It removes columns which are unused by the application
3. It changes float keys to int by simply removing the decimal point.

Deduplication provides two benefits: it reduces storage requirements and it
makes the data more transparent.
"""
import os

DATADIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../data')


def make_new_key(filename, prec=4, rest=None):
    """
    Step 1. Open file, get items.
    Step 2. Construct list1 of key/value pairs, where the value is a tuple
    Step 3. zip(*list1) to get list2 of tuple values
    Step 4. list3 = list(enumerate(set(list2)))
    Step 5. dict1 = {v, k for k, v in list3}
    Step 6. create new file f'{filename}1' from list3
    Step 7. list4 = [k, dict1[v] for k, v in list1]
    Step 8. create new file f'{filename}_key' from list4
    """
    if rest is None:
        rest = slice(1, None, None)
    with open(f'{DATADIR}/{filename}.txt', 'r') as f:
        contents = f.read()

    items = (line.split() for line in contents.strip().split('\n'))
    list1 = [(int(''.join(item[0].split('.'))), tuple(float(itm) for itm in item[rest]))
             for item in items]
    print(f'Original file has {len(list1)} items')

    _, list2 = zip(*list1)
    list3 = list(enumerate(set(list2)))
    print(f'Deduplicated file has {len(list3)} items')

    dict1 = {v: k for k, v in list3}
    list4 = [[k, dict1[v]] for k, v in list1]

    # keep plenty of decimal places, but remove trailing zeros, decimal point.
    with open(f'{DATADIR}/{filename}1.txt', 'w') as f:
        f.write('\n'.join(f'{item[0]}\t' +
                          '\t'.join((f'{itm:.9f}'.rstrip('0').rstrip('.')
                                     for itm in item[1]))
                for item in list3))
    with open(f'{DATADIR}/{filename}_key.txt', 'w') as f:
        f.write('\n'.join(('\t'.join((str(item[0]), str(item[1]))) for item in list4)))


if __name__ == '__main__':
    make_new_key('scoArp', rest=slice(2, None, None))
    make_new_key('scoArpw', rest=slice(2, None, None))
    make_new_key('eco')
    make_new_key('scoYp', rest=slice(2, None, None))
    make_new_key('enterFactorRev')
    make_new_key('enterpriseFactor')
    make_new_key('griphr')
    make_new_key('grip')
    make_new_key('grp')
    make_new_key('options', rest=slice(1, 4, None))
    make_new_key('pEnterFactorRev')
    make_new_key('penterpriseFactor')
    make_new_key('prateDiff')
    make_new_key('rateDiff')
    make_new_key('rates')
