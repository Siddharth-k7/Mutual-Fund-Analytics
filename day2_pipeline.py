from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
DB_PATH = ROOT / "bluestock_mf.db"
SCHEMA_PATH = ROOT / "schema.sql"
QUERIES_PATH = ROOT / "queries.sql"
DICTIONARY_PATH = ROOT / "data_dictionary.md"

RETURN_COLUMNS = [
    "return_1yr_pct",
    "return_3yr_pct",
    "return_5yr_pct",
    "benchmark_3yr_pct",
    "alpha",
    "beta",
    "sharpe_ratio",
    "sortino_ratio",
    "std_dev_ann_pct",
    "max_drawdown_pct",
]
KYC_STATUSES = {"Verified", "Pending", "Rejected"}
TRANSACTION_TYPES = {
    "sip": "SIP",
    "systematic investment plan": "SIP",
    "lumpsum": "Lumpsum",
    "lump sum": "Lumpsum",
    "redemption": "Redemption",
    "redeem": "Redemption",
}


def date_key(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.strftime("%Y%m%d").astype("int64")


def clean_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    for column in df.select_dtypes(include=["object", "string"]).columns:
        df[column] = df[column].astype("string").str.strip()
    return df


def read_csv(name: str) -> pd.DataFrame:
    return clean_string_columns(pd.read_csv(RAW_DIR / name))


def clean_fund_master() -> pd.DataFrame:
    df = read_csv("01_fund_master.csv")
    df["amfi_code"] = pd.to_numeric(df["amfi_code"], errors="raise").astype("int64")
    df["launch_date"] = pd.to_datetime(df["launch_date"], errors="raise").dt.date.astype("string")
    numeric_columns = [
        "expense_ratio_pct",
        "exit_load_pct",
        "min_sip_amount",
        "min_lumpsum_amount",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="raise")
    df = df.drop_duplicates(subset=["amfi_code"], keep="last").sort_values("amfi_code")
    if not df["expense_ratio_pct"].between(0.1, 2.5).all():
        raise ValueError("Fund master expense_ratio_pct outside 0.1%-2.5%.")
    return df.reset_index(drop=True)


def clean_nav_history() -> pd.DataFrame:
    df = read_csv("02_nav_history.csv")
    df["amfi_code"] = pd.to_numeric(df["amfi_code"], errors="raise").astype("int64")
    df["date"] = pd.to_datetime(df["date"], errors="raise")
    df["nav"] = pd.to_numeric(df["nav"], errors="raise")
    df = df[df["nav"] > 0].drop_duplicates(subset=["amfi_code", "date"], keep="last")
    filled_frames = []
    for amfi_code, fund_nav in df.sort_values(["amfi_code", "date"]).groupby("amfi_code"):
        fund_nav = fund_nav.set_index("date").sort_index()
        daily_index = pd.date_range(fund_nav.index.min(), fund_nav.index.max(), freq="D")
        filled = fund_nav.reindex(daily_index)
        filled["amfi_code"] = amfi_code
        filled["is_forward_filled"] = filled["nav"].isna()
        filled["nav"] = filled["nav"].ffill()
        filled.index.name = "date"
        filled_frames.append(filled.reset_index())
    out = pd.concat(filled_frames, ignore_index=True)
    out["date_key"] = date_key(out["date"])
    out["date"] = out["date"].dt.date.astype("string")
    out = out[["amfi_code", "date", "date_key", "nav", "is_forward_filled"]]
    if (out["nav"] <= 0).any():
        raise ValueError("NAV history contains non-positive NAV after cleaning.")
    return out.sort_values(["amfi_code", "date"]).reset_index(drop=True)


def clean_aum_by_fund_house() -> pd.DataFrame:
    df = read_csv("03_aum_by_fund_house.csv")
    df["date"] = pd.to_datetime(df["date"], errors="raise")
    df["date_key"] = date_key(df["date"])
    for column in ["aum_lakh_crore", "aum_crore", "num_schemes"]:
        df[column] = pd.to_numeric(df[column], errors="raise")
    df = df.drop_duplicates(subset=["date", "fund_house"], keep="last")
    df["date"] = df["date"].dt.date.astype("string")
    return df.sort_values(["date", "fund_house"]).reset_index(drop=True)


def clean_monthly_sip_inflows() -> pd.DataFrame:
    df = read_csv("04_monthly_sip_inflows.csv")
    df["month"] = pd.to_datetime(df["month"], format="%Y-%m", errors="raise")
    df["date_key"] = date_key(df["month"])
    for column in df.columns.difference(["month"]):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["month"] = df["month"].dt.strftime("%Y-%m")
    return df.sort_values("month").reset_index(drop=True)


def clean_category_inflows() -> pd.DataFrame:
    df = read_csv("05_category_inflows.csv")
    df["month"] = pd.to_datetime(df["month"], format="%Y-%m", errors="raise")
    df["date_key"] = date_key(df["month"])
    df["net_inflow_crore"] = pd.to_numeric(df["net_inflow_crore"], errors="raise")
    df = df.drop_duplicates(subset=["month", "category"], keep="last")
    df["month"] = df["month"].dt.strftime("%Y-%m")
    return df.sort_values(["month", "category"]).reset_index(drop=True)


def clean_industry_folio_count() -> pd.DataFrame:
    df = read_csv("06_industry_folio_count.csv")
    df["month"] = pd.to_datetime(df["month"], format="%Y-%m", errors="raise")
    df["date_key"] = date_key(df["month"])
    for column in df.columns.difference(["month"]):
        df[column] = pd.to_numeric(df[column], errors="raise")
    df["month"] = df["month"].dt.strftime("%Y-%m")
    return df.sort_values("month").reset_index(drop=True)


def clean_scheme_performance() -> pd.DataFrame:
    df = read_csv("07_scheme_performance.csv")
    df["amfi_code"] = pd.to_numeric(df["amfi_code"], errors="raise").astype("int64")
    for column in RETURN_COLUMNS + ["aum_crore", "expense_ratio_pct", "morningstar_rating"]:
        df[column] = pd.to_numeric(df[column], errors="raise")
    reasons = []
    for _, row in df.iterrows():
        row_reasons = []
        for column in RETURN_COLUMNS:
            if pd.isna(row[column]):
                row_reasons.append(f"{column} not numeric")
            elif abs(float(row[column])) > 100:
                row_reasons.append(f"{column} outside +/-100%")
        if not 0.1 <= float(row["expense_ratio_pct"]) <= 2.5:
            row_reasons.append("expense_ratio_pct outside 0.1%-2.5%")
        reasons.append("; ".join(row_reasons))
    df["anomaly_flag"] = [bool(reason) for reason in reasons]
    df["anomaly_reason"] = reasons
    as_of_date = pd.Timestamp("2025-12-31")
    df["as_of_date"] = as_of_date.date().isoformat()
    df["date_key"] = int(as_of_date.strftime("%Y%m%d"))
    return df.sort_values("amfi_code").reset_index(drop=True)


def clean_investor_transactions() -> pd.DataFrame:
    df = read_csv("08_investor_transactions.csv")
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="raise")
    df["date_key"] = date_key(df["transaction_date"])
    df["amfi_code"] = pd.to_numeric(df["amfi_code"], errors="raise").astype("int64")
    normalized_type = df["transaction_type"].str.lower().map(TRANSACTION_TYPES)
    invalid_types = df.loc[normalized_type.isna(), "transaction_type"].unique()
    if len(invalid_types):
        raise ValueError(f"Unknown transaction_type values: {invalid_types}")
    df["transaction_type"] = normalized_type
    df["amount_inr"] = pd.to_numeric(df["amount_inr"], errors="raise")
    if (df["amount_inr"] <= 0).any():
        raise ValueError("Transactions contain amount_inr <= 0.")
    invalid_kyc = sorted(set(df["kyc_status"]) - KYC_STATUSES)
    if invalid_kyc:
        raise ValueError(f"Unknown kyc_status values: {invalid_kyc}")
    df["annual_income_lakh"] = pd.to_numeric(df["annual_income_lakh"], errors="raise")
    df = df.drop_duplicates().sort_values(["transaction_date", "investor_id", "amfi_code"])
    df.insert(0, "transaction_id", range(1, len(df) + 1))
    df["transaction_date"] = df["transaction_date"].dt.date.astype("string")
    return df.reset_index(drop=True)


