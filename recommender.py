"""Simple mutual fund recommender based on risk appetite and Sharpe ratio."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "processed" / "07_scheme_performance.csv"

RISK_MAP = {
    "low": ["Low"],
    "moderate": ["Moderate", "Moderately High"],
    "high": ["High", "Very High"],
}


def recommend_funds(risk_appetite: str, top_n: int = 3) -> pd.DataFrame:
    risk_key = risk_appetite.strip().lower()
    if risk_key not in RISK_MAP:
        raise ValueError("risk_appetite must be one of: Low, Moderate, High")

    perf = pd.read_csv(DATA_PATH)
    eligible = perf[perf["risk_grade"].isin(RISK_MAP[risk_key])].copy()
    if eligible.empty:
        return eligible

    cols = [
        "scheme_name",
        "fund_house",
        "risk_grade",
        "sharpe_ratio",
        "return_3yr_pct",
        "return_1yr_pct",
        "aum_crore",
        "expense_ratio_pct",
    ]
    out = (
        eligible.sort_values(["sharpe_ratio", "aum_crore"], ascending=[False, False])
        .head(top_n)[cols]
        .reset_index(drop=True)
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Recommend funds by risk appetite.")
    parser.add_argument("--risk", help="Low, Moderate, or High")
    parser.add_argument("--top-n", type=int, default=3)
    args = parser.parse_args()

    risk = args.risk or input("Enter risk appetite (Low / Moderate / High): ").strip()
    recs = recommend_funds(risk, top_n=args.top_n)
    if recs.empty:
        print("No matching funds found.")
        return

    print(f"\nTop {len(recs)} recommendations for {risk.title()} risk appetite:\n")
    print(recs.to_string(index=False))


if __name__ == "__main__":
    main()
