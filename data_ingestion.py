"""Load the raw Bluestock mutual-fund CSV extracts.

The helper returns a dictionary of dataframes keyed by source file name so
analysis notebooks and pipeline steps can share a single ingestion path.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"

RAW_FILES = [
    "01_fund_master.csv",
    "02_nav_history.csv",
    "03_aum_by_fund_house.csv",
    "04_monthly_sip_inflows.csv",
    "05_category_inflows.csv",
    "06_industry_folio_count.csv",
    "07_scheme_performance.csv",
    "08_investor_transactions.csv",
    "09_portfolio_holdings.csv",
    "10_benchmark_indices.csv",
]


def ingest_data() -> dict[str, pd.DataFrame]:
    """Load each raw CSV into a dataframe keyed by file name."""

    datasets: dict[str, pd.DataFrame] = {}
    for file_name in RAW_FILES:
        path = RAW_DIR / file_name
        try:
            datasets[file_name] = pd.read_csv(path)
        except Exception as exc:
            print(f"Error loading {file_name}: {exc}")
    return datasets


def main() -> None:
    """Run a quick CLI smoke test for the raw dataset inventory."""

    datasets = ingest_data()
    print(f"Loaded {len(datasets)} raw datasets from {RAW_DIR}.")
    for name, df in datasets.items():
        print(f"{name}: {df.shape[0]} rows x {df.shape[1]} columns")


if __name__ == "__main__":
    main()
