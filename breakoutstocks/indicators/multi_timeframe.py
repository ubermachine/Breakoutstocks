"""Multi-timeframe indicator calculations."""

import pandas as pd

def get_weekly_bias(df_daily: pd.DataFrame) -> str:
    """Resample daily to weekly and return trend bias.
    
    Args:
        df_daily: DataFrame containing at least 'Open', 'High', 'Low', 'Close', 'Volume'.
                  Must have a DatetimeIndex or a 'Date' column.
                  
    Returns:
        String indicating weekly bias: 'BULLISH', 'BEARISH', or 'NEUTRAL'.
    """
    df = df_daily.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)
        else:
            # Cannot resample without dates
            return "NEUTRAL"

    try:
        # Resample to weekly ending on Friday
        df_w = df.resample("W-FRI").agg({
            "Open": "first", 
            "High": "max", 
            "Low": "min",
            "Close": "last", 
            "Volume": "sum"
        }).dropna()
        
        if len(df_w) < 10:
            return "NEUTRAL"
        
        sma_10w = df_w["Close"].rolling(10).mean().iloc[-1]
        close_w = df_w["Close"].iloc[-1]
        
        if close_w > sma_10w:
            return "BULLISH"  # Weekly trend supports daily longs
        elif close_w < sma_10w * 0.98:
            return "BEARISH"  # Weekly trend opposes daily longs
        else:
            return "NEUTRAL"
    except Exception:
        return "NEUTRAL"
