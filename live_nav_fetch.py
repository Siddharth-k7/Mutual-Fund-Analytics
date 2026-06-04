import requests
import json
import pandas as pd

codes = [125497, 119551, 120503, 118632, 119092, 120841]

def fetch_and_save(code):
    url = f"https://api.mfapi.in/mf/{code}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data['data'])
        df['amfi_code'] = code
        df.to_csv(f'data/raw/nav_{code}.csv', index=False)
        print(f"Saved NAV data for code {code}")
    else:
        print(f"Failed to fetch data for code {code}: {response.status_code}")

if __name__ == "__main__":
    for code in codes:
        fetch_and_save(code)