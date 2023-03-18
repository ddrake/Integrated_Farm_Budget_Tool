"""
Script make_new_key

Three of the data files were quite large (~ 250MB), but contained many sets of rows with
distinct key codes, but identical data.  This script introduces new key files which
cross reference the original key to a new key, which is then used to key data in
the de-duplicated version of the file.
"""
import os

DATADIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../data')


def make_new_key(filename, prec=4, rest=None):
    """
    Step 1. Open file, get items.
    Step 2. Construct list1 of key/value pairs, where the value is a tuple
    Step 3. Sort list1 by value
    Step 4. zip(*list1) to get list2 of keys, list3 of tuple values
    Step 5. list4 = list(enumerate(set(list3)))
    Step 6. dict1 = {v, k for k, v in list4}
    Step 7. create new file f'{filename}1' from list4
    Step 8. list5 = [k, dict1[v] for k, v in list1]
    """
    if rest is None:
        rest = slice(1, None, None)
    with open(f'{DATADIR}/{filename}.txt', 'r') as f:
        contents = f.read()
    items = (line.split() for line in contents.strip().split('\n'))
    list1 = [(int(item[0]), tuple(float(itm) for itm in item[rest])) for item in items]
    list2, list3 = zip(*list1)
    list4 = list(enumerate(set(list3)))
    dict1 = {v: k for k, v in list4}
    list5 = [[k, dict1[v]] for k, v in list1]
    with open(f'{DATADIR}/{filename}1.txt', 'w') as f:
        f.write('\n'.join(f'{item[0]}\t' + '\t'.join((f'{itm:6.4f}' for itm in item[1]))
                for item in list4))
    with open(f'{DATADIR}/{filename}_key.txt', 'w') as f:
        f.write('\n'.join(('\t'.join((str(item[0]), str(item[1]))) for item in list5)))


if __name__ == '__main__':
    make_new_key('scoArp', rest=slice(2, None, None))
    make_new_key('scoArpw', rest=slice(2, None, None))
    make_new_key('eco')
