# Integrated Farm Budget Tool (IFBT)

An integrated tool at [ifbt.farm](https://ifbt.farm) allowing midwest grain farmers to budget farm profitability and readily visualize outcomes sensitized to price and yield.

Based on farm-specific inputs, this tool assists an operator in 

1) evaluating crop profitability and acreage allocation, 
2) budgeting revenues reflective of already marketed and unmarketed grain,
3) assessing the implications of crop insurance alternatives, and
4) assessing the implications of title selection.

Farm operators can easily change any key inputs or assumptions to quickly test alternatives and visualize the holistic impact on their farm's budgeted profitability.   Furthermore, all the drivers of revenue, costs, crop insurance and title are sensitized to actual harvest price and yield.  Therefore an operator can readily visualize not only the implications of decisions on a static budget, but also the range of potential outomes of farm profitability dependent upon a range of possible actual harvest prices and yields.

The application is designed to be used for budgetting for a crop year for the period between January 12 (before spring planting) and July 1 of the following year when a final budget can be completed.  Decisions on crop insurance for spring-planted crops must typically be made in February or March, depending on the region, and decisions on Government title plan must be made in mid-March.  Grain marketing decisions can be made at any time.

The application supports common conventional crops: irrigated and non irrigated corn, winter wheat, spring wheat and soybeans, including soybeans following another crop (FAC) for U.S. counties in which some or all of those crops can be insured by the USDA Risk Management Agency.  See the [Wiki page on supported states and counties](https://github.com/ddrake/Integrated_Farm_Budget_Tool/wiki/Unsupported-states-and-counties) for details on which specific counties are supported.  Estimated premiums and indemnities are computed for both farm-based enterprise and county-based crop insurance (and optional county-level policies SCO and ECO).  Calculation of estimated PLC and ARC-CO title payments are performed over a range of yield and price scenarios.

See the [Wiki](https://github.com/ddrake/Integrated_Farm_Budget_Tool/wiki) for help on getting started quickly, as well as detailed information about the application's functionality.  The [Discussions](https://github.com/ddrake/Integrated_Farm_Budget_Tool/discussions) forum is a good place to get your questions answered.  If you encounter a bug or have ideas for new features, feel free to create an issue in [Issues](https://github.com/ddrake/Integrated_Farm_Budget_Tool/issues).  Screen-capture walkthrough videos are planned to be available before January 2024.

This application will be ready to use for the 2024 crop year by Jan 12, 2024.

## Prerequisites for local installation and testing (collaborators only)

This application relies on a PostgreSQL database pre-populated with data tables assembled from various public and government sources and includes logic in the form of views and user functions.  This database is not public at this time so local installation and (most) testing can be performed only by collaborators to this project.  Some prerequisites for local installation and testing are:

- [Python 3.10 or above](https://www.python.org/) (For Windows, check the box to add python to the path)
- [PostgreSQL/pgAdmin](https://www.postgresql.org/download/windows/)
- [git version control](https://git-scm.com/downloads)
- An account at [Github](https://github.com)
- [Django 4.2](https://numpy.org/) `pip install django`
- [psycopg2](https://numpy.org/) `pip install psycopg2`
- [NumPy](https://numpy.org/) `pip install numpy`
- A text editor or IDE of your choice.
- Other resources, including a local/test database, are available to collaborators in the IFBT Google Drive folder

## Get the source code

```
git clone https://github.com/ddrake/Integrated_Farm_Budget_Tool.git
```

## Project collaborators

- Kelley Drake
- Dow Drake
- Bennett Drake
- Varun Sadasivam
- Danny Huang
- Osanna Drake
