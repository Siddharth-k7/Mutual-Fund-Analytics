"""Master execution script for the Bluestock mutual-fund capstone.

This entrypoint runs a raw-data smoke test first and then executes the ETL
load that builds the cleaned CSVs, SQLite database, and data dictionary.
"""

from __future__ import annotations

from data_ingestion import ingest_data
from day2_pipeline import main as build_warehouse
from load_processed import list_processed_files


def main() -> None:
    """Run the end-to-end local data pipeline."""

    raw_datasets = ingest_data()
    print(f"Preflight check: {len(raw_datasets)} raw datasets available.")
    build_warehouse()
    processed_files = list_processed_files()
    print(f"Processed outputs available: {len(processed_files)} CSV files.")


if __name__ == "__main__":
    main()