def clean_portfolio_holdings() -> pd.DataFrame:
    df = read_csv("09_portfolio_holdings.csv")
    df["amfi_code"] = pd.to_numeric(df["amfi_code"], errors="raise").astype("int64")
    df["portfolio_date"] = pd.to_datetime(df["portfolio_date"], errors="raise")
    df["date_key"] = date_key(df["portfolio_date"])
    for column in ["weight_pct", "market_value_cr", "current_price_inr"]:
        df[column] = pd.to_numeric(df[column], errors="raise")
    df = df.drop_duplicates(subset=["amfi_code", "stock_symbol", "portfolio_date"], keep="last")
    df["portfolio_date"] = df["portfolio_date"].dt.date.astype("string")
    return df.sort_values(["amfi_code", "stock_symbol"]).reset_index(drop=True)


def clean_benchmark_indices() -> pd.DataFrame:
    df = read_csv("10_benchmark_indices.csv")
    df["date"] = pd.to_datetime(df["date"], errors="raise")
    df["date_key"] = date_key(df["date"])
    df["close_value"] = pd.to_numeric(df["close_value"], errors="raise")
    df = df[df["close_value"] > 0].drop_duplicates(subset=["date", "index_name"], keep="last")
    df["date"] = df["date"].dt.date.astype("string")
    return df.sort_values(["index_name", "date"]).reset_index(drop=True)


