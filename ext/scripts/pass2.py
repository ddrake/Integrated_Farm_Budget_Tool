import os

"""
Befor running this script, run the shell script 'move_unused.sh' to move unused
files to a subdirectory 'unused'
Second pass, keep only the listed columns for the given files
Send results to an out subdirectory
"""
filecodes = ('00030 00070 00200 00420 00440 00460 00510 00520 00540 ' +
             '00570 00580 00810 01010 01020 01030 01040 01050 01060 ' +
             '01090 01100 01135 01130').split()
keepcols = [
            # 00030 InsuranceOffer
            ['ADM Insurance Offer ID', 'Commodity Code',
             'Insurance Plan Code', 'State Code', 'County Code', 'Type Code',
             'Practice Code', 'Beta ID', 'Unit Discount ID'],
            # 00070 SubsidyPercent
            ['Commodity Code', 'Unit Structure Code',
             'Insurance Plan Code', 'Coverage Level Percent',
             'Coverage Type Code', 'Subsidy Percent'],
            # 00200 Date
            ['Commodity Code', 'Insurance Plan Code',
             'State Code', 'County Code', 'Sub County Code', 'Type Code',
             'Practice Code', 'Contract Change Date',
             'Sales Closing Date', 'Modified Sales Closing Date',
             'Extednded Sales Closing Date', 'Earliest Planting Date',
             'Final Planting Date', 'Extended Final Planting Date',
             'Acreage Reporting Date', 'Modified Acreage Reporting Date',
             'End Of Insurance Date', 'Cancellation Date',
             'Modified Cancellation Date', 'Termination Date', 'Premium Billing Date',
             'Production Reporting Date', 'Modified Production Reporting Date',
             'End of Late Planting Period Date', 'Sales Period Begin Date',
             'Sales Period End Date', 'Insurance Attachment Date',
             'Commodity Reporting Date', 'Modified Commodity Reporting Date',
             'Last Released Date', 'Released Date', 'Deleted Date', 'Filing Date'],
            # 00420 Commodity
            ['Commodity Code', 'Commodity Name'],
            # 00440 County
            ['State Code', 'County Code', 'County Name'],
            # 00460 InsurancePlan
            ['Insurance Plan Code', 'Insurance Plan Name',
             'Insurance Plan Abbreviation'],
            # 00510 Practice
            ['Commodity Code', 'Practice Code', 'Practice Name'],
            # 00520 State
            ['State Code', 'State Name', 'State Abbreviation'],
            # 00540 Type
            ['Commodity Code', 'Type Code', 'Type Name', 'Type Abbreviation'],
            # 00570 InsuranceOption
            ['Insurance Option Code', 'Insurance Option Name'],
            # 00580 RateMethod
            ['Rate Method Code', 'Rate Method Description'],
            # 00810 Price
            ['Commodity Code', 'Insurance Plan Code', 'State Code',
             'County Code', 'Type Code', 'Practice Code', 'Catastrophic Price',
             'Projected Price', 'Price Volatility Factor', 'Expected Index Value',
             'Expected Revenue Amount'],
            # 01010 BaseRate
            ['Commodity Code', 'Insurance Plan Code', 'State Code',
             'County Code', 'Type Code', 'Practice Code', 'Coverage Level Percent',
             'Reference Rate', 'Exponent Value', 'Fixed Rate',
             'Prior Year Reference Rate', 'Prior Year Exponent Value',
             'Prior Year Fixed Rate'],
            # 01020 Beta
            ['Beta ID', 'Yield Draw Quantity', 'Price Draw Quantity'],
            # 01030 ComboRevenueFactor
            ['Commodity Code', 'State Code', 'Base Rate',
             'Mean Quantity', 'Standard Deviation Quantity'],
            # 01040 CoverageLevelDifferential
            ['Commodity Code', 'Insurance Plan Code', 'State Code',
             'County Code', 'Sub County Code', 'Type Code', 'Practice Code',
             'Coverage Level Percent', 'Coverage Type Code', 'Rate Differential Factor',
             'Enterprise Unit Residual Factor', 'Prior Year Rate Differential Factor',
             'Prior Year Enterprise Unit Residual Factor'],
            # 01050 SubCountyRate
            ['Commodity Code', 'Insurance Plan Code', 'State Code',
             'County Code', 'Sub County Code', 'Type Code', 'Practice Code',
             'Sub County Rate', 'Rate Method Code'],
            # 01060 OptionRate
            ['Commodity Code', 'Insurance Plan Code', 'State Code',
             'County Code', 'Type Code', 'Practice Code', 'Insurance Option Code',
             'Option Rate'],
            # 01090 UnitDiscount
            ['Unit Discount ID', 'Coverage Level Percent',
             'Area Low Quantity', 'Area High Quantity',
             'Enterprise Unit Discount Factor'],
            # 01100 YieldAndTYield
            ['Commodity Code', 'Insurance Plan Code', 'State Code',
             'County Code', 'Type Code', 'Practice Code', 'Prior Commodity Year',
             'Transitional Amount', 'Prior Transitional Amount'],
            # 01135 AreaRate
            ['Area Rate ID', 'Price Volatility Factor',
             'Base Rate'],
            # 01130 AreaCoverageLevel
            ['ADM Insurance Offer ID',
             'Coverage Level Percent', 'Area Rate ID']
            ]


if __name__ == '__main__':
    files = [f for f in os.listdir('.')
             if os.path.isfile(f) and f.split('.')[1] == 'txt']
    filedict = {f.split('_')[1][1:]: f for f in files}
    for filecode, cols in zip(filecodes, keepcols):
        file = filedict[filecode]
        print(f'processing {file}')
        with open(file, 'r') as f:
            f2 = open(f'out/{file}', 'w')
            i = 0
            idxs = None
            for line in f:
                line = line.strip('\n').split('\t')
                if i == 0:
                    header_keep = [(i, item) for i, item in enumerate(line)
                                   if item in cols]
                    idxs, header = zip(*header_keep)
                    linestr = '\t'.join(header) + '\n'
                else:
                    linestr = '\t'.join((line[j] for j in idxs)) + '\n'
                f2.write(linestr)
                i += 1
            f2.close()
