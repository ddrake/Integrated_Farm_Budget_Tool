import os

"""
First pass takes dataflies from RMA set, convert to UTF-8 encoding, filter
out crops, types, practices, states, etc. that are not needed by the app.
Send results to an out subdirectory
After running this script, run the shell script 'move_unused.sh' to move unused
files to a subdirectory 'unused'
"""
# Note: empty strings are in each list because we don't want to filter rows if these
#  column values are missing.
states = {
    '17', '01', '05', '12', '13', '18', '19', '20', '21', '22', '24', '26',
    '27', '28', '29', '31', '37', '38', '39', '42', '45', '46', '47', '51',
    '54', '55', '40', '48', ''}
crops = {'0011', '0041', '0081', ''}
croptypes = {'011', '012', '016', '997', ''}
practices = {'053', '094', '043', '095', '003', '002', ''}
insplans = {'01', '02', '03', '04', '05', '06', '31', '32', '33', '87', '88', '89', ''}
countycoderemove = {'998', ''}
insoptcodes = {'HF', 'PF', ''}


def process_line(line, stcol, cmcol, tpcol, prcol, ipcol, ctcol, occol):
    line = ([item for item in items]
            if (stcol is None or items[stcol] in states)
            and (cmcol is None or items[cmcol] in crops)
            and (tpcol is None or items[tpcol] in croptypes)
            and (prcol is None or items[prcol] in practices)
            and (ipcol is None or items[ipcol] in insplans)
            and (ctcol is None or items[ctcol] not in countycoderemove)
            and (occol is None or items[occol] in insoptcodes) else None)
    return line


if __name__ == '__main__':
    files = [f for f in os.listdir('.')
             if os.path.isfile(f) and f.split('.')[1] == 'txt']
    for file in files:
        print(f'processing {file}')
        with open(file, 'r', encoding='Windows-1252') as f:
            f2 = open(f'out/{file}', 'w', encoding='UTF-8')
            i = 0
            for line in f:
                items = line.strip('\n').split('|')
                if i == 0:
                    print(items)
                    stcol = (items.index('State Code')
                             if 'State Code' in items else None)
                    cmcol = (items.index('Commodity Code')
                             if 'Commodity Code' in items else None)
                    tpcol = (items.index('Type Code')
                             if 'Type Code' in items else None)
                    prcol = (items.index('Practice Code')
                             if 'Practice Code' in items else None)
                    ipcol = (items.index('Insurance Plan Code')
                             if 'Insurance Plan Code' in items else None)
                    ctcol = (items.index('County Code')
                             if 'County Code' in items else None)
                    occol = (items.index('Insurance Option Code')
                             if 'Insurance Option Code' in items else None)
                    print('stcol', stcol, 'cmcol', cmcol, 'tpcol', tpcol,
                          'prcol', prcol, 'ipcol', ipcol,
                          'ctcol', ctcol, 'occol', occol)
                    linenew = items
                else:
                    linenew = process_line(line, stcol, cmcol, tpcol, prcol,
                                           ipcol, ctcol, occol)
                if linenew is not None:
                    linenew = '\t'.join(linenew) + '\n'
                    f2.write(linenew)
                i += 1