def build_dim_date(cleaned: dict[str, pd.DataFrame]) -> pd.DataFrame:
    keys = []
    for df in cleaned.values():
        if "date_key" in df.columns:
            keys.extend(df["date_key"].dropna().astype("int64").tolist())
    dates = pd.to_datetime(pd.Series(sorted(set(keys))).astype("string"), format="%Y%m%d")
    return pd.DataFrame(
        {
            "date_key": dates.dt.strftime("%Y%m%d").astype("int64"),
            "date": dates.dt.date.astype("string"),
            "year": dates.dt.year.astype("int64"),
            "quarter": dates.dt.quarter.astype("int64"),
            "month": dates.dt.month.astype("int64"),
            "month_name": dates.dt.month_name(),
            "day": dates.dt.day.astype("int64"),
            "day_of_week": dates.dt.day_name(),
            "is_weekend": dates.dt.dayofweek.isin([5, 6]),
        }
    )


def write_processed_csvs(cleaned: dict[str, pd.DataFrame]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in cleaned.items():
        df.to_csv(PROCESSED_DIR / name, index=False)


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS benchmark_indices;
DROP TABLE IF EXISTS portfolio_holdings;
DROP TABLE IF EXISTS industry_folio_count;
DROP TABLE IF EXISTS category_inflows;
DROP TABLE IF EXISTS monthly_sip_inflows;
DROP TABLE IF EXISTS fact_aum;
DROP TABLE IF EXISTS fact_performance;
DROP TABLE IF EXISTS fact_transactions;
DROP TABLE IF EXISTS fact_nav;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_fund;

CREATE TABLE dim_fund (
    fund_key INTEGER PRIMARY KEY,
    amfi_code INTEGER NOT NULL UNIQUE,
    fund_house TEXT NOT NULL,
    scheme_name TEXT NOT NULL,
    category TEXT NOT NULL,
    sub_category TEXT NOT NULL,
    plan TEXT NOT NULL,
    launch_date DATE NOT NULL,
    benchmark TEXT NOT NULL,
    expense_ratio_pct REAL NOT NULL CHECK (expense_ratio_pct BETWEEN 0.1 AND 2.5),
    exit_load_pct REAL NOT NULL,
    min_sip_amount REAL NOT NULL,
    min_lumpsum_amount REAL NOT NULL,
    fund_manager TEXT NOT NULL,
    risk_category TEXT NOT NULL,
    sebi_category_code TEXT NOT NULL
);

CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    day INTEGER NOT NULL,
    day_of_week TEXT NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

CREATE TABLE fact_nav (
    fund_key INTEGER NOT NULL,
    date_key INTEGER NOT NULL,
    nav REAL NOT NULL CHECK (nav > 0),
    is_forward_filled BOOLEAN NOT NULL,
    PRIMARY KEY (fund_key, date_key),
    FOREIGN KEY (fund_key) REFERENCES dim_fund(fund_key),
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key)
);

CREATE TABLE fact_transactions (
    transaction_id INTEGER PRIMARY KEY,
    investor_id TEXT NOT NULL,
    date_key INTEGER NOT NULL,
    fund_key INTEGER NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('SIP', 'Lumpsum', 'Redemption')),
    amount_inr REAL NOT NULL CHECK (amount_inr > 0),
    state TEXT NOT NULL,
    city TEXT NOT NULL,
    city_tier TEXT NOT NULL,
    age_group TEXT NOT NULL,
    gender TEXT NOT NULL,
    annual_income_lakh REAL NOT NULL,
    payment_mode TEXT NOT NULL,
    kyc_status TEXT NOT NULL CHECK (kyc_status IN ('Verified', 'Pending', 'Rejected')),
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (fund_key) REFERENCES dim_fund(fund_key)
);

