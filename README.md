# Integrated_Farm_Budget_Tool

An integrated tool allowing midwest grain farmers to budget farm profitability and readily visualize outcomes sensitized to price and yield.

Based on farm specific inputs, this tool will assist an operator in 1) evaluating crop profitability and acreage allocation, 2) budgeting revenues reflective of already marketed and unmarketed grain, 3) assessing the implications of crop insurance alternatives, and 4) assessing the implications of title selection.  Farm operators can easily change any key inputs or assumptions to quickly test alternatives and visualize the holistic impact on their farm's budgeted profitability.   Furthermore, all the drivers of revenue, costs, crop insurance and title are sensitized to actual harvest price and yield.  Therefore an operator can readily visualize not only the implications of decisions on a static budget, but also the range of potential outomes of farm profitability dependant upon a range of possible actual harvest prices and yields.

The current implementation is just beginning development with a goal of verifying this Python codebase against Kelley's benchmarking.xlsx Excel workbook.  Once the logic has been validated and a detailed roadmap proposed, the plan is to build a publicly available web application, possibly in Django.  Having registered to use this application, an operator could enter/upload farm-specific data and then use the tool to evaluate various alternatives across various price and yield scenarios to both maximize profitability while also minimizing risks.

At this point, all the components (revenue, cost, gov_pmt, crop_ins, and cash_flow) are complete and reasonably well tested, but there is more refactoring and testing to do.

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
