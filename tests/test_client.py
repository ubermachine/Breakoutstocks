"""Unit tests for MarketDataClient facade."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from breakoutstocks.config import Config
from breakoutstocks.models.types import MarketRegime


@pytest.fixture
def sample_ohlcv():
    dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq="D")
    return pd.DataFrame({
        "Date": dates,
        "Open": np.linspace(100, 110, 30),
        "High": np.linspace(102, 112, 30),
        "Low": np.linspace(98, 108, 30),
        "Close": np.linspace(101, 111, 30),
        "Volume": [500000] * 30,
        "Ticker": ["TCS.NS"] * 30,
    })


@pytest.fixture
def nifty_sample_data():
    dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq="D")
    close_vals = np.linspace(24000, 25000, 30)
    return pd.DataFrame({
        "Date": dates,
        "Open": close_vals - 50,
        "High": close_vals + 100,
        "Low": close_vals - 100,
        "Close": close_vals,
        "Volume": [1000000] * 30,
        "Ticker": ["^NSEI"] * 30,
    })


@pytest.fixture
def vix_sample_data():
    dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq="D")
    close_vals = np.linspace(16, 13, 30)
    return pd.DataFrame({
        "Date": dates,
        "Open": close_vals + 0.2,
        "High": close_vals + 0.5,
        "Low": close_vals - 0.5,
        "Close": close_vals,
        "Volume": [0] * 30,
        "Ticker": ["^INDIAVIX"] * 30,
    })


def test_package_export():
    """Verify MarketDataClient is exported from breakoutstocks.data."""
    from breakoutstocks.data import MarketDataClient as ExportedClient
    from breakoutstocks.data.client import MarketDataClient
    assert ExportedClient is MarketDataClient


class TestMarketDataClientInit:
    def test_init_default_config(self):
        from breakoutstocks.data.client import MarketDataClient
        client = MarketDataClient()
        assert isinstance(client.config, Config)
        assert client.lake is not None
        assert client.nse is not None

    def test_init_custom_config(self):
        from breakoutstocks.data.client import MarketDataClient
        custom_cfg = Config(LAKE_PATH="/custom/lake")
        client = MarketDataClient(config=custom_cfg)
        assert client.config.LAKE_PATH == "/custom/lake"
        assert client.lake.base_path == "/custom/lake"


class TestGetStockOHLCV:
    @patch("breakoutstocks.data.lake_client.DataLakeClient.get_daily_bars")
    def test_get_stock_ohlcv_lake_hit(self, mock_get_daily_bars, sample_ohlcv):
        from breakoutstocks.data.client import MarketDataClient
        mock_get_daily_bars.return_value = sample_ohlcv
        client = MarketDataClient()

        df = client.get_stock_ohlcv("TCS.NS", days=30)
        assert df is not None
        assert len(df) == 30
        mock_get_daily_bars.assert_called_once_with("TCS.NS", days=30)

    @patch("breakoutstocks.data.lake_client.DataLakeClient.get_daily_bars", return_value=None)
    @patch("yfinance.Ticker")
    def test_get_stock_ohlcv_yfinance_fallback_success(self, mock_yf_ticker, mock_get_daily_bars, sample_ohlcv):
        from breakoutstocks.data.client import MarketDataClient
        mock_instance = MagicMock()
        mock_instance.history.return_value = sample_ohlcv
        mock_yf_ticker.return_value = mock_instance

        client = MarketDataClient()
        df = client.get_stock_ohlcv("TCS", days=30)

        assert df is not None
        mock_get_daily_bars.assert_called_once_with("TCS", days=30)
        mock_yf_ticker.assert_called_once_with("TCS.NS")

    @patch("breakoutstocks.data.lake_client.DataLakeClient.get_daily_bars", return_value=None)
    @patch("yfinance.Ticker")
    def test_get_stock_ohlcv_complete_failure(self, mock_yf_ticker, mock_get_daily_bars):
        from breakoutstocks.data.client import MarketDataClient
        mock_instance = MagicMock()
        mock_instance.history.return_value = pd.DataFrame()
        mock_yf_ticker.return_value = mock_instance

        client = MarketDataClient()
        df = client.get_stock_ohlcv("UNKNOWN", days=30)
        assert df is None

    @patch("breakoutstocks.data.lake_client.DataLakeClient.get_daily_bars", return_value=None)
    def test_get_stock_ohlcv_fallback_disabled(self, mock_get_daily_bars):
        from breakoutstocks.data.client import MarketDataClient
        cfg = Config(YFINANCE_FALLBACK=False)
        client = MarketDataClient(config=cfg)

        with patch("yfinance.Ticker") as mock_yf:
            df = client.get_stock_ohlcv("TCS", days=30)
            assert df is None
            mock_yf.assert_not_called()


class TestDelegationMethods:
    @patch("breakoutstocks.data.lake_client.DataLakeClient.get_stock_name", return_value="Tata Consultancy Services")
    def test_get_stock_name(self, mock_name):
        from breakoutstocks.data.client import MarketDataClient
        client = MarketDataClient()
        assert client.get_stock_name("TCS.NS") == "Tata Consultancy Services"
        mock_name.assert_called_once_with("TCS.NS")

    @patch("breakoutstocks.data.lake_client.DataLakeClient.get_all_tickers", return_value=["TCS.NS", "INFY.NS"])
    def test_get_all_nse_tickers(self, mock_tickers):
        from breakoutstocks.data.client import MarketDataClient
        client = MarketDataClient()
        assert client.get_all_nse_tickers() == ["TCS.NS", "INFY.NS"]
        mock_tickers.assert_called_once()

    @patch("breakoutstocks.data.nse_live.NSELiveClient.get_option_chain")
    def test_get_option_chain(self, mock_option_chain):
        from breakoutstocks.data.client import MarketDataClient
        mock_df = pd.DataFrame({"strikePrice": [2500]})
        mock_option_chain.return_value = mock_df
        client = MarketDataClient()

        res = client.get_option_chain("RELIANCE")
        assert res is not None
        assert res.iloc[0]["strikePrice"] == 2500
        mock_option_chain.assert_called_once_with("RELIANCE")

    @patch("breakoutstocks.data.nse_live.NSELiveClient.get_fii_dii")
    def test_get_fii_dii(self, mock_fii_dii):
        from breakoutstocks.data.client import MarketDataClient
        sample_dict = {"fii_net": 500.0, "dii_net": 200.0}
        mock_fii_dii.return_value = sample_dict
        client = MarketDataClient()

        res = client.get_fii_dii()
        assert res == sample_dict
        mock_fii_dii.assert_called_once()

    @patch("breakoutstocks.data.nse_live.NSELiveClient.get_fo_ban_list")
    def test_get_fo_ban_list(self, mock_ban_list):
        from breakoutstocks.data.client import MarketDataClient
        mock_ban_list.return_value = ["ZEEL", "GNFC"]
        client = MarketDataClient()

        res = client.get_fo_ban_list()
        assert res == ["ZEEL", "GNFC"]
        mock_ban_list.assert_called_once()


class TestIndexQueries:
    def test_get_nifty_data_uses_nsei(self, nifty_sample_data):
        from breakoutstocks.data.client import MarketDataClient
        with patch.object(MarketDataClient, "get_stock_ohlcv") as mock_get_ohlcv:
            mock_get_ohlcv.return_value = nifty_sample_data
            client = MarketDataClient()

            df = client.get_nifty_data(days=30)
            assert df is not None
            mock_get_ohlcv.assert_called_once_with("^NSEI", days=30)

    def test_get_vix_data_uses_indiavix(self, vix_sample_data):
        from breakoutstocks.data.client import MarketDataClient
        with patch.object(MarketDataClient, "get_stock_ohlcv") as mock_get_ohlcv:
            mock_get_ohlcv.return_value = vix_sample_data
            client = MarketDataClient()

            df = client.get_vix_data(days=30)
            assert df is not None
            mock_get_ohlcv.assert_called_once_with("^INDIAVIX", days=30)


class TestGetMarketRegime:
    def test_bullish_market_regime(self, nifty_sample_data, vix_sample_data):
        from breakoutstocks.data.client import MarketDataClient
        with patch.object(MarketDataClient, "get_nifty_data", return_value=nifty_sample_data), \
             patch.object(MarketDataClient, "get_vix_data", return_value=vix_sample_data), \
             patch.object(MarketDataClient, "get_fii_dii", return_value={"fii_net": 1500.0, "dii_net": 500.0, "fii_trend": "BUY", "dii_trend": "BUY"}):

            client = MarketDataClient()
            regime = client.get_market_regime()

            assert isinstance(regime, MarketRegime)
            assert regime.nifty_above_20_sma is True
            assert regime.nifty_trend == "BULLISH"
            assert regime.fii_dii_bias_positive is True
            assert regime.fii_net == 1500.0
            assert regime.dii_net == 500.0
            assert regime.vix_level == pytest.approx(13.0, rel=1e-2)
            assert regime.regime_score >= 7.0

    def test_bearish_market_regime(self):
        from breakoutstocks.data.client import MarketDataClient
        dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq="D")
        nifty_falling = pd.DataFrame({"Date": dates, "Close": np.linspace(25000, 23000, 30)})
        vix_rising = pd.DataFrame({"Date": dates, "Close": np.linspace(13, 22, 30)})

        with patch.object(MarketDataClient, "get_nifty_data", return_value=nifty_falling), \
             patch.object(MarketDataClient, "get_vix_data", return_value=vix_rising), \
             patch.object(MarketDataClient, "get_fii_dii", return_value={"fii_net": -2000.0, "dii_net": -500.0, "fii_trend": "SELL", "dii_trend": "SELL"}):

            client = MarketDataClient()
            regime = client.get_market_regime()

            assert isinstance(regime, MarketRegime)
            assert regime.nifty_above_20_sma is False
            assert regime.nifty_trend == "BEARISH"
            assert regime.fii_dii_bias_positive is False
            assert regime.regime_score <= 3.0

    def test_graceful_missing_data_regime(self):
        from breakoutstocks.data.client import MarketDataClient
        with patch.object(MarketDataClient, "get_nifty_data", return_value=None), \
             patch.object(MarketDataClient, "get_vix_data", return_value=None), \
             patch.object(MarketDataClient, "get_fii_dii", return_value=None):

            client = MarketDataClient()
            regime = client.get_market_regime()

            assert isinstance(regime, MarketRegime)
            assert regime.nifty_trend == "SIDEWAYS"
            assert regime.regime_score == 5.0
