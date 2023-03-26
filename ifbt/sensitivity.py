"""
Module sensitivity

Generate a table of values from two sensitivity parameters
"""
from tabulate import tabulate

from ifbt import Crop, Cost, GovPmt, Revenue, CropIns, CashFlow, Premium

prem = Premium()


yield_pcts = "40 55 70 80 90 95 100 105".split()
price_pcts = "60 75 90 95 100 105 110 125 140 165 180".split()

yield_pct_labels = [p+'%' for p in yield_pcts]
price_pct_labels = [p+'%' for p in price_pcts]

yield_pcts = [int(p)/100 for p in yield_pcts]
price_pcts = [int(p)/100 for p in price_pcts]

ny = len(yield_pcts)


def show_table(r, method, title, takes_pf=True):
    """
    Given a model instance, a method to call and a title, Show a sensitivity
    table by passing a range of yield and price factors to the given method.
    The optional argument is used to handle the case of the total_cost
    method, which takes only a yield factor.
    """
    data = [['']*3 +
            [round((method(pf=p, yf=y) if takes_pf else method(yf=y))/1000)
             for y in yield_pcts] for p in price_pcts]

    # add 3 empty rows for headers
    table = [['']*(3+ny) for i in range(3)] + data

    # add header text
    table[0][0] = title
    table[0][1] = 'Yield'
    table[1][0] = 'Price'
    table[0][2] = 'Corn'
    table[1][2] = 'Beans'
    table[2][0] = 'Corn'
    table[2][1] = 'Beans'
    table[2][2] = '%'

    # Row headers at left
    for i, p in enumerate(price_pcts):
        table[3+i][0] = round(p * r.fall_futures_price[Crop.CORN], 2)
        table[3+i][1] = round(p * r.fall_futures_price[Crop.SOY], 2)
        table[3+i][2] = price_pct_labels[i]

    # Column headers along top
    for i, p in enumerate(yield_pcts):
        table[0][3+i] = round(p * r.projected_yield_crop(Crop.CORN), 1)
        table[1][3+i] = round(p * r.projected_yield_crop(Crop.SOY), 1)
        table[2][3+i] = yield_pct_labels[i]

    print(tabulate(table, tablefmt="simple_grid"))


def sens_revenue(crop_year, overrides=None):
    """
    Display a revenue sensitivity table for the specified crop year
    Optionally override some textfile settings by passing a dict.
    """
    r = Revenue(crop_year, overrides=overrides)
    show_table(r, r.total_revenue, 'REVENUE')


def sens_cost(crop_year, overrides=None):
    """
    Display a cost sensitivity table for the specified crop year
    Optionally override some textfile settings by passing a dict.
    """
    c = Cost(crop_year, overrides=overrides)
    show_table(c, c.total_cost, 'COST', takes_pf=False)


def sens_gov_pmt(crop_year, overrides=None):
    """
    Display a government payment sensitivity table for the specified crop year
    Optionally override some textfile settings by passing a dict.
    """
    g = GovPmt(crop_year, overrides=overrides)
    show_table(g, g.total_gov_pmt, 'GOV_PMT')


def sens_crop_ins(crop_year, overrides=None):
    """
    Display a crop insurance sensitivity table for the specified crop year
    Optionally override some textfile settings by passing a dict.
    """
    c = CropIns(crop_year, overrides=overrides, prem=prem)
    show_table(c, c.total_net_indemnity, 'CROP INS REV')


def sens_cash_flow(crop_year, overrides=None):
    """
    Display a cash flow sensitivity table for the specified crop year
    Optionally override some textfile settings by passing a dict.
    """
    c = CashFlow(crop_year, overrides=overrides, prem=prem)
    show_table(c, c.total_cash_flow, 'CASH FLOW')
