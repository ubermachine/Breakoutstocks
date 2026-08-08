"""Technical indicators module.

This module serves as the single source of truth for all technical indicator calculations
in the Breakoutstocks application.
"""

from typing import Optional
import pandas as pd
import numpy as np


def calculate_all_indicators(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Calculate all technical indicators on raw OHLCV DataFrame.

    Args:
        df: DataFrame containing at least ['Open', 'High', 'Low', 'Close', 'Volume'] columns.

    Returns:
        DataFrame enriched with technical indicator columns, or None if df is None or len(df) < 50.
    """
    if df is None or len(df) < 50:
        return None

    df = df.copy()

    # 1. Moving Averages
    df["SMA_20"] = df["Close"].rolling(window=20).mean()
    df["SMA_50"] = df["Close"].rolling(window=50).mean()
    df["SMA_200"] = df["Close"].rolling(window=200).mean()
    df["EMA_10"] = df["Close"].ewm(span=10, adjust=False).mean()
    df["EMA_12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["EMA_26"] = df["Close"].ewm(span=26, adjust=False).mean()

    # 2. MACD
    df["MACD"] = df["EMA_12"] - df["EMA_26"]
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    # 3. RSI (Wilder's exponential smoothing alpha=1/14)
    delta = df["Close"].diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # Handle zero division edge cases safely:
    # If loss is 0 and gain > 0 -> RSI = 100
    # If loss is 0 and gain is 0 -> RSI = 50
    rsi = rsi.fillna(pd.Series(np.where(avg_gain > 0, 100.0, 50.0), index=df.index))
    df["RSI"] = rsi.clip(0.0, 100.0)

    # 4. Bollinger Bands (20-period, 2 std dev)
    df["BB_Middle"] = df["Close"].rolling(window=20).mean()
    bb_std = df["Close"].rolling(window=20).std()
    df["BB_Upper"] = df["BB_Middle"] + (2.0 * bb_std)
    df["BB_Lower"] = df["BB_Middle"] - (2.0 * bb_std)

    # 5. ATR (14-period Wilder's smoothing)
    prev_close = df["Close"].shift(1)
    tr1 = df["High"] - df["Low"]
    tr2 = (df["High"] - prev_close).abs()
    tr3 = (df["Low"] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(alpha=1/14, adjust=False).mean()

    # 6. Volume Indicators
    df["Volume_SMA_20"] = df["Volume"].rolling(window=20).mean()
    df["Volume_Ratio"] = (df["Volume"] / df["Volume_SMA_20"].replace(0, np.nan)).fillna(0.0)
    
    change = df["Close"].diff()
    direction = pd.Series(np.where(change > 0, 1.0, np.where(change < 0, -1.0, 0.0)), index=df.index)
    df["OBV"] = (direction * df["Volume"]).cumsum()

    tp = (df["High"] + df["Low"] + df["Close"]) / 3.0
    cum_vol = df["Volume"].cumsum()
    df["VWAP"] = ((tp * df["Volume"]).cumsum() / cum_vol.replace(0, np.nan)).fillna(0.0)

    # 7. Momentum
    df["ROC_10"] = ((df["Close"] - df["Close"].shift(10)) / df["Close"].shift(10).replace(0, np.nan)) * 100.0
    df["ROC_20"] = ((df["Close"] - df["Close"].shift(20)) / df["Close"].shift(20).replace(0, np.nan)) * 100.0

    lowest_low = df["Low"].rolling(window=14).min()
    highest_high = df["High"].rolling(window=14).max()
    denom = (highest_high - lowest_low).replace(0, np.nan)
    stoch_k = ((df["Close"] - lowest_low) / denom) * 100.0
    df["Stoch_K"] = stoch_k.fillna(50.0).clip(0.0, 100.0)
    df["Stoch_D"] = df["Stoch_K"].rolling(window=3).mean().clip(0.0, 100.0)

    # 8. Trend Indicators (14-period ADX, Plus_DI, Minus_DI)
    up_move = df["High"] - df["High"].shift(1)
    down_move = df["Low"].shift(1) - df["Low"]
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    plus_dm_smoothed = pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean()
    minus_dm_smoothed = pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean()

    atr_denom = df["ATR"].replace(0, np.nan)
    df["Plus_DI"] = (100.0 * (plus_dm_smoothed / atr_denom)).fillna(0.0)
    df["Minus_DI"] = (100.0 * (minus_dm_smoothed / atr_denom)).fillna(0.0)

    di_sum = (df["Plus_DI"] + df["Minus_DI"]).replace(0, np.nan)
    dx = (100.0 * ((df["Plus_DI"] - df["Minus_DI"]).abs() / di_sum)).fillna(0.0)
    df["ADX"] = dx.ewm(alpha=1/14, adjust=False).mean()

    # 9. Convenience Aliases
    df["prev_close"] = df["Close"].shift(1)
    df["prev_high"] = df["High"].shift(1)
    df["prev_rsi"] = df["RSI"].shift(1)
    df["ema_10"] = df["EMA_10"]
    df["rsi"] = df["RSI"]
    df["atr"] = df["ATR"]
    df["volume_ratio"] = df["Volume_Ratio"]
    df["avg_volume_20d"] = df["Volume_SMA_20"]

    return df
