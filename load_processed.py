"""Utilities to load processed CSVs from MFA/data/processed.

Provides:
  - `PROCESSED_DIR` path constant
  - `list_processed_files()` -> list[str]
  - `load_processed_csv(name, **pd.read_csv kwargs)` -> pd.DataFrame
  - `load_all_processed()` -> dict[name, DataFrame]

Usage:
    from load_processed import load_processed_csv
    fm = load_processed_csv("01_fund_master.csv", parse_dates=["launch_date"])
    nav = load_processed_csv("02_nav_history.csv", parse_dates=["date"])

The module expects the processed files under `MFA/data/processed/` (relative
to this file). It raises a clear FileNotFoundError if the folder is missing.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = ROOT / "data" / "processed"


def _ensure_dir() -> None:
    if not PROCESSED_DIR.exists():
        raise FileNotFoundError(
            f"Processed data directory not found: {PROCESSED_DIR!s}.\n"
            "Place the cleaned CSVs under MFA/data/processed/"
        )


def list_processed_files() -> List[str]:
    """Return sorted list of CSV file names in the processed directory."""
    _ensure_dir()
    return sorted([p.name for p in PROCESSED_DIR.glob("*.csv")])


def processed_path(name: str) -> Path:
    """Return a Path for a processed CSV given a file name or stem.

    Examples:
        processed_path('01_fund_master.csv')
        processed_path('01_fund_master')
    """
    _ensure_dir()
    p = Path(name)
    if p.suffix == "":
        p = p.with_suffix(".csv")
    return PROCESSED_DIR / p.name


def load_processed_csv(name: str, **read_csv_kwargs) -> pd.DataFrame:
    """Load a single processed CSV by name (or stem).

    Pass any `pandas.read_csv` kwargs (e.g. `parse_dates=[...]`).
    """
    path = processed_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Processed CSV not found: {path}")
    return pd.read_csv(path, **read_csv_kwargs)


def load_all_processed(names: Iterable[str] | None = None, **common_read_kwargs) -> Dict[str, pd.DataFrame]:
    """Load multiple processed CSVs.

    - If `names` is None, loads all CSVs found in the processed dir.
    - Returns a dict mapping file name (e.g. '01_fund_master.csv') -> DataFrame.
    - `common_read_kwargs` are forwarded to `pd.read_csv` for all files.
    """
    _ensure_dir()
    files = list_processed_files() if names is None else [
        (name if name.endswith(".csv") else f"{name}.csv") for name in names
    ]
    out: Dict[str, pd.DataFrame] = {}
    for fname in files:
        out[fname] = pd.read_csv(PROCESSED_DIR / fname, **common_read_kwargs)
    return out


__all__ = [
    "PROCESSED_DIR",
    "list_processed_files",
    "processed_path",
    "load_processed_csv",
    "load_all_processed",
]
