"""
Module sensitivity

Generate a table of values from two sensitivity parameters
"""
from tabulate import tabulate

from cost import Cost
from gov_pmt import GovPmt
from revenue import Revenue
from crop_ins import CropIns

yield_pcts = "40 55 70 80 90 95 100 105".split()
price_pcts = "60 75 90 95 100 105 110 125 140 165 180".split()

yield_pct_labels = [p+'%' for p in yield_pcts]
price_pct_labels = [p+'%' for p in price_pcts]

yield_pcts = [int(p)/100 for p in yield_pcts]
price_pcts = [int(p)/100 for p in price_pcts]

ny = len(yield_pcts)


def setup_table(data, r, title):
    # add 3 empty rows for headers
    table = [['']*(3+ny)] + [['']*(3+ny)] + [['']*(3+ny)] + data

    # add header text
    table[0][0] = 'REVENUE'
    table[0][1] = 'Yield'
    table[1][0] = 'Price'
    table[0][2] = 'Corn'
    table[1][2] = 'Beans'
    table[2][0] = 'Corn'
    table[2][1] = 'Beans'
    table[2][2] = '%'

    # Row headers at left
    for i, p in enumerate(price_pcts):
        table[3+i][0] = round(p * r.fall_futures_price_corn, 2)
        table[3+i][1] = round(p * r.fall_futures_price_soy, 2)
        table[3+i][2] = price_pct_labels[i]

    # Column headers along top
    for i, p in enumerate(yield_pcts):
        table[0][3+i] = round(p * r.proj_yield_farm_corn, 1)
        table[1][3+i] = round(p * r.projected_yield_soy(), 1)
        table[2][3+i] = yield_pct_labels[i]

    return table


def sens_revenue(crop_year=2023):
    """
    Display a sensitivity table for the specified crop year
    for straightforward comparison with the revenue table
    in 'benchmarks.xls!KeyInputs'
    """
    r = Revenue(crop_year)

    data = [['']*3 + [round(r.total_revenue(p, y)/1000) for y in yield_pcts]
            for p in price_pcts]

    table = setup_table(data, r, 'REVENUE')

    print(tabulate(table, tablefmt="simple_grid"))


def sens_cost(crop_year=2023):
    """
    Display a sensitivity table for the specified crop year
    for straightforward comparison with the cost table
    in 'benchmarks.xls!KeyInputs'
    """
    r = Revenue(crop_year)
    c = Cost(crop_year)

    data = [['']*3 + [round(c.total_cost(y)/1000) for y in yield_pcts]
            for p in price_pcts]

    table = setup_table(data, r, 'COST')

    print(tabulate(table, tablefmt="simple_grid"))


def sens_gov_pmt(crop_year=2023):
    """
    Display a sensitivity table for the specified crop year
    for straightforward comparison with the cost table
    in 'benchmarks.xls!KeyInputs'
    """
    r = Revenue(crop_year)
    g = GovPmt(crop_year)

    data = [['']*3 + [round(g.total_gov_pmt(p, y)/1000) for y in yield_pcts]
            for p in price_pcts]

    table = setup_table(data, r, 'GOV_PMT')

    print(tabulate(table, tablefmt="simple_grid"))


def sens_crop_ins(crop_year=2023, overrides=None):
    """
    Display a sensitivity table for the specified crop year
    for straightforward comparison with the crop insurance table
    in 'benchmarks.xls!KeyInputs'
    """
    r = Revenue(crop_year)
    c = CropIns(crop_year, overrides)

    data = [['']*3 + [round(c.total_net_crop_ins_indemnity(p, y)/1000)
                      for y in yield_pcts]
            for p in price_pcts]

    table = setup_table(data, r, 'CROP_INS_NET_EXPENSE')

    print(tabulate(table, tablefmt="simple_grid"))
