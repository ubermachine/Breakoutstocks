"""Unit tests for MultibaggerScanner and fundamental scoring."""

from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd
import pytest

from breakoutstocks.config import Config
from breakoutstocks.models.types import MultibaggerResult


# We import score_fundamentals and MultibaggerScanner from breakoutstocks.scanners.multibagger
# (This will fail initially before implementation, as per TDD)
from breakoutstocks.scanners.multibagger import (
    MultibaggerScanner,
    score_fundamentals,
)


@pytest.fixture
def sample_config():
    """Return a standard Config instance."""
    return Config()


@pytest.fixture
def ideal_fundamentals():
    """Return fundamental dictionary meeting all 5 criteria."""
    return {
        "pe_ratio": 20.0,
        "revenue_growth": 0.25,
        "profit_margin": 0.15,
        "debt_to_equity": 0.3,
        "roe": 0.20,
    }


@pytest.fixture
def bad_fundamentals():
    """Return fundamental dictionary missing all criteria."""
    return {
        "pe_ratio": 50.0,
        "revenue_growth": 0.05,
        "profit_margin": 0.02,
        "debt_to_equity": 2.5,
        "roe": 0.05,
    }


def test_score_fundamentals_ideal(sample_config, ideal_fundamentals):
    """Test that score_fundamentals returns 5.0 for ideal metrics."""
    score = score_fundamentals(ideal_fundamentals, sample_config)
    assert score == 5.0


def test_score_fundamentals_bad(sample_config, bad_fundamentals):
    """Test that score_fundamentals returns 0.0 for bad metrics."""
    score = score_fundamentals(bad_fundamentals, sample_config)
    assert score == 0.0


def test_score_fundamentals_partial_and_missing(sample_config):
    """Test fundamental scoring with partial, None, missing, or invalid values."""
    # PE and ROE pass, others fail or missing
    partial = {
        "pe_ratio": 15.0,  # pass (< 30)
        "revenue_growth": None,  # missing -> 0
        "profit_margin": "invalid",  # invalid -> 0
        "debt_to_equity": 1.5,  # fail (> 1.0) -> 0
        "roe": 0.22,  # pass (> 0.15)
    }
    score = score_fundamentals(partial, sample_config)
    assert score == 2.0


def test_score_fundamentals_custom_config():
    """Test score_fundamentals with custom Config thresholds."""
    custom_cfg = Config(MAX_PE=15.0, MIN_ROE=0.25)
    fundamentals = {
        "pe_ratio": 20.0,  # Fails custom MAX_PE=15.0
        "revenue_growth": 0.20,  # Passes default 0.15
        "profit_margin": 0.12,  # Passes default 0.10
        "debt_to_equity": 0.5,  # Passes default 1.0
        "roe": 0.20,  # Fails custom MIN_ROE=0.25
    }
    score = score_fundamentals(fundamentals, custom_cfg)
    assert score == 3.0


def test_analyze_stock_multibagger_success(sample_config, ideal_fundamentals):
    """Test analyze_stock returning a valid multibagger result dict."""
    dates = pd.date_range("2021-01-01", periods=100, freq="D")
    adj_close = np.linspace(100.0, 250.0, 100)  # 150% return = 1.5 return_pct
    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": adj_close,
            "High": adj_close + 1.0,
            "Low": adj_close - 1.0,
            "Close": adj_close,
            "Adj Close": adj_close,
            "Volume": np.full(100, 10000.0),
        }
    )

    mock_client = MagicMock()
    mock_client.get_stock_ohlcv.return_value = df
    mock_client.get_stock_name.return_value = "Tata Motors Ltd"
    mock_client.config = sample_config

    scanner = MultibaggerScanner(years=5, data_client=mock_client, config=sample_config)

    with patch.object(scanner, "_fetch_fundamentals", return_value=ideal_fundamentals):
        res = scanner.analyze_stock("TATAMOTORS.NS")

    assert res is not None
    assert res["symbol"] == "TATAMOTORS.NS"
    assert res["return_pct"] == pytest.approx(1.5, abs=1e-4)
    assert res["fundamental_score"] == 5.0
    assert res["is_multibagger"] is True


