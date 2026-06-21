"""Utilities for reading cleaned CSVs from `MFA/data/processed/`.

The helpers keep notebook and ad-hoc analysis code consistent by centralizing
path resolution and file existence checks.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = ROOT / "data" / "processed"


def _ensure_dir() -> None:
    """Raise a clear error when the processed directory is missing."""

    if not PROCESSED_DIR.exists():
        raise FileNotFoundError(
            f"Processed data directory not found: {PROCESSED_DIR!s}.\n"
            "Place the cleaned CSVs under MFA/data/processed/"
        )


def list_processed_files() -> list[str]:
    """Return the sorted CSV inventory from the processed directory."""

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


def load_all_processed(names: Iterable[str] | None = None, **common_read_kwargs) -> dict[str, pd.DataFrame]:
    """Load multiple processed CSVs.

    - If `names` is None, loads all CSVs found in the processed dir.
    - Returns a dict mapping file name (e.g. '01_fund_master.csv') -> DataFrame.
    - `common_read_kwargs` are forwarded to `pd.read_csv` for all files.
    """
    _ensure_dir()
    files = list_processed_files() if names is None else [
        (name if name.endswith(".csv") else f"{name}.csv") for name in names
    ]
    out: dict[str, pd.DataFrame] = {}
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
