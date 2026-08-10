"""Simple signal backtester for evaluating trade patterns over historical data."""
import os
import sys
import pandas as pd
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from breakoutstocks.data.client import MarketDataClient
from breakoutstocks.indicators.technical import calculate_all_indicators
from breakoutstocks.scanners.breakout_reversal import BreakoutReversalScanner

def run_backtest(days: int = 365, hold_days: int = 10):
    client = MarketDataClient()
    scanner = BreakoutReversalScanner(client)
    tickers = client.get_all_nse_tickers()
    
    print(f"Running backtest over {len(tickers)} tickers for {days} days. Hold period: {hold_days} days.")
    
    results = []
    
    for symbol in tickers[:50]: # Limit for demo speed
        df = client.get_stock_ohlcv(symbol, days=days)
        if df is None or len(df) < 50:
            continue
            
        df_ind = calculate_all_indicators(df)
        if df_ind is None:
            continue
            
        # Very simple rolling simulation
        for i in range(50, len(df_ind) - hold_days):
            slice_df = df_ind.iloc[:i]
            # Since BreakoutReversalScanner looks at the last row of the slice
            signals = scanner.detect_breakout_signals(slice_df, symbol)
            if signals:
                entry_price = slice_df.iloc[-1]["Close"]
                exit_price = df_ind.iloc[i + hold_days]["Close"]
                ret = (exit_price / entry_price) - 1.0
                
                for sig in signals:
                    results.append({
                        "symbol": symbol,
                        "date": slice_df.index[-1],
                        "signal": sig["type"],
                        "return": ret,
                        "win": 1 if ret > 0 else 0
                    })
                    
    if not results:
        print("No signals found.")
        return
        
    res_df = pd.DataFrame(results)
    summary = res_df.groupby("signal").agg(
        count=("symbol", "count"),
        win_rate=("win", "mean"),
        avg_return=("return", "mean")
    ).sort_values("win_rate", ascending=False)
    
    print("\n=== Backtest Summary ===")
    print(summary)
    
if __name__ == "__main__":
    run_backtest()
