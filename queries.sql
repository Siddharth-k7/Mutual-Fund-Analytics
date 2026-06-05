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
