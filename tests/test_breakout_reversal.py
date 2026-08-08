"""Unit tests for BaseScanner and BreakoutReversalScanner signal detection."""

import os
from unittest.mock import MagicMock
import numpy as np
import pandas as pd
import pytest

from breakoutstocks.config import Config
from breakoutstocks.indicators.technical import calculate_all_indicators
from breakoutstocks.scanners.base import BaseScanner
from breakoutstocks.scanners.breakout_reversal import (
    BreakoutReversalScanner,
    detect_breakout_signals,
    detect_reversal_signals,
)


@pytest.fixture
def base_ohlcv():
    """Generate 60 days of synthetic OHLCV data."""
    np.random.seed(42)
    n = 60
    dates = pd.date_range("2026-01-01", periods=n, freq="D")

    close = np.linspace(100.0, 110.0, n)
    high = close + 2.0
    low = close - 2.0
    open_p = close - 0.5
    volume = np.full(n, 10000.0)

    df = pd.DataFrame(
        {
            "Open": open_p,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=dates,
    )
    return df


def test_detect_breakout_20day_high(base_ohlcv):
    """Test detection of 20-day high breakout with volume surge."""
    df = calculate_all_indicators(base_ohlcv)

    # Modify last row to break 20-day high with 2.5x volume ratio
    prev_20_high = df["High"].iloc[-21:-1].max()
    df.iloc[-1, df.columns.get_loc("Close")] = prev_20_high + 5.0
    df.iloc[-1, df.columns.get_loc("High")] = prev_20_high + 6.0
    df.iloc[-1, df.columns.get_loc("Volume_Ratio")] = 2.5

    signals = detect_breakout_signals(df, "TCS.NS")
    types = [s["type"] for s in signals]
    assert "BREAKOUT_20DAY_HIGH" in types


def test_detect_breakout_sma50(base_ohlcv):
    """Test detection of 50-day SMA crossover with volume surge."""
    df = calculate_all_indicators(base_ohlcv)

    # Set up previous close below SMA_50 and current close above SMA_50 with volume ratio 1.5
    sma_50 = df["SMA_50"].iloc[-1]
    df.iloc[-2, df.columns.get_loc("Close")] = sma_50 - 1.0
    df.iloc[-1, df.columns.get_loc("Close")] = sma_50 + 2.0
    df.iloc[-1, df.columns.get_loc("Volume_Ratio")] = 1.5

    signals = detect_breakout_signals(df, "500325.BO")
    types = [s["type"] for s in signals]
    assert "BREAKOUT_SMA50" in types


def test_detect_bollinger_breakout(base_ohlcv):
    """Test detection of Bollinger Upper Band breakout."""
    df = calculate_all_indicators(base_ohlcv)

    bb_upper = df["BB_Upper"].iloc[-1]
    df.iloc[-1, df.columns.get_loc("Close")] = bb_upper + 3.0
    df.iloc[-1, df.columns.get_loc("Volume_Ratio")] = 1.8

    signals = detect_breakout_signals(df, "RELIANCE.NS")
    types = [s["type"] for s in signals]
    assert "BOLLINGER_BREAKOUT" in types


def test_detect_golden_cross():
    """Test detection of 50 SMA crossing above 200 SMA."""
    n = 220
    dates = pd.date_range("2025-01-01", periods=n, freq="D")
    df = pd.DataFrame(
        {
            "Open": np.full(n, 100.0),
            "High": np.full(n, 105.0),
            "Low": np.full(n, 95.0),
            "Close": np.full(n, 100.0),
            "Volume": np.full(n, 10000.0),
        },
        index=dates,
    )
    df = calculate_all_indicators(df)

    # Simulate SMA_50 crossing SMA_200
    df.iloc[-2, df.columns.get_loc("SMA_50")] = 100.0
    df.iloc[-2, df.columns.get_loc("SMA_200")] = 101.0
    df.iloc[-1, df.columns.get_loc("SMA_50")] = 102.0
    df.iloc[-1, df.columns.get_loc("SMA_200")] = 101.0

    signals = detect_breakout_signals(df, "INFY.NS")
    types = [s["type"] for s in signals]
    assert "GOLDEN_CROSS" in types


def test_detect_rsi_oversold_reversal(base_ohlcv):
    """Test detection of RSI oversold reversal signal."""
    df = calculate_all_indicators(base_ohlcv)

    df.iloc[-2, df.columns.get_loc("RSI")] = 25.0
    df.iloc[-1, df.columns.get_loc("RSI")] = 28.0

    signals = detect_reversal_signals(df, "TCS.NS")
    types = [s["type"] for s in signals]
    assert "RSI_OVERSOLD_REVERSAL" in types


def test_detect_macd_bullish_crossover(base_ohlcv):
    """Test detection of MACD bullish crossover."""
    df = calculate_all_indicators(base_ohlcv)

    df.iloc[-2, df.columns.get_loc("MACD")] = -0.5
    df.iloc[-2, df.columns.get_loc("MACD_Signal")] = 0.0
    df.iloc[-1, df.columns.get_loc("MACD")] = 0.5
    df.iloc[-1, df.columns.get_loc("MACD_Signal")] = 0.0

    signals = detect_reversal_signals(df, "500325.BO")
    types = [s["type"] for s in signals]
    assert "MACD_BULLISH_CROSSOVER" in types


def test_detect_hammer_pattern(base_ohlcv):
    """Test detection of Hammer candlestick pattern."""
    df = calculate_all_indicators(base_ohlcv)

    # Previous candle bearish
    df.iloc[-2, df.columns.get_loc("Open")] = 105.0
    df.iloc[-2, df.columns.get_loc("Close")] = 100.0

    # Hammer candle: Open 101, Close 102 (body 1), Low 98 (lower shadow 3 >= 2*1), High 102.2 (upper shadow 0.2 < 1)
    df.iloc[-1, df.columns.get_loc("Open")] = 101.0
    df.iloc[-1, df.columns.get_loc("Close")] = 102.0
    df.iloc[-1, df.columns.get_loc("Low")] = 98.0
    df.iloc[-1, df.columns.get_loc("High")] = 102.2

    signals = detect_reversal_signals(df, "TATAMOTORS.NS")
    types = [s["type"] for s in signals]
    assert "HAMMER_PATTERN" in types


def test_detect_bullish_divergence(base_ohlcv):
    """Test detection of price-RSI bullish divergence."""
    df = calculate_all_indicators(base_ohlcv)

    # Over last 10 bars: price drops, RSI rises
    df.iloc[-10, df.columns.get_loc("Close")] = 110.0
    df.iloc[-1, df.columns.get_loc("Close")] = 100.0

    df.iloc[-10, df.columns.get_loc("RSI")] = 35.0
    df.iloc[-1, df.columns.get_loc("RSI")] = 45.0

    signals = detect_reversal_signals(df, "HDFCBANK.NS")
    types = [s["type"] for s in signals]
    assert "BULLISH_DIVERGENCE" in types


def test_breakout_reversal_scanner_execution(base_ohlcv, tmp_path):
    """Test BreakoutReversalScanner analyze_stock, scan, and save_results."""
    df = calculate_all_indicators(base_ohlcv)

    # Trigger a 20-day high breakout
    prev_20_high = df["High"].iloc[-21:-1].max()
    df.iloc[-1, df.columns.get_loc("Close")] = prev_20_high + 5.0
    df.iloc[-1, df.columns.get_loc("High")] = prev_20_high + 6.0
    df.iloc[-1, df.columns.get_loc("Volume_Ratio")] = 2.5

    mock_client = MagicMock()
    mock_client.get_stock_ohlcv.return_value = df
    mock_client.get_stock_name.side_effect = lambda sym: "Tata Consultancy Services" if "TCS" in sym else "Reliance Industries"

    config = Config(OUTPUT_DIR=str(tmp_path))
    scanner = BreakoutReversalScanner(data_client=mock_client, config=config)

    # Test analyze_stock
    result = scanner.analyze_stock("TCS.NS")
    assert result is not None
    assert result["symbol"] == "TCS.NS"
    assert result["name"] == "Tata Consultancy Services"
    assert result["strength_score"] > 0
    assert len(result["signals"]) > 0

    # Test parallel scan
    symbols = ["TCS.NS", "500325.BO"]
    scan_df = scanner.scan(symbols, max_workers=2)
    assert not scan_df.empty
    assert len(scan_df) == 2
    assert "symbol" in scan_df.columns
    assert "strength_score" in scan_df.columns

    # Test save_results
    filepath = scanner.save_results(scan_df, "test_breakouts")
    assert filepath.endswith(".csv")
    assert os.path.exists(filepath)
    saved_df = pd.read_csv(filepath)
    assert not saved_df.empty
