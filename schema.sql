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
