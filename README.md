# Bluestock MF Capstone

End-to-end mutual-fund analytics project for the MFA workspace. The repository contains:

- A cleaned SQLite warehouse and processed CSV extracts
- A reusable ETL pipeline
- Exploratory analysis outputs and dashboard assets
- Final report and presentation deliverables

## Project Overview

The project analyzes mutual-fund scheme data across 10 public datasets to study:

- Retail investor participation
- SIP inflow growth and category rotation
- Fund-house AUM trends
- Performance, risk, alpha, and benchmark context

## Setup

1. Install Python 3.13 or newer.
2. Create a virtual environment if desired.
3. Install the project dependencies:

```bash
python -m pip install -r requirements.txt
```

If you want to regenerate the final report and presentation assets, also install:

```bash
python -m pip install reportlab PyMuPDF
```

## How to Run the ETL

Run the master pipeline from the `MFA` folder:

```bash
python run_pipeline.py
```

This will:

- Check the raw CSV inventory
- Clean and standardize the data
- Rebuild `bluestock_mf.db`
- Regenerate `data/processed/`
- Rewrite `schema.sql`, `queries.sql`, and `data_dictionary.md`

You can also run the ETL directly:

```bash
python day2_pipeline.py
```

## How to Open the Dashboard

The project dashboard is available as the local Power BI file:

```text
Mutual_Fund PowerBi.pbix
```

Open it in Power BI Desktop to inspect the report locally.

Optional publishing to Power BI Service or Tableau Public was not completed in this environment, so no hosted dashboard URL is available yet.

## Repository Layout

- `data/raw/` - original source files
- `data/processed/` - cleaned CSV outputs
- `data/db/` - local SQLite database, ignored by Git
- `notebooks/` - analysis notebooks
- `scripts/` - submission-facing ETL and utility entrypoints
- `sql/` - schema and query files
- `dashboard/` - Power BI dashboard file
- `reports/` - final PDF report and slide deck copies

## Final Deliverables

- `Final_Report.pdf`
- `Bluestock_MF_Presentation.pptx`
- `data/db/bluestock_mf.db`
- `data/processed/`

## Dataset Descriptions

- `01_fund_master.csv` - scheme master data, fund-house metadata, fees, and benchmarks
- `02_nav_history.csv` - daily NAV history with forward-filled calendar coverage
- `03_aum_by_fund_house.csv` - fund-house AUM trend
- `04_monthly_sip_inflows.csv` - SIP inflow and account growth trend
- `05_category_inflows.csv` - monthly category-level net inflows
- `06_industry_folio_count.csv` - industry folio counts by asset class
- `07_scheme_performance.csv` - returns, alpha, beta, volatility, and drawdown
- `08_investor_transactions.csv` - investor-level transaction behavior
- `09_portfolio_holdings.csv` - portfolio holdings and sector allocation
- `10_benchmark_indices.csv` - benchmark close series for comparison analysis

## Reproducibility Notes

- `run_pipeline.py` is the master entrypoint for local refreshes.
- `day2_pipeline.py` contains the warehouse cleaning and load logic.
- `recommender.py` returns scheme suggestions by risk appetite.