def test_analyze_stock_uses_adjusted_close(sample_config, ideal_fundamentals):
    """Test that analyze_stock uses Adj Close (handling stock splits) instead of unadjusted Close."""
    dates = pd.date_range("2021-01-01", periods=100, freq="D")
    # Unadjusted Close looks flat due to 1:2 split (100 -> 100)
    unadjusted_close = np.full(100, 100.0)
    # Adjusted Close reflects true split-adjusted price growth (40 -> 100, 150% gain)
    adjusted_close = np.linspace(40.0, 100.0, 100)

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": unadjusted_close,
            "High": unadjusted_close + 1.0,
            "Low": unadjusted_close - 1.0,
            "Close": unadjusted_close,
            "Adj Close": adjusted_close,
            "Volume": np.full(100, 10000.0),
        }
    )

    mock_client = MagicMock()
    mock_client.get_stock_ohlcv.return_value = df
    mock_client.config = sample_config

    scanner = MultibaggerScanner(years=5, data_client=mock_client, config=sample_config)

    with patch.object(scanner, "_fetch_fundamentals", return_value=ideal_fundamentals):
        res = scanner.analyze_stock("SPLITSTOCK.NS")

    assert res is not None
    # If Close was used, return_pct would be 0.0. Adj Close yields (100-40)/40 = 1.5
    assert res["return_pct"] == pytest.approx(1.5, abs=1e-4)


def test_analyze_stock_not_multibagger(sample_config, ideal_fundamentals):
    """Test analyze_stock returning None when return_pct is below MULTIBAGGER_RETURN_THRESHOLD."""
    dates = pd.date_range("2021-01-01", periods=100, freq="D")
    adj_close = np.linspace(100.0, 150.0, 100)  # 50% gain = 0.5 (< 1.0 threshold)
    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": adj_close,
            "High": adj_close,
            "Low": adj_close,
            "Close": adj_close,
            "Adj Close": adj_close,
            "Volume": np.full(100, 5000.0),
        }
    )

    mock_client = MagicMock()
    mock_client.get_stock_ohlcv.return_value = df
    mock_client.config = sample_config

    scanner = MultibaggerScanner(years=5, data_client=mock_client, config=sample_config)

    with patch.object(scanner, "_fetch_fundamentals", return_value=ideal_fundamentals):
        res = scanner.analyze_stock("SLOWSTOCK.NS")

    assert res is None


def test_analyze_stock_missing_or_empty_data(sample_config):
    """Test analyze_stock handling empty/missing data gracefully."""
    mock_client = MagicMock()
    mock_client.get_stock_ohlcv.return_value = None
    mock_client.config = sample_config

    scanner = MultibaggerScanner(years=5, data_client=mock_client, config=sample_config)
    res = scanner.analyze_stock("NODATA.NS")
    assert res is None


def test_scan_multiple_stocks(sample_config, ideal_fundamentals):
    """Test scanner.scan running parallel analysis over multiple symbols."""
    dates = pd.date_range("2021-01-01", periods=50, freq="D")

    # Multi: 100 -> 300 (+200% = 2.0 return_pct)
    df_multi = pd.DataFrame(
        {
            "Date": dates,
            "Close": np.linspace(100.0, 300.0, 50),
            "Adj Close": np.linspace(100.0, 300.0, 50),
        }
    )
    # Slow: 100 -> 120 (+20% = 0.2 return_pct)
    df_slow = pd.DataFrame(
        {
            "Date": dates,
            "Close": np.linspace(100.0, 120.0, 50),
            "Adj Close": np.linspace(100.0, 120.0, 50),
        }
    )

    def mock_ohlcv(symbol, days=None):
        if symbol == "MULTI.NS":
            return df_multi
        elif symbol == "SLOW.NS":
            return df_slow
        return None

    mock_client = MagicMock()
    mock_client.get_stock_ohlcv.side_effect = mock_ohlcv
    mock_client.get_stock_name.side_effect = lambda sym: f"Company {sym}"
    mock_client.config = sample_config

    scanner = MultibaggerScanner(years=5, data_client=mock_client, config=sample_config)

    with patch.object(scanner, "_fetch_fundamentals", return_value=ideal_fundamentals):
        df_results = scanner.scan(["MULTI.NS", "SLOW.NS", "NODATA.NS"])

    assert not df_results.empty
    assert len(df_results) == 1
    assert df_results.iloc[0]["symbol"] == "MULTI.NS"
    assert df_results.iloc[0]["return_pct"] == pytest.approx(2.0, abs=1e-4)


def test_multibagger_result_model():
    """Test MultibaggerResult model creation."""
    res = MultibaggerResult(
        symbol="INFY.NS",
        name="Infosys Ltd",
        pe_ratio=25.0,
        revenue_growth=0.18,
        profit_margin=0.20,
        debt_to_equity=0.0,
        roe=0.28,
        market_cap=600000000000.0,
        return_pct=2.5,
        composite_score=5.0,
    )
    assert res.symbol == "INFY.NS"
    assert res.return_pct == 2.5
    assert res.composite_score == 5.0