CREATE TABLE fact_performance (
    fund_key INTEGER PRIMARY KEY,
    date_key INTEGER NOT NULL,
    return_1yr_pct REAL NOT NULL,
    return_3yr_pct REAL NOT NULL,
    return_5yr_pct REAL NOT NULL,
    benchmark_3yr_pct REAL NOT NULL,
    alpha REAL NOT NULL,
    beta REAL NOT NULL,
    sharpe_ratio REAL NOT NULL,
    sortino_ratio REAL NOT NULL,
    std_dev_ann_pct REAL NOT NULL,
    max_drawdown_pct REAL NOT NULL,
    aum_crore REAL NOT NULL,
    expense_ratio_pct REAL NOT NULL CHECK (expense_ratio_pct BETWEEN 0.1 AND 2.5),
    morningstar_rating INTEGER NOT NULL,
    risk_grade TEXT NOT NULL,
    anomaly_flag BOOLEAN NOT NULL,
    anomaly_reason TEXT NOT NULL,
    FOREIGN KEY (fund_key) REFERENCES dim_fund(fund_key),
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key)
);

CREATE TABLE fact_aum (
    aum_id INTEGER PRIMARY KEY,
    date_key INTEGER NOT NULL,
    fund_house TEXT NOT NULL,
    aum_lakh_crore REAL NOT NULL,
    aum_crore REAL NOT NULL,
    num_schemes INTEGER NOT NULL,
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key)
);

CREATE TABLE monthly_sip_inflows (
    date_key INTEGER PRIMARY KEY,
    sip_inflow_crore REAL NOT NULL,
    active_sip_accounts_crore REAL NOT NULL,
    new_sip_accounts_lakh REAL NOT NULL,
    sip_aum_lakh_crore REAL NOT NULL,
    yoy_growth_pct REAL,
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key)
);

CREATE TABLE category_inflows (
    date_key INTEGER NOT NULL,
    category TEXT NOT NULL,
    net_inflow_crore REAL NOT NULL,
    PRIMARY KEY (date_key, category),
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key)
);

CREATE TABLE industry_folio_count (
    date_key INTEGER PRIMARY KEY,
    total_folios_crore REAL NOT NULL,
    equity_folios_crore REAL NOT NULL,
    debt_folios_crore REAL NOT NULL,
    hybrid_folios_crore REAL NOT NULL,
    others_folios_crore REAL NOT NULL,
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key)
);

CREATE TABLE portfolio_holdings (
    fund_key INTEGER NOT NULL,
    date_key INTEGER NOT NULL,
    stock_symbol TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    sector TEXT NOT NULL,
    weight_pct REAL NOT NULL,
    market_value_cr REAL NOT NULL,
    current_price_inr REAL NOT NULL,
    PRIMARY KEY (fund_key, date_key, stock_symbol),
    FOREIGN KEY (fund_key) REFERENCES dim_fund(fund_key),
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key)
);

CREATE TABLE benchmark_indices (
    date_key INTEGER NOT NULL,
    index_name TEXT NOT NULL,
    close_value REAL NOT NULL CHECK (close_value > 0),
    PRIMARY KEY (date_key, index_name),
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key)
);
"""


QUERIES_SQL = """
-- 1. Top 5 funds by AUM
SELECT f.scheme_name, f.fund_house, p.aum_crore
FROM fact_performance p
JOIN dim_fund f ON f.fund_key = p.fund_key
ORDER BY p.aum_crore DESC
LIMIT 5;

-- 2. Average NAV per month
SELECT f.scheme_name, d.year, d.month, ROUND(AVG(n.nav), 4) AS avg_nav
FROM fact_nav n
JOIN dim_fund f ON f.fund_key = n.fund_key
JOIN dim_date d ON d.date_key = n.date_key
GROUP BY f.scheme_name, d.year, d.month
ORDER BY f.scheme_name, d.year, d.month;

-- 3. SIP YoY growth
SELECT d.year, d.month, s.sip_inflow_crore, s.yoy_growth_pct
FROM monthly_sip_inflows s
JOIN dim_date d ON d.date_key = s.date_key
ORDER BY d.year, d.month;

-- 4. Transactions by state
SELECT state, transaction_type, COUNT(*) AS transaction_count, SUM(amount_inr) AS total_amount_inr
FROM fact_transactions
GROUP BY state, transaction_type
ORDER BY total_amount_inr DESC;

-- 5. Funds with expense_ratio < 1%
SELECT scheme_name, fund_house, category, plan, expense_ratio_pct
FROM dim_fund
WHERE expense_ratio_pct < 1
ORDER BY expense_ratio_pct, scheme_name;

