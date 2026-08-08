import pytest
import pandas as pd
import numpy as np
from breakoutstocks.indicators.technical import calculate_all_indicators

@pytest.fixture
def sample_ohlcv():
    """Generate 60 rows of synthetic OHLCV data for testing."""
    np.random.seed(42)
    n = 60
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    
    # Generate prices with a trend and noise
    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, size=n)
    close = base_price * np.exp(np.cumsum(returns))
    high = close * (1 + np.abs(np.random.normal(0, 0.01, size=n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, size=n)))
    open_price = low + (high - low) * np.random.uniform(0.2, 0.8, size=n)
    volume = np.random.randint(1000, 50000, size=n).astype(float)
    
    return pd.DataFrame({
        "Open": open_price,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    }, index=dates)


def test_calculate_all_indicators_none_or_short(sample_ohlcv):
    """Should return None if input DataFrame is None or length < 50."""
    assert calculate_all_indicators(None) is None
    
    short_df = sample_ohlcv.iloc[:49]
    assert calculate_all_indicators(short_df) is None


def test_calculate_all_indicators_columns(sample_ohlcv):
    """Should return DataFrame with all expected indicator columns."""
    result = calculate_all_indicators(sample_ohlcv)
    assert result is not None
    
    required_cols = [
        "SMA_20", "SMA_50", "SMA_200",
        "EMA_10", "EMA_12", "EMA_26",
        "MACD", "MACD_Signal", "MACD_Hist",
        "RSI",
        "BB_Upper", "BB_Middle", "BB_Lower",
        "ATR",
        "Volume_SMA_20", "Volume_Ratio", "OBV", "VWAP",
        "ROC_10", "ROC_20",
        "Stoch_K", "Stoch_D",
        "ADX", "Plus_DI", "Minus_DI",
        "prev_close", "prev_high", "prev_rsi", "ema_10", "rsi", "atr", "volume_ratio", "avg_volume_20d"
    ]
    
    for col in required_cols:
        assert col in result.columns, f"Missing expected column: {col}"


def test_rsi_wilders_smoothing(sample_ohlcv):
    """Test RSI bounded [0, 100] and matches Wilder's exponential smoothing behavior."""
    result = calculate_all_indicators(sample_ohlcv)
    assert result is not None
    
    rsi = result["RSI"].dropna()
    assert (rsi >= 0.0).all() and (rsi <= 100.0).all()
    
    # Calculate simple rolling RSI for comparison to ensure we are NOT using simple rolling mean
    delta = sample_ohlcv["Close"].diff()
    gain_simple = delta.clip(lower=0).rolling(14).mean()
    loss_simple = (-delta.clip(upper=0)).rolling(14).mean()
    rs_simple = gain_simple / loss_simple.replace(0, np.nan)
    rsi_simple = 100.0 - (100.0 / (1.0 + rs_simple))
    
    # Wilder's RSI should differ from Simple Rolling RSI
    diff = (rsi - rsi_simple).dropna()
    assert not np.allclose(rsi.loc[diff.index], rsi_simple.loc[diff.index]), "RSI should use Wilder's ewm(alpha=1/14), not simple rolling mean"


def test_bollinger_bands_ordering(sample_ohlcv):
    """Assert Bollinger Bands ordering: BB_Upper >= BB_Middle >= BB_Lower."""
    result = calculate_all_indicators(sample_ohlcv)
    assert result is not None
    
    valid_bb = result.dropna(subset=["BB_Upper", "BB_Middle", "BB_Lower"])
    assert (valid_bb["BB_Upper"] >= valid_bb["BB_Middle"] - 1e-9).all()
    assert (valid_bb["BB_Middle"] >= valid_bb["BB_Lower"] - 1e-9).all()


def test_volume_ratio(sample_ohlcv):
    """Assert Volume_Ratio = Volume / Volume_SMA_20."""
    result = calculate_all_indicators(sample_ohlcv)
    assert result is not None
    
    valid = result.dropna(subset=["Volume_SMA_20", "Volume_Ratio"])
    expected_ratio = valid["Volume"] / valid["Volume_SMA_20"]
    np.testing.assert_allclose(valid["Volume_Ratio"], expected_ratio)


def test_stochastic_oscillator_bounds(sample_ohlcv):
    """Assert Stochastic K and D are bounded in [0, 100]."""
    result = calculate_all_indicators(sample_ohlcv)
    assert result is not None
    
    stoch_k = result["Stoch_K"].dropna()
    stoch_d = result["Stoch_D"].dropna()
    
    assert (stoch_k >= 0.0).all() and (stoch_k <= 100.0).all()
    assert (stoch_d >= 0.0).all() and (stoch_d <= 100.0).all()


def test_atr_positive(sample_ohlcv):
    """Assert ATR > 0 for valid rows."""
    result = calculate_all_indicators(sample_ohlcv)
    assert result is not None
    
    atr = result["ATR"].dropna()
    assert (atr > 0.0).all()


def test_macd_hist(sample_ohlcv):
    """Assert MACD_Hist == MACD - MACD_Signal."""
    result = calculate_all_indicators(sample_ohlcv)
    assert result is not None
    
    valid = result.dropna(subset=["MACD", "MACD_Signal", "MACD_Hist"])
    np.testing.assert_allclose(valid["MACD_Hist"], valid["MACD"] - valid["MACD_Signal"])


def test_aliases(sample_ohlcv):
    """Assert convenience aliases match their original indicator columns."""
    result = calculate_all_indicators(sample_ohlcv)
    assert result is not None
    
    np.testing.assert_allclose(result["ema_10"], result["EMA_10"])
    np.testing.assert_allclose(result["rsi"], result["RSI"])
    np.testing.assert_allclose(result["atr"], result["ATR"])
    np.testing.assert_allclose(result["volume_ratio"], result["Volume_Ratio"])
    np.testing.assert_allclose(result["avg_volume_20d"], result["Volume_SMA_20"])
    np.testing.assert_allclose(result["prev_close"].iloc[1:], result["Close"].iloc[:-1])
    np.testing.assert_allclose(result["prev_high"].iloc[1:], result["High"].iloc[:-1])
    np.testing.assert_allclose(result["prev_rsi"].iloc[1:], result["RSI"].iloc[:-1])
