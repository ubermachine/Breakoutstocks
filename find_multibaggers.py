import requests
import zipfile
import io
import pandas as pd
import datetime
import yfinance as yf
import time
import os

def get_latest_bhavcopy():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    today = datetime.datetime.now()

    for i in range(10):
        d = today - datetime.timedelta(days=i)
        date_str = d.strftime("%d%m%y")
        url = f"https://www.bseindia.com/download/BhavCopy/Equity/EQ{date_str}_CSV.ZIP"

        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200 and response.content.startswith(b'PK\x03\x04'):
                print(f"Found Bhavcopy for {d.strftime('%Y-%m-%d')}")
                return response.content
        except requests.RequestException:
            pass

    print("Falling back to a known working Bhavcopy date (03/05/2024)")
    url = "https://www.bseindia.com/download/BhavCopy/Equity/EQ030524_CSV.ZIP"
    response = requests.get(url, headers=headers)
    if response.status_code == 200 and response.content.startswith(b'PK\x03\x04'):
        return response.content
    raise Exception("Could not download a valid Bhavcopy ZIP file from BSE")

def get_bse_tickers():
    content = get_latest_bhavcopy()
    tickers = []
    names = {}
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        for filename in z.namelist():
            with z.open(filename) as f:
                df = pd.read_csv(f)
                df.columns = df.columns.str.strip()
                if 'SC_CODE' in df.columns:
                    for _, row in df.iterrows():
                        ticker = f"{str(row['SC_CODE']).strip()}.BO"
                        tickers.append(ticker)
                        if 'SC_NAME' in df.columns:
                            names[ticker] = str(row['SC_NAME']).strip()
    return tickers, names

def fetch_yfinance_with_retry(tickers, start_date, end_date, max_retries=3):
    # To reduce the impact of rate limits, we can sleep slightly longer on retries.
    for attempt in range(max_retries):
        try:
            data = yf.download(tickers, start=start_date, end=end_date, threads=True, progress=False)
            if not data.empty:
                return data
        except Exception as e:
            pass
        time.sleep(2)
    return pd.DataFrame()

def get_multibaggers():
    print("Fetching BSE tickers...")
    tickers, names = get_bse_tickers()

    # Optional environment variable limit to speed up test runs or local testing
    max_tickers_to_process = os.environ.get("MAX_TICKERS")
    if max_tickers_to_process:
        tickers = tickers[:int(max_tickers_to_process)]
        print(f"Total tickers to process (limited by env): {len(tickers)}")
    else:
        print(f"Total tickers to process: {len(tickers)}")

    chunk_size = 100
    all_multibaggers = []

    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=365 * 5)

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        print(f"Processing chunk {i//chunk_size + 1}/{(len(tickers) + chunk_size - 1)//chunk_size} ({len(chunk)} tickers)...")

        data = fetch_yfinance_with_retry(chunk, start_date, end_date)

        if data.empty:
            print("No data retrieved for chunk.")
            continue

        if isinstance(data.columns, pd.MultiIndex):
            if 'Close' in data.columns.levels[0]:
                closes = data['Close']
            else:
                closes = pd.DataFrame()
        else:
            if len(chunk) == 1:
                if 'Close' in data:
                    closes = data['Close'].to_frame(name=chunk[0])
                else:
                    closes = pd.DataFrame()
            else:
                closes = data['Close'] if 'Close' in data else pd.DataFrame()

        for t in chunk:
            if t in closes.columns:
                series = closes[t].dropna()
                if len(series) > 0:
                    start_p = series.iloc[0]
                    end_p = series.iloc[-1]
                    if start_p > 0:
                        ret = (end_p - start_p) / start_p
                        if ret >= 1.0:
                            all_multibaggers.append({
                                'Ticker': t,
                                'Company_Name': names.get(t, 'Unknown'),
                                'Start_Date': series.index[0].strftime('%Y-%m-%d'),
                                'End_Date': series.index[-1].strftime('%Y-%m-%d'),
                                'Start_Price': round(start_p, 2),
                                'End_Price': round(end_p, 2),
                                'Return_%': round(ret * 100, 2)
                            })

        # We need a small delay between chunks to avoid Yahoo rate limits
        time.sleep(2)

    df_mb = pd.DataFrame(all_multibaggers)
    if not df_mb.empty:
        df_mb = df_mb.sort_values(by='Return_%', ascending=False)
        df_mb.to_csv("bse_multibaggers.csv", index=False)
        print(f"Found {len(df_mb)} multibaggers. Saved to bse_multibaggers.csv")
    else:
        print("No multibaggers found.")
        pd.DataFrame(columns=['Ticker', 'Company_Name', 'Start_Date', 'End_Date', 'Start_Price', 'End_Price', 'Return_%']).to_csv("bse_multibaggers.csv", index=False)

if __name__ == "__main__":
    get_multibaggers()