-- 6. Highest 3-year alpha funds
SELECT f.scheme_name, f.category, p.return_3yr_pct, p.benchmark_3yr_pct, p.alpha
FROM fact_performance p
JOIN dim_fund f ON f.fund_key = p.fund_key
ORDER BY p.alpha DESC
LIMIT 10;

-- 7. Monthly net flows by category
SELECT d.year, d.month, c.category, c.net_inflow_crore
FROM category_inflows c
JOIN dim_date d ON d.date_key = c.date_key
ORDER BY d.year, d.month, c.net_inflow_crore DESC;

-- 8. Redemption pressure by fund
SELECT f.scheme_name,
       SUM(CASE WHEN t.transaction_type = 'Redemption' THEN t.amount_inr ELSE 0 END) AS redemption_amount_inr,
       SUM(t.amount_inr) AS total_transaction_amount_inr,
       ROUND(100.0 * SUM(CASE WHEN t.transaction_type = 'Redemption' THEN t.amount_inr ELSE 0 END) / SUM(t.amount_inr), 2) AS redemption_share_pct
FROM fact_transactions t
JOIN dim_fund f ON f.fund_key = t.fund_key
GROUP BY f.scheme_name
ORDER BY redemption_share_pct DESC;

-- 9. Latest NAV by fund
SELECT f.scheme_name, d.date, n.nav, n.is_forward_filled
FROM fact_nav n
JOIN dim_fund f ON f.fund_key = n.fund_key
JOIN dim_date d ON d.date_key = n.date_key
WHERE d.date_key = (SELECT MAX(date_key) FROM fact_nav)
ORDER BY f.scheme_name;

-- 10. Benchmark index monthly returns
WITH month_end AS (
    SELECT index_name, d.year, d.month, MAX(d.date_key) AS month_end_key
    FROM benchmark_indices b
    JOIN dim_date d ON d.date_key = b.date_key
    GROUP BY index_name, d.year, d.month
),
monthly_close AS (
    SELECT m.index_name, m.year, m.month, b.close_value
    FROM month_end m
    JOIN benchmark_indices b
      ON b.index_name = m.index_name
     AND b.date_key = m.month_end_key
)
SELECT index_name,
       year,
       month,
       close_value,
       ROUND(100.0 * (close_value / LAG(close_value) OVER (PARTITION BY index_name ORDER BY year, month) - 1), 2) AS monthly_return_pct
