# Integrated_Farm_Budget_Tool

An integrated tool allowing midwest grain farmers to budget farm profitability and readily visualize outcomes sensitized to price and yield.

Based on farm specific inputs, this tool will assist an operator in 1) evaluating crop profitability and acreage allocation, 2) budgeting revenues reflective of already marketed and unmarketed grain, 3) assessing the implications of crop insurance alternatives, and 4) assessing the implications of title selection.  Farm operators can easily change any key inputs or assumptions to quickly test alternatives and visualize the holistic impact on their farm's budgeted profitability.   Furthermore, all the drivers of revenue, costs, crop insurance and title are sensitized to actual harvest price and yield.  Therefore an operator can readily visualize not only the implications of decisions on a static budget, but also the range of potential outomes of farm profitability dependant upon a range of possible actual harvest prices and yields.

The current implementation is beginning the second phase of development.  The first phase was to devolop a Python codebase which could be validated against the sensitivity tables in Kelley's benchmarking.xlsx Excel workbook.  This is now complete and reasonably well-tested, and has been moved to a new _benchmarking_ branch for further testing.  Although this implementation can compute the indemnity payments for crop insurance, it relies on a set of pre-computed premiums, which is not a feasible option, since premiums depend on the county and the farm history.

The final phase will be to implement a more general version of this tool, as a Django application.  This application will allow a logged-in user to select from a set of preset budget models and customize it as needed, then enter their farm-specific data.  This application will treat wheat and FAC soybeans as first-class crops.  A new workbook 'simplebudgettool.xlsx' has been developed by Kelley as a model for this tool.

This new tool will replace the hard-coded crop insurance premiums in 'crop_ins_premiums.txt' file with premium computation logic and data sourced by the RMA (Risk Management Agency).  The computational logic has now been largely implemented, but we are working out how to source some of its data.  It will support irrigated and non irrigated corn, winter wheat and soybeans, including soybeans following another crop (FAC).  It will support all counties in the following 28 states: IL, AL, AR, FL, GA, IN, IA, KS, KY, LA, MD, MI, MN, MS, MO, NE, NC, ND, OH, PA, SC, SD, TN, VA, WV, WI, OK, TX.

Ideally we would like the application to support every legal crop insurance option.  However, for simplicity, we currently limit the Farm-based products to the Enterprise unit, assume that every user's farm operation is restricted to a single county, and that all acres for a crop adhere to the same practice (e.g. irrigated or non-irrigated).  There may be other implicit assumptions that will have to be dealt with in a production version of the code.

Django is flexible and powerful, and will be introduced soon, but we may save development time by fleshing out the model using a simple command-line interface, tabular display tools, and textfile vs. database storage before introducing the complexity of the framework.


## Prerequisites 

- [Python 3.10 or above](https://www.python.org/)
- [pip (Python package manager)](https://pip.pypa.io/en/stable/installation/)
- [git version control](https://git-scm.com/downloads)
- [tabulate](https://pypi.org/project/tabulate/) `pip install tabulate`

## Installation

The following steps install this tool locally as an 'editable' Python package: `ifbt`

```
git clone https://github.com/ddrake/Integrated_Farm_Budget_Tool.git
cd Integrated_Farm_Budget_Tool
pip install -e .
```

Download the data directory from the Google Drive folder corresponding to the branch you want to work with and place it inside ifbt/.  Note: The data on Google Drive contains only textfiles, which are compact, but slow to load.  The current implementation for crop insurance premiums on the main branch looks for data in pickle (.pkl) files.  If a pickle file is not found, the corresponding textfile is loaded, converted to a dict, and the dict saved to a pickle file.  Currently, 1.3 GB of drive space is required for data for the main branch.  The drive space required for the benchmarking branch data is less then 1 MB.

## Usage

In Python console or ipython console:

To see the revenue, cost, government payment and crop insurance sensitivity tables for 2023:

```
from sensitivity import (sens_revenue, sens_cost, sens_gov_pmt,
                         sens_crop_ins, sens_cash_flow)
sens_revenue(2023)
sens_cost(2023)
sens_gov_pmt(2023)
sens_crop_ins(2023)
sens_cash_flow(2023)
```

To compute a single cell of the table (or test wih arbitrary sensitivity factors): 

```
from ifbt import Revenue
r = Revenue(2023)

# 'pf' is price factor, 'yf' is yield factor
r.total_revenue(pf=.95, yf=1.05)
```

The module/sript `scenario_mgr` allows a user to evaluate net cash flow scenarios for a range of price and yield sensitivity factors and return the top 10 best legal configurations of farm program and crop insurance choices for each scenario.  Since there are 500,000 legal configurations and 88 scenarios, this script may take 10 hours or so to complete depending on your machine.  It uses minimal memory and only one CPU core.  To try this feature, run at a command prompt:

```
python3 ifbt/scenario_mgr.py
```

To get the top *n* best legal configurations for each scenario in the output file, call the script with that argument.  For example, the following usage writes the best 5 configurations for each scenario:

```
python3 ifbt/scenario_mgr.py 5
```

This script generates a tab-separated values file 'bestcases.txt', which can easily be imported into a spreadsheet or a Pandas dataset for further analysis.

Note that the "best legal configuration" depends on budget items, especially the proportion of contracted grain for each crop, and hence will generally be different for each user.  Also, it's not possible to use directly the results of this table to make farm program and crop insurance choices since knowledge of the harvest yields and prices is not available in the time frame when crop insurance can be purchased.

## Testing

- You will need pytest for now.  Install it via `pip install pytest`.
- To run all tests,

```
cd ifbt 
pytest
```

The test files are located in the directory `ifbt/tests` and will be found by pytest automatically.  If you get a message that pytest is not found, you may need to add the location of the pytest executable to your PATH.
- Note: many of the tests depend on the data text files, which take their values from a slightly modified copy of the 1/30/2023 'benchmarks.xslx' workbook.  If you are a collaborator and would like a copy of that workbook for testing purposes, please contact Dow.

## Project collaborators

- Kelley Drake
- Dow Drake
- Bennett Drake
- Varun Sadasivam
- Danny Huang

## Recommendations for collaborators

If you're unfamiliar with the Git version control system, a good place to start is this [tutorial](https://docs.github.com/en/get-started/quickstart/hello-world).

If you have an IDE you are already comfortable with, such as [PyCharm](https://www.jetbrains.com/pycharm/) or [VSCode](https://code.visualstudio.com/), that may be a good tool for testing this application and writing code to submit as pull requests.  However, if you are new to programming, you may find learning to use a heavy-weight IDE to be a time-consuming distraction from accomplishing your immediate goals.

In this case, you may prefer to use a simple [text editor](https://en.wikipedia.org/wiki/List_of_text_editors) in conjunction with a Python or Ipython console running in a terminal/command window.  Personally, this is the approach I prefer (I use the Vim editor with syntax-checking and highlighting from the flake8 package), but Vim has its own learning curve, and is probably not a good editor choice for a beginning programmer.

If you have some familiarity with Python, but want to get a deeper understanding, I highly recommend the book 'Fluent Python' by Luciano Ramalho.

In addition to the excellent Django tutorial and documentation at the Django site, there is another good tutorial at the [Mozilla Developers Network](https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django).
