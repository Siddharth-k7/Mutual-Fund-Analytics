# Bluestock Mutual Fund Data Dictionary

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
| 01_fund_master.csv | 40 | 40 | matches raw row count |
| 02_nav_history.csv | 46000 | 64320 | higher after daily holiday/weekend forward-fill |
| 03_aum_by_fund_house.csv | 90 | 90 | matches raw row count |
| 04_monthly_sip_inflows.csv | 48 | 48 | matches raw row count |
| 05_category_inflows.csv | 144 | 144 | matches raw row count |
| 06_industry_folio_count.csv | 21 | 21 | matches raw row count |
| 07_scheme_performance.csv | 40 | 40 | matches raw row count |
| 08_investor_transactions.csv | 32778 | 32778 | matches raw row count |
| 09_portfolio_holdings.csv | 322 | 322 | matches raw row count |
| 10_benchmark_indices.csv | 8050 | 8050 | matches raw row count |

## Load Verification

| Table | Cleaned rows | SQLite rows | Match |
|---|---:|---:|---|
| dim_fund | 40 | 40 | true |
| dim_date | 1609 | 1609 | true |
| fact_nav | 64320 | 64320 | true |
| fact_transactions | 32778 | 32778 | true |
| fact_performance | 40 | 40 | true |
| fact_aum | 90 | 90 | true |
| monthly_sip_inflows | 48 | 48 | true |
| category_inflows | 144 | 144 | true |
| industry_folio_count | 21 | 21 | true |
| portfolio_holdings | 322 | 322 | true |
| benchmark_indices | 8050 | 8050 | true |

## Core Star Schema Columns

### dim_fund

| Column | Type | Business definition | Source |
|---|---|---|---|
| fund_key | INTEGER | Surrogate fund key; equal to AMFI code. | 01_fund_master.csv |
| amfi_code | INTEGER | Official AMFI scheme code. | 01_fund_master.csv |
| fund_house | TEXT | Asset management company or fund-house name. | 01_fund_master.csv |
| scheme_name | TEXT | Mutual fund scheme name. | 01_fund_master.csv |
| category | TEXT | Broad mutual fund category. | 01_fund_master.csv |
| sub_category | TEXT | SEBI or business sub-category. | 01_fund_master.csv |
| plan | TEXT | Direct or regular plan type. | 01_fund_master.csv |
| launch_date | DATE | Scheme launch date. | 01_fund_master.csv |
| benchmark | TEXT | Benchmark index used for comparison. | 01_fund_master.csv |
| expense_ratio_pct | REAL | Annual expense ratio percentage. | 01_fund_master.csv |
| exit_load_pct | REAL | Exit load percentage. | 01_fund_master.csv |
| min_sip_amount | REAL | Minimum SIP investment amount. | 01_fund_master.csv |
| min_lumpsum_amount | REAL | Minimum lump-sum investment amount. | 01_fund_master.csv |
| fund_manager | TEXT | Named fund manager. | 01_fund_master.csv |
| risk_category | TEXT | Risk classification. | 01_fund_master.csv |
| sebi_category_code | TEXT | SEBI category code. | 01_fund_master.csv |

### dim_date

| Column | Type | Business definition | Source |
|---|---|---|---|
| date_key | INTEGER | Date surrogate key in YYYYMMDD format. | Derived |
| date | DATE | Calendar date. | Derived from dated sources |
| year | INTEGER | Calendar year. | Derived |
| quarter | INTEGER | Calendar quarter. | Derived |
| month | INTEGER | Calendar month number. | Derived |
| month_name | TEXT | Calendar month name. | Derived |
| day | INTEGER | Calendar day of month. | Derived |
| day_of_week | TEXT | Day name. | Derived |
| is_weekend | BOOLEAN | True for Saturday and Sunday. | Derived |

### fact_nav

| Column | Type | Business definition | Source |
|---|---|---|---|
| fund_key | INTEGER | Fund foreign key. | 02_nav_history.csv |
| date_key | INTEGER | Date foreign key. | 02_nav_history.csv |
| nav | REAL | Net asset value. | 02_nav_history.csv |
| is_forward_filled | BOOLEAN | True when NAV was filled for a non-trading calendar day. | Derived |

### fact_transactions