FROM monthly_close
ORDER BY index_name, year, month;
"""


def prepare_load_frames(cleaned: dict[str, pd.DataFrame], dim_date: pd.DataFrame) -> dict[str, pd.DataFrame]:
    dim_fund = cleaned["01_fund_master.csv"].rename(columns={"amfi_code": "fund_key"}).copy()
    dim_fund.insert(1, "amfi_code", dim_fund["fund_key"])

    fact_nav = cleaned["02_nav_history.csv"].rename(columns={"amfi_code": "fund_key"})
    fact_nav = fact_nav[["fund_key", "date_key", "nav", "is_forward_filled"]]

    fact_transactions = cleaned["08_investor_transactions.csv"].rename(columns={"amfi_code": "fund_key"})
    fact_transactions = fact_transactions[
        [
            "transaction_id",
            "investor_id",
            "date_key",
            "fund_key",
            "transaction_type",
            "amount_inr",
            "state",
            "city",
            "city_tier",
            "age_group",
            "gender",
            "annual_income_lakh",
            "payment_mode",
            "kyc_status",
        ]
    ]

    fact_performance = cleaned["07_scheme_performance.csv"].rename(columns={"amfi_code": "fund_key"})
    fact_performance = fact_performance[
        [
            "fund_key",
            "date_key",
            *RETURN_COLUMNS,
            "aum_crore",
            "expense_ratio_pct",
            "morningstar_rating",
            "risk_grade",
            "anomaly_flag",
            "anomaly_reason",
        ]
    ]

    fact_aum = cleaned["03_aum_by_fund_house.csv"].copy()
    fact_aum.insert(0, "aum_id", range(1, len(fact_aum) + 1))
    fact_aum = fact_aum[["aum_id", "date_key", "fund_house", "aum_lakh_crore", "aum_crore", "num_schemes"]]

    monthly_sip = cleaned["04_monthly_sip_inflows.csv"][
        [
            "date_key",
            "sip_inflow_crore",
            "active_sip_accounts_crore",
            "new_sip_accounts_lakh",
            "sip_aum_lakh_crore",
            "yoy_growth_pct",
        ]
    ]
    category_inflows = cleaned["05_category_inflows.csv"][["date_key", "category", "net_inflow_crore"]]
    folios = cleaned["06_industry_folio_count.csv"][
        [
            "date_key",
            "total_folios_crore",
            "equity_folios_crore",
            "debt_folios_crore",
            "hybrid_folios_crore",
            "others_folios_crore",
        ]
    ]
    holdings = cleaned["09_portfolio_holdings.csv"].rename(columns={"amfi_code": "fund_key"})
    holdings = holdings[
        [
            "fund_key",
            "date_key",
            "stock_symbol",
            "stock_name",
            "sector",
            "weight_pct",
            "market_value_cr",
            "current_price_inr",
        ]
    ]
    benchmarks = cleaned["10_benchmark_indices.csv"][["date_key", "index_name", "close_value"]]

    return {
        "dim_fund": dim_fund,
        "dim_date": dim_date,
        "fact_nav": fact_nav,
        "fact_transactions": fact_transactions,
        "fact_performance": fact_performance,
        "fact_aum": fact_aum,
        "monthly_sip_inflows": monthly_sip,
        "category_inflows": category_inflows,
        "industry_folio_count": folios,
        "portfolio_holdings": holdings,
        "benchmark_indices": benchmarks,
    }


def write_sql_files() -> None:
    SCHEMA_PATH.write_text(SCHEMA_SQL.strip() + "\n", encoding="utf-8")
    QUERIES_PATH.write_text(QUERIES_SQL.strip() + "\n", encoding="utf-8")


def load_sqlite(load_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if DB_PATH.exists():
        DB_PATH.unlink()
    engine = create_engine(f"sqlite:///{DB_PATH}")
    with engine.begin() as conn:
        for statement in SCHEMA_SQL.split(";"):
            if statement.strip():
                conn.execute(text(statement))
        conn.execute(text("PRAGMA foreign_keys = ON"))
        for table, df in load_frames.items():
            df.to_sql(table, conn, if_exists="append", index=False)

        checks = []
        for table, df in load_frames.items():
            db_count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            checks.append(
                {
                    "table_name": table,
                    "cleaned_rows": len(df),
                    "db_rows": db_count,
                    "matches_cleaned_csv": len(df) == db_count,
                }
            )
    return pd.DataFrame(checks)


def write_data_dictionary(row_counts: pd.DataFrame) -> None:
    sections = []
    processed_counts = []
    for source_path in sorted(RAW_DIR.glob("[0-9][0-9]_*.csv")):
        processed_path = PROCESSED_DIR / source_path.name
        if processed_path.exists():
            raw_rows = len(pd.read_csv(source_path))
            cleaned_rows = len(pd.read_csv(processed_path))
            note = "matches raw row count"
            if source_path.name == "02_nav_history.csv":
                note = "higher after daily holiday/weekend forward-fill"
            elif raw_rows != cleaned_rows:
                note = "changed by cleaning/deduplication"
            processed_counts.append((source_path.name, raw_rows, cleaned_rows, note))

    sections.append(
        """# Bluestock Mutual Fund Data Dictionary

This dictionary documents the Day 2 cleaned CSVs and SQLite star schema. Source references are the numbered files in `data/raw/`; cleaned references are the matching files in `data/processed/`.

## Cleaning Rules

- Dates are parsed to ISO date strings and `date_key` uses `YYYYMMDD`.
- NAV is sorted by `amfi_code` and date, duplicate fund/date rows are removed, non-positive NAV values are rejected, and missing calendar days are forward-filled with `is_forward_filled = true`.
- Transaction types are standardized to `SIP`, `Lumpsum`, and `Redemption`; `amount_inr` must be positive; `kyc_status` must be `Verified`, `Pending`, or `Rejected`.
- Scheme return metrics are numeric. Performance anomalies are flagged when return metrics exceed +/-100% or expense ratios fall outside 0.1%-2.5%.
- Expense ratios in fund and performance data are constrained to 0.1%-2.5%.

## Raw to Processed Row Counts

| Source CSV | Raw rows | Processed rows | Note |
|---|---:|---:|---|
"""
    )
    for name, raw_rows, cleaned_rows, note in processed_counts:
        sections.append(f"| {name} | {raw_rows} | {cleaned_rows} | {note} |\n")

    sections.append(
        """
## Load Verification

