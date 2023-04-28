# Integrated_Farm_Budget_Tool

An integrated tool allowing midwest grain farmers to budget farm profitability and readily visualize outcomes sensitized to price and yield.

Based on farm specific inputs, this tool will assist an operator in 1) evaluating crop profitability and acreage allocation, 2) budgeting revenues reflective of already marketed and unmarketed grain, 3) assessing the implications of crop insurance alternatives, and 4) assessing the implications of title selection.  Farm operators can easily change any key inputs or assumptions to quickly test alternatives and visualize the holistic impact on their farm's budgeted profitability.   Furthermore, all the drivers of revenue, costs, crop insurance and title are sensitized to actual harvest price and yield.  Therefore an operator can readily visualize not only the implications of decisions on a static budget, but also the range of potential outomes of farm profitability dependent upon a range of possible actual harvest prices and yields.

The application is designed to be used for budgetting for a crop year for the period between January 12 and June 30 of that crop year.  Decisions on crop insurance must be made in February or March, depending on the region, and decisions on Government title plan must be made in mid-March.  Grain marketing decisions.

The application will support common conventional crops: irrigated and non irrigated corn, winter wheat, spring wheat and soybeans, including soybeans following another crop (FAC).  It will support all counties in the following 33 states: AL, AR, CO, FL, GA, ID, IL, IN, IA, KS, KY, LA, MD, MI, MN, MO, MS, MT, NE, NC, ND, OH, OK, OR, PA, SC, SD, TN, VA, WA, WV, WI, TX.   Estimated premiums and indemnities are computed for both farm-based and county-based crop insurance (and optional policies SCO and ECO), but for simplicity, the farm-based crop-insurance products are limited to the Enterprise unit.  The PLC and ARC-CO government title programs will be supported. Users will need to specify the 'main county' for their operation and the 'main cropping practice' (irrigated or non-irrigated) for each of their crops.

The project is now in transition to a Django web application with a PostgreSQL database.  This application will allow a logged-in user to select from a set of preset budget models and customize it as needed, then enter their farm-specific data.  A new workbook 'simplebudgettool.xlsx' has been developed by Kelley as a model for the future user interface.  This is available on the collaborators' Google Drive in the IFBT folder.

The current implementation is entering the final phase of development.  The first phase was to develop a Python codebase, the logic of which could be validated against the sensitivity tables in Kelley's benchmarking.xlsx Excel workbook.  This is now complete and reasonably well-tested, and has been moved to a _benchmarking_ branch, which is now fairly stale.  Although this implementation computed the indemnity payments for crop insurance, it relied on a set of pre-computed premiums, not a feasible option, since premiums depend on the county and the farm history.

2023 RMA data files (21 GB) needed to compute premiums have now been analyzed, transformed and imported into a PostgreSQL database.  This process was complicated and time-consuming, but all structural changes and data operations were scripted in SQL, in an effort to streamline the process for future years.  The scripts and links to the RMA data set are available to collaborators on the Google Drive. 

## Prerequisites for local installation and testing 

- [Python 3.10 or above](https://www.python.org/) (If installing on Windows, check the box to add python to the path)
- [Windows Terminal](https://apps.microsoft.com/store/detail/windows-terminal/9N0DX20HK701) (This is optional, but highly recommended if you are running Windows.)
- [PostgreSQL/pgAdmin](https://www.postgresql.org/download/windows/)
- [pip (Python package manager)](https://pip.pypa.io/en/stable/installation/)
- [git version control](https://git-scm.com/downloads)
- You should also sign up for a free account at [Github](https://github.com) if you haven't got one.  Also, unless you really enjoy typing passwords, follow the steps [here](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account) to generate an SSH key pair and upload the public key to GitHub.
- [Django](https://numpy.org/) `pip install django`
- [psycopg2](https://numpy.org/) `pip install psycopg2`
- [NumPy](https://numpy.org/) `pip install numpy`
- [tabulate](https://pypi.org/project/tabulate/) `pip install tabulate`
- [IPython](https://ipython.org/) `pip install ipython`  (Not essential, but much better than the default Python console.
- A text editor or IDE of your choice.  [Notepad++](https://notepad-plus-plus.org/downloads/) should do just fine for a small project like this.  For more on this, see [this section](#recommendations-for-collaborators).

## Get the code

```
git clone https://github.com/ddrake/Integrated_Farm_Budget_Tool.git
```

Download the postgreSQL dump file from the Google Drive folder and restore it to your local database. There are more notes and instructions on Django and PostgreSQL in the Google Drive folder.  During the transition phase, you may still need to download the data directory to get the tests to pass.

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

To compute a single cell of the table (or test with arbitrary sensitivity factors): 

```
from ifbt import Revenue
r = Revenue(2023)

# 'pf' is price factor, 'yf' is yield factor
r.total_revenue(pf=.95, yf=1.05)
```

## Testing

- You will need pytest for now.  Install it via `pip install pytest`.
- To run all tests,

```
cd core/models 
pytest
```

- Note: many of the tests depend on the data text files, which take their values from a copy of the 'simpleBudgetTool.xlsx', which is available on the Collaborators' Google Drive IFBT folder.

- ## Project collaborators

- Kelley Drake
- Dow Drake
- Bennett Drake
- Varun Sadasivam
- Danny Huang
- Osanna Drake

## Recommendations for collaborators

I recommend we use [CodePen](https://codepen.io) for developing and presenting front end components.  It may be better to search for and integrate existing components or build from scratch.  Either approach is fine.

If you're unfamiliar with the Git version control system, a good place to start is this [tutorial](https://docs.github.com/en/get-started/quickstart/hello-world).

If you have an IDE you are already comfortable with, such as [PyCharm](https://www.jetbrains.com/pycharm/) or [VSCode](https://code.visualstudio.com/), that may be a good tool for testing this application and writing code to submit as pull requests.  However, if you are new to programming, you may find learning to use a heavy-weight IDE to be a time-consuming distraction from accomplishing your immediate goals.

In this case, you may prefer to use a simple [text editor](https://en.wikipedia.org/wiki/List_of_text_editors) in conjunction with a Python or Ipython console running in a terminal/command window.  Personally, this is the approach I prefer (I use the Vim editor with syntax-checking and highlighting from the flake8 package), but Vim has its own learning curve, and is probably not a good editor choice for a beginning programmer.

If you have some familiarity with Python, but want to get a deeper understanding, I highly recommend the book 'Fluent Python' by Luciano Ramalho.

In addition to the excellent Django tutorial and documentation at the Django site, there is another good tutorial at the [Mozilla Developers Network](https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django).