| Column | Type | Business definition | Source |
|---|---|---|---|
| transaction_id | INTEGER | Sequential transaction key assigned after cleaning. | 08_investor_transactions.csv |
| investor_id | TEXT | Masked investor identifier. | 08_investor_transactions.csv |
| date_key | INTEGER | Transaction date foreign key. | 08_investor_transactions.csv |
| fund_key | INTEGER | Fund foreign key. | 08_investor_transactions.csv |
| transaction_type | TEXT | Standardized transaction type. | 08_investor_transactions.csv |
| amount_inr | REAL | Transaction amount in Indian rupees. | 08_investor_transactions.csv |
| state | TEXT | Investor state. | 08_investor_transactions.csv |
| city | TEXT | Investor city. | 08_investor_transactions.csv |
| city_tier | TEXT | B30 or T30 city classification. | 08_investor_transactions.csv |
| age_group | TEXT | Investor age bucket. | 08_investor_transactions.csv |
| gender | TEXT | Investor gender. | 08_investor_transactions.csv |
| annual_income_lakh | REAL | Annual income in lakh INR. | 08_investor_transactions.csv |
| payment_mode | TEXT | Payment channel. | 08_investor_transactions.csv |
| kyc_status | TEXT | KYC status enum. | 08_investor_transactions.csv |

### fact_performance

| Column | Type | Business definition | Source |
|---|---|---|---|
| fund_key | INTEGER | Fund foreign key. | 07_scheme_performance.csv |
| date_key | INTEGER | As-of date key for the performance snapshot. | Derived |
| return_1yr_pct | REAL | Trailing 1-year return percentage. | 07_scheme_performance.csv |
| return_3yr_pct | REAL | Trailing 3-year return percentage. | 07_scheme_performance.csv |
| return_5yr_pct | REAL | Trailing 5-year return percentage. | 07_scheme_performance.csv |
| benchmark_3yr_pct | REAL | Trailing 3-year benchmark return percentage. | 07_scheme_performance.csv |
| alpha | REAL | Excess return metric. | 07_scheme_performance.csv |
| beta | REAL | Market beta. | 07_scheme_performance.csv |
| sharpe_ratio | REAL | Risk-adjusted return ratio. | 07_scheme_performance.csv |
| sortino_ratio | REAL | Downside-risk adjusted return ratio. | 07_scheme_performance.csv |
| std_dev_ann_pct | REAL | Annualized standard deviation percentage. | 07_scheme_performance.csv |
| max_drawdown_pct | REAL | Maximum drawdown percentage. | 07_scheme_performance.csv |
| aum_crore | REAL | Scheme AUM in crore INR. | 07_scheme_performance.csv |
| expense_ratio_pct | REAL | Annual expense ratio percentage. | 07_scheme_performance.csv |
| morningstar_rating | INTEGER | Morningstar rating. | 07_scheme_performance.csv |
| risk_grade | TEXT | Risk grade label. | 07_scheme_performance.csv |
| anomaly_flag | BOOLEAN | True when validation found an anomaly. | Derived |
| anomaly_reason | TEXT | Semicolon-separated anomaly descriptions. | Derived |

### fact_aum

| Column | Type | Business definition | Source |
|---|---|---|---|
| aum_id | INTEGER | Sequential AUM fact key. | 03_aum_by_fund_house.csv |
| date_key | INTEGER | AUM date foreign key. | 03_aum_by_fund_house.csv |
| fund_house | TEXT | Fund house at AUM reporting grain. | 03_aum_by_fund_house.csv |
| aum_lakh_crore | REAL | AUM in lakh crore INR. | 03_aum_by_fund_house.csv |
| aum_crore | REAL | AUM in crore INR. | 03_aum_by_fund_house.csv |
| num_schemes | INTEGER | Number of schemes managed. | 03_aum_by_fund_house.csv |

## Additional Loaded Tables

### monthly_sip_inflows

Monthly SIP inflows, active SIP accounts, new SIP accounts, SIP AUM, and YoY growth from 04_monthly_sip_inflows.csv.

### category_inflows

Monthly net inflow by fund category from 05_category_inflows.csv.

### industry_folio_count

Industry folio counts by month and asset class from 06_industry_folio_count.csv.

### portfolio_holdings

Fund portfolio holdings by stock and sector from 09_portfolio_holdings.csv.

### benchmark_indices

Benchmark index close values by date from 10_benchmark_indices.csv.
