import os

"""
Third pass, reorder columns for some files.  This is needed because Django always
reorders columns to place foreign key fields last (in alphabetical order
if more than 1).  Save results to an out subdirectory
"""

filecodes = ('00030 00070 00440 00510 00540 01010 ' +
             '01030 01040 01050 01060 01130').split()
ordrcols = [
            # 00030 InsuranceOffer
            ['ADM Insurance Offer ID', 'County Code', 'Beta ID',
             'Unit Discount ID', 'Practice Code', 'Commodity Code', 'Type Code',
             'Insurance Plan Code', 'State Code'],
            # 00070 SubsidyPercent
            ['Unit Structure Code', 'Coverage Level Percent',
             'Subsidy Percent', 'Commodity Code', 'Coverage Type Code',
             'Insurance Plan Code'],
            # 00440 County
            ['County Code', 'County Name', 'State Code'],
            # 00510 Practice
            ['Practice Code', 'Practice Name', 'Commodity Code'],
            # 00540 Type
            ['Type Code', 'Type Name', 'Type Abbreviation', 'Commodity Code'],
            # 01010 BaseRate
            ['County Code', 'Coverage Level Percent',
             'Reference Rate', 'Exponent Value', 'Fixed Rate',
             'Prior Year Reference Rate', 'Prior Year Exponent Value',
             'Prior Year Fixed Rate', 'Practice Code', 'Commodity Code',
             'Type Code', 'Insurance Plan Code', 'State Code',],
            # 01030 ComboRevenueFactor
            ['Base Rate', 'Standard Deviation Quantity',
             'Mean Quantity', 'Commodity Code', 'State Code'],
            # 01040 CoverageLevelDifferential
            ['County Code', 'Coverage Level Percent',
             'Rate Differential Factor', 'Enterprise Unit Residual Factor',
             'Prior Year Rate Differential Factor',
             'Prior Year Enterprise Unit Residual Factor', 'Practice Code',
             'Commodity Code', 'Type Code', 'Coverage Type Code', 'Insurance Plan Code',
             'State Code', 'Sub County Code'],
            # 01050 SubCountyRate
            ['County Code', 'Sub County Rate', 'Practice Code', 'Commodity Code',
             'Type Code', 'Insurance Plan Code', 'Rate Method Code',
             'State Code', 'Sub County Code'],
            # 01060 OptionRate
            ['County Code', 'Option Rate', 'Practice Code',
             'Commodity Code', 'Type Code', 'Insurance Option Code',
             'Insurance Plan Code', 'State Code'],
            # 01130 AreaCoverageLevel
            ['Coverage Level Percent', 'Area Rate ID',
             'ADM Insurance Offer ID'],
            ]


if __name__ == '__main__':
    files = [f for f in os.listdir('.')
             if os.path.isfile(f) and f.split('.')[1] == 'txt']
    filedict = {f.split('_')[1][1:]: f for f in files}
    for filecode, cols in zip(filecodes, ordrcols):
        file = filedict[filecode]
        print(f'processing {file}')
        with open(file, 'r') as f:
            f2 = open(f'out/{file}', 'w')
            i = 0
            idxs = None
            for line in f:
                # Don't strip the line, could be trailing tabs
                line = line.strip('\n').split('\t')
                if i == 0:
                    idxs = [line.index(c) for c in cols]
                linestr = '\t'.join(((line[i] if i < len(line) else '')
                                     for i in idxs)) + '\n'
                f2.write(linestr)
                i += 1
            f2.close()
