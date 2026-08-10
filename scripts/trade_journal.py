"""Simple CSV-based swing trade journal."""
import os
import pandas as pd
from datetime import datetime
from breakoutstocks.models.types import TradePlan

class TradeJournal:
    def __init__(self, filepath="output/trade_journal.csv"):
        self.filepath = filepath
        os.makedirs(os.path.dirname(os.path.abspath(self.filepath)), exist_ok=True)
        
    def log_trade(self, symbol: str, tp: TradePlan, reason: str = ""):
        entry = {
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Symbol": symbol,
            "Entry": tp.entry,
            "StopLoss": tp.stop_loss,
            "Target1": tp.target_1,
            "Target2": tp.target_2,
            "RR": tp.risk_reward,
            "Size": tp.position_size,
            "MaxHoldDays": tp.max_hold_days,
            "Reason": reason
        }
        
        df_new = pd.DataFrame([entry])
        
        if os.path.exists(self.filepath):
            df_new.to_csv(self.filepath, mode='a', header=False, index=False)
        else:
            df_new.to_csv(self.filepath, mode='w', header=True, index=False)
            
        print(f"Logged trade for {symbol} to {self.filepath}")

if __name__ == "__main__":
    journal = TradeJournal()
    print(f"Journal initialized at {journal.filepath}")
