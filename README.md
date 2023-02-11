# Integrated_Farm_Budget_Tool

An integrated tool allowing midwest grain farmers to budget farm profitability and readily visualize outcomes sensitized to price and yield.

Based on farm specific inputs, this tool will assist an operator in 1) evaluating crop profitability and acreage allocation, 2) budgeting revenues reflective of already marketed and unmarketed grain, 3) assessing the implications of crop insurance alternatives, and 4) assessing the implications of title selection.  Farm operators can easily change any key inputs or assumptions to quickly test alternatives and visualize the holistic impact on their farm's budgeted profitability.   Furthermore, all the drivers of revenue, costs, crop insurance and title are sensitized to actual harvest price and yield.  Therefore an operator can readily visualize not only the implications of decisions on a static budget, but also the range of potential outomes of farm profitability dependant upon a range of possible actual harvest prices and yields.

The current implementation is beginning the second phase of development.  The first phase was to devolop a Python codebase which could be validated against the sensitivity tables in Kelley's benchmarking.xlsx Excel workbook.  This is now complete and reasonably well-tested.

The next phase will be to implement on a different branch, a more general version of this tool, which will allow a user to select from a set of preset cost/revenue models and enter crop acres.  A user will be able to override many cost and revenue items with her own farm's data.  It will treat wheat and FAC soybeans as first-class crops.  A new workbook 'simplebudgettool.xlsx' is currently being developed by Kelley.

Once finalized, it will be coded in Python and serve as the core business logic component of the third phase, a Django application to be built this summer.  Having registered to use this application, an operator could enter/upload farm-specific data and then use the tool to evaluate various alternatives across various price and yield scenarios to both maximize profitability while also minimizing risks.

## Prerequisites 

- [Python 3.10 or above](https://www.python.org/)
- [pip (Python package manager)](https://pip.pypa.io/en/stable/installation/)
- [git version control](https://git-scm.com/downloads)
- [tabulate](https://pypi.org/project/tabulate/) `pip install tabulate`

## Installation

`git clone https://github.com/ddrake/Integrated_Farm_Budget_Tool.git`

## Usage

In Python console or ipython console:

To see the revenue, cost, gov_pmt and crp_ins sensitivity tables for 2023:

```
from sensitivity import (sens_revenue, sens_cost, sens_gov_pmt,
                         sens_crp_ins, sens_cash_flow)
sens_revenue(2023)
sens_cost(2023)
sens_gov_pmt(2023)
sens_crp_ins(2023)
sens_cash_flow(2023)
```

To compute a single cell of the table (or test wih arbitrary sensitivity factors): 

```
from revenue import Revenue
r = Revenue(2023)

# 'pf' is price factor, 'yf' is yield factor
r.total_revenue(pf=.95, yf=1.05)
```

There is a new experimental feature in module/sript `scenario_mgr` that allows a user to evaluate net cash flow scenarios for a range of price and yield sensitivity factors and return the top 10 best legal configurations of farm program and crop insurance choices for a given scenario.  This script may take 10 hours or so to complete depending on your machine, but does not use much memory or CPU resources.  To try this feature, run at a command prompt:

```
python3 scenario_mgr.py
```

This script generates a tab-separated values file 'bestcases.txt', which can easily be imported into a spreadsheet for further analysis.

## Testing

- You will need pytest for now.  Install it via `pip install pytest`.
- To run all tests, open a terminal in the project directory and enter `pytest`; the test files will be found automatically.  If you get a message that pytest is not found, you may need to add the location of the pytest executable to your PATH.
- Note: many of the tests depend on the data text files, which take their values from a slightly modified copy of the 1/30/2023 'benchmarks.xslx' workbook.  If you are a collaborator and would like a copy of that workbook for testing purposes, please contact Dow.

## Project collaborators

- Kelley Drake
- Dow Drake
- Bennett Drake
- Varun Sadasivam
- Danny Huang
