"""Track daily profits of active swing trades."""
import os
import sys
import pandas as pd
from datetime import datetime
import yfinance as yf

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

JOURNAL_FILE = "output/trade_journal.csv"
TRACKER_FILE = "output/daily_profit_tracker.csv"

def fetch_current_price(symbol: str) -> float:
    """Fetch the latest closing price using yfinance."""
    try:
        # Assuming Indian stocks need .NS suffix if not present, but journal might already have it
        ticker = symbol if symbol.endswith((".NS", ".BO")) else f"{symbol}.NS"
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")
        if not data.empty:
            return float(data["Close"].iloc[-1])
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
    return 0.0

def track_profits():
    if not os.path.exists(JOURNAL_FILE):
        print(f"No trade journal found at {JOURNAL_FILE}. Nothing to track.")
        return

    # Load journal
    journal_df = pd.read_csv(JOURNAL_FILE)
    
    # Load existing tracker if it exists
    if os.path.exists(TRACKER_FILE):
        tracker_df = pd.read_csv(TRACKER_FILE)
    else:
        tracker_df = pd.DataFrame(columns=[
            "Date", "TradeDate", "Symbol", "Entry", "CurrentPrice", 
            "Profit_Rs", "Profit_Pct", "Status", "ExitReason"
        ])

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    
    new_rows = []
    
    # Group tracker by TradeDate and Symbol to find CLOSED trades
    closed_trades = set()
    if not tracker_df.empty:
        closed = tracker_df[tracker_df["Status"] == "CLOSED"]
        for _, row in closed.iterrows():
            closed_trades.add((row["TradeDate"], row["Symbol"]))
            
    for _, trade in journal_df.iterrows():
        trade_date = str(trade["Date"])
        symbol = str(trade["Symbol"])
        
        # Skip if already closed
        if (trade_date, symbol) in closed_trades:
            continue
            
        entry_price = float(trade["Entry"])
        stop_loss = float(trade["StopLoss"])
        target_2 = float(trade["Target2"])
        max_hold_days = int(trade.get("MaxHoldDays", 7))
        
        # Calculate days held
        entry_dt = datetime.strptime(trade_date, "%Y-%m-%d %H:%M:%S")
        days_held = (today - entry_dt).days
        
        # Fetch current price
        current_price = fetch_current_price(symbol)
        if current_price == 0.0:
            print(f"Skipping {symbol} due to missing price data.")
            continue
            
        profit_rs = current_price - entry_price
        profit_pct = (profit_rs / entry_price) * 100
        
        status = "OPEN"
        exit_reason = ""
        
        # Closure Logic
        if current_price >= target_2:
            status = "CLOSED"
            exit_reason = "Target Hit"
        elif current_price <= stop_loss:
            status = "CLOSED"
            exit_reason = "Stop Loss Hit"
        elif days_held >= max_hold_days:
            status = "CLOSED"
            exit_reason = "Time Stop (Max Hold Days)"
            
        new_rows.append({
            "Date": today_str,
            "TradeDate": trade_date,
            "Symbol": symbol,
            "Entry": entry_price,
            "CurrentPrice": round(current_price, 2),
            "Profit_Rs": round(profit_rs, 2),
            "Profit_Pct": round(profit_pct, 2),
            "Status": status,
            "ExitReason": exit_reason
        })
        
        print(f"Tracked {symbol}: {status} (Profit: {profit_pct:.2f}%)")
        
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        
        if os.path.exists(TRACKER_FILE):
            new_df.to_csv(TRACKER_FILE, mode='a', header=False, index=False)
        else:
            os.makedirs(os.path.dirname(os.path.abspath(TRACKER_FILE)), exist_ok=True)
            new_df.to_csv(TRACKER_FILE, mode='w', header=True, index=False)
            
        print(f"Appended {len(new_rows)} updates to {TRACKER_FILE}")
    else:
        print("No active trades needed updating.")

if __name__ == "__main__":
    track_profits()
