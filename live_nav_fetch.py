"""Fetch and store raw NAV history snapshots from mfapi.in."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
SCHEME_CODES = [125497, 119551, 120503, 118632, 119092, 120841]


def fetch_and_save(code: int, session: requests.Session | None = None) -> Path:
    """Fetch one scheme's history and persist it under `data/raw/`."""

    http = session or requests.Session()
    url = f"https://api.mfapi.in/mf/{code}"
    response = http.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()
    df = pd.DataFrame(data["data"])
    df["amfi_code"] = code

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DIR / f"nav_{code}.csv"
    df.to_csv(output_path, index=False)
    return output_path


def fetch_many(codes: Iterable[int] = SCHEME_CODES) -> list[Path]:
    """Fetch multiple scheme histories and return the created file paths."""

    outputs: list[Path] = []
    with requests.Session() as session:
        for code in codes:
            outputs.append(fetch_and_save(code, session=session))
    return outputs


def main() -> None:
    """CLI entry point for refreshing the local NAV snapshots."""

    outputs = fetch_many()
    for path in outputs:
        print(f"Saved NAV data to {path}")


if __name__ == "__main__":
    main()
