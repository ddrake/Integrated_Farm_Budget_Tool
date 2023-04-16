import os

"""
Get a table with all three-letter subcounty codes.
"""

# 01040 CoverageLevelDifferential, 01050 SubCountyRate
filecodes = ('01040 01050').split()


if __name__ == '__main__':
    files = [f for f in os.listdir('.')
             if os.path.isfile(f) and f.split('.')[1] == 'txt']
    filedict = {f.split('_')[1][1:]: f for f in files}
    allcodes = []
    for filecode in filecodes:
        file = filedict[filecode]
        print(f'processing {file}')
        with open(file, 'r') as f:
            contents = f.read()
        lines = [line.strip('\n').split('\t') for line in contents.strip().split('\n')]
        header = lines.pop(0)
        idx = header.index('Sub County Code')
        codes = [line[idx] for line in lines]
        allcodes += codes
    allcodes = sorted(list(set(allcodes)))
    allcodes = [code for code in allcodes if code != '']
    with open('SubCounty.txt', 'w') as f:
        f.write('\n'.join(['id'] + allcodes))
