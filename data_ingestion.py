import pandas as pd

def ingest_data():
    files = [
        "01_fund_master.csv",
        "02_nav_history.csv", 
        "03_aum_by_fund_house.csv",
        "04_monthly_sip_inflows.csv",
        "05_category_inflows.csv",
        "06_industry_folio_count.csv",
        "07_scheme_performance.csv",
        "08_investor_transactions.csv",
        "09_portfolio_holdings.csv",
        "10_benchmark_indices.csv"
    ]
    
    datasets = {}
    for f in files:
        try:
            df = pd.read_csv(f"data/raw/{f}")
            datasets[f] = df
            print(f"Loaded {f}: {df.shape[0]} rows, {df.shape[1]} columns")
        except Exception as e:
            print(f"Error loading {f}: {str(e)}")
    
    return datasets

if __name__ == "__main__":
    datasets = ingest_data()
    print(f"\nSuccessfully loaded {len(datasets)} datasets")