| Table | Cleaned rows | SQLite rows | Match |
|---|---:|---:|---|
"""
    )
    for row in row_counts.itertuples(index=False):
        sections.append(
            f"| {row.table_name} | {row.cleaned_rows} | {row.db_rows} | {str(row.matches_cleaned_csv).lower()} |\n"
        )

    tables = {
        "dim_fund": [
            ("fund_key", "INTEGER", "Surrogate fund key; equal to AMFI code.", "01_fund_master.csv"),
            ("amfi_code", "INTEGER", "Official AMFI scheme code.", "01_fund_master.csv"),
            ("fund_house", "TEXT", "Asset management company or fund-house name.", "01_fund_master.csv"),
            ("scheme_name", "TEXT", "Mutual fund scheme name.", "01_fund_master.csv"),
            ("category", "TEXT", "Broad mutual fund category.", "01_fund_master.csv"),
            ("sub_category", "TEXT", "SEBI or business sub-category.", "01_fund_master.csv"),
            ("plan", "TEXT", "Direct or regular plan type.", "01_fund_master.csv"),
            ("launch_date", "DATE", "Scheme launch date.", "01_fund_master.csv"),
            ("benchmark", "TEXT", "Benchmark index used for comparison.", "01_fund_master.csv"),
            ("expense_ratio_pct", "REAL", "Annual expense ratio percentage.", "01_fund_master.csv"),
            ("exit_load_pct", "REAL", "Exit load percentage.", "01_fund_master.csv"),
            ("min_sip_amount", "REAL", "Minimum SIP investment amount.", "01_fund_master.csv"),
            ("min_lumpsum_amount", "REAL", "Minimum lump-sum investment amount.", "01_fund_master.csv"),
            ("fund_manager", "TEXT", "Named fund manager.", "01_fund_master.csv"),
            ("risk_category", "TEXT", "Risk classification.", "01_fund_master.csv"),
            ("sebi_category_code", "TEXT", "SEBI category code.", "01_fund_master.csv"),
        ],
        "dim_date": [
            ("date_key", "INTEGER", "Date surrogate key in YYYYMMDD format.", "Derived"),
            ("date", "DATE", "Calendar date.", "Derived from dated sources"),
            ("year", "INTEGER", "Calendar year.", "Derived"),
            ("quarter", "INTEGER", "Calendar quarter.", "Derived"),
            ("month", "INTEGER", "Calendar month number.", "Derived"),
            ("month_name", "TEXT", "Calendar month name.", "Derived"),
            ("day", "INTEGER", "Calendar day of month.", "Derived"),
            ("day_of_week", "TEXT", "Day name.", "Derived"),
            ("is_weekend", "BOOLEAN", "True for Saturday and Sunday.", "Derived"),
        ],
        "fact_nav": [
            ("fund_key", "INTEGER", "Fund foreign key.", "02_nav_history.csv"),
            ("date_key", "INTEGER", "Date foreign key.", "02_nav_history.csv"),
            ("nav", "REAL", "Net asset value.", "02_nav_history.csv"),
            ("is_forward_filled", "BOOLEAN", "True when NAV was filled for a non-trading calendar day.", "Derived"),
        ],
        "fact_transactions": [
            ("transaction_id", "INTEGER", "Sequential transaction key assigned after cleaning.", "08_investor_transactions.csv"),
            ("investor_id", "TEXT", "Masked investor identifier.", "08_investor_transactions.csv"),
            ("date_key", "INTEGER", "Transaction date foreign key.", "08_investor_transactions.csv"),
            ("fund_key", "INTEGER", "Fund foreign key.", "08_investor_transactions.csv"),
            ("transaction_type", "TEXT", "Standardized transaction type.", "08_investor_transactions.csv"),
            ("amount_inr", "REAL", "Transaction amount in Indian rupees.", "08_investor_transactions.csv"),
            ("state", "TEXT", "Investor state.", "08_investor_transactions.csv"),
            ("city", "TEXT", "Investor city.", "08_investor_transactions.csv"),
            ("city_tier", "TEXT", "B30 or T30 city classification.", "08_investor_transactions.csv"),
            ("age_group", "TEXT", "Investor age bucket.", "08_investor_transactions.csv"),
            ("gender", "TEXT", "Investor gender.", "08_investor_transactions.csv"),
            ("annual_income_lakh", "REAL", "Annual income in lakh INR.", "08_investor_transactions.csv"),
            ("payment_mode", "TEXT", "Payment channel.", "08_investor_transactions.csv"),
            ("kyc_status", "TEXT", "KYC status enum.", "08_investor_transactions.csv"),
        ],
        "fact_performance": [
            ("fund_key", "INTEGER", "Fund foreign key.", "07_scheme_performance.csv"),
            ("date_key", "INTEGER", "As-of date key for the performance snapshot.", "Derived"),
            ("return_1yr_pct", "REAL", "Trailing 1-year return percentage.", "07_scheme_performance.csv"),
            ("return_3yr_pct", "REAL", "Trailing 3-year return percentage.", "07_scheme_performance.csv"),
            ("return_5yr_pct", "REAL", "Trailing 5-year return percentage.", "07_scheme_performance.csv"),
            ("benchmark_3yr_pct", "REAL", "Trailing 3-year benchmark return percentage.", "07_scheme_performance.csv"),
            ("alpha", "REAL", "Excess return metric.", "07_scheme_performance.csv"),
            ("beta", "REAL", "Market beta.", "07_scheme_performance.csv"),
            ("sharpe_ratio", "REAL", "Risk-adjusted return ratio.", "07_scheme_performance.csv"),
            ("sortino_ratio", "REAL", "Downside-risk adjusted return ratio.", "07_scheme_performance.csv"),
            ("std_dev_ann_pct", "REAL", "Annualized standard deviation percentage.", "07_scheme_performance.csv"),
            ("max_drawdown_pct", "REAL", "Maximum drawdown percentage.", "07_scheme_performance.csv"),
            ("aum_crore", "REAL", "Scheme AUM in crore INR.", "07_scheme_performance.csv"),
            ("expense_ratio_pct", "REAL", "Annual expense ratio percentage.", "07_scheme_performance.csv"),
            ("morningstar_rating", "INTEGER", "Morningstar rating.", "07_scheme_performance.csv"),
            ("risk_grade", "TEXT", "Risk grade label.", "07_scheme_performance.csv"),
            ("anomaly_flag", "BOOLEAN", "True when validation found an anomaly.", "Derived"),
            ("anomaly_reason", "TEXT", "Semicolon-separated anomaly descriptions.", "Derived"),
        ],
        "fact_aum": [
            ("aum_id", "INTEGER", "Sequential AUM fact key.", "03_aum_by_fund_house.csv"),
            ("date_key", "INTEGER", "AUM date foreign key.", "03_aum_by_fund_house.csv"),
            ("fund_house", "TEXT", "Fund house at AUM reporting grain.", "03_aum_by_fund_house.csv"),
            ("aum_lakh_crore", "REAL", "AUM in lakh crore INR.", "03_aum_by_fund_house.csv"),
            ("aum_crore", "REAL", "AUM in crore INR.", "03_aum_by_fund_house.csv"),
            ("num_schemes", "INTEGER", "Number of schemes managed.", "03_aum_by_fund_house.csv"),
        ],
    }

    extra_tables = {
        "monthly_sip_inflows": "Monthly SIP inflows, active SIP accounts, new SIP accounts, SIP AUM, and YoY growth from 04_monthly_sip_inflows.csv.",
        "category_inflows": "Monthly net inflow by fund category from 05_category_inflows.csv.",
        "industry_folio_count": "Industry folio counts by month and asset class from 06_industry_folio_count.csv.",
        "portfolio_holdings": "Fund portfolio holdings by stock and sector from 09_portfolio_holdings.csv.",
        "benchmark_indices": "Benchmark index close values by date from 10_benchmark_indices.csv.",
    }

    sections.append("\n## Core Star Schema Columns\n")
    for table, columns in tables.items():
        sections.append(f"\n### {table}\n\n| Column | Type | Business definition | Source |\n|---|---|---|---|\n")
        for column, dtype, definition, source in columns:
            sections.append(f"| {column} | {dtype} | {definition} | {source} |\n")

    sections.append("\n## Additional Loaded Tables\n")
    for table, definition in extra_tables.items():
        sections.append(f"\n### {table}\n\n{definition}\n")

    DICTIONARY_PATH.write_text("".join(sections), encoding="utf-8")


def main() -> None:
    cleaned = {
        "01_fund_master.csv": clean_fund_master(),
        "02_nav_history.csv": clean_nav_history(),
        "03_aum_by_fund_house.csv": clean_aum_by_fund_house(),
        "04_monthly_sip_inflows.csv": clean_monthly_sip_inflows(),
        "05_category_inflows.csv": clean_category_inflows(),
        "06_industry_folio_count.csv": clean_industry_folio_count(),
        "07_scheme_performance.csv": clean_scheme_performance(),
        "08_investor_transactions.csv": clean_investor_transactions(),
        "09_portfolio_holdings.csv": clean_portfolio_holdings(),
        "10_benchmark_indices.csv": clean_benchmark_indices(),
    }
    dim_date = build_dim_date(cleaned)
    write_processed_csvs(cleaned)
    write_sql_files()
    load_frames = prepare_load_frames(cleaned, dim_date)
    row_counts = load_sqlite(load_frames)
    write_data_dictionary(row_counts)
    print(row_counts.to_string(index=False))


if __name__ == "__main__":
    main()
