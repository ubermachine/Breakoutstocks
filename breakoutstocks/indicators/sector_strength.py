"""Sector Relative Strength indicator calculations."""

import pandas as pd

def calculate_rs_rating(df_stock: pd.DataFrame, df_sector: pd.DataFrame) -> float:
    """Calculate Relative Strength (RS) of a stock against its sector.
    
    A simple RS based on 20-day returns.
    
    Args:
        df_stock: Daily bars of the stock
        df_sector: Daily bars of the sector index
        
    Returns:
        float representing RS score (-1.0 to 1.0)
    """
    if df_stock is None or df_stock.empty or df_sector is None or df_sector.empty:
        return 0.0
        
    try:
        # Align by date
        df1 = df_stock.copy()
        df2 = df_sector.copy()
        
        if "Date" in df1.columns:
            df1.set_index("Date", inplace=True)
        if "Date" in df2.columns:
            df2.set_index("Date", inplace=True)
            
        common_dates = df1.index.intersection(df2.index)
        if len(common_dates) < 20:
            return 0.0
            
        df1_common = df1.loc[common_dates]
        df2_common = df2.loc[common_dates]
        
        # 20-day returns
        ret_stock = (df1_common["Close"].iloc[-1] / df1_common["Close"].iloc[-20]) - 1.0
        ret_sector = (df2_common["Close"].iloc[-1] / df2_common["Close"].iloc[-20]) - 1.0
        
        # Relative return (stock outperformance)
        rs = ret_stock - ret_sector
        
        # Clip to -1.0 to 1.0 range
        return max(-1.0, min(1.0, rs * 10)) # Multiply by 10 to scale small percentages
    except Exception:
        return 0.0
