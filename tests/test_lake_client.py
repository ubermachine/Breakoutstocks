"""Unit tests for DataLakeClient."""

import os
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from breakoutstocks.config import Config
from breakoutstocks.data import DataLakeClient
from breakoutstocks.data.lake_client import DataLakeClient as DataLakeClientDirect



@pytest.fixture
def sample_daily_bars():
    dates = pd.date_range(end=pd.Timestamp.now(), periods=10, freq="D")
    df1 = pd.DataFrame({
        "Ticker": ["TCS.NS"] * 10,
        "Date": dates,
        "Open": np.linspace(3000, 3100, 10),
        "High": np.linspace(3050, 3150, 10),
        "Low": np.linspace(2950, 3050, 10),
        "Close": np.linspace(3020, 3120, 10),
        "Volume": [100000] * 10,
    })
    df2 = pd.DataFrame({
        "Ticker": ["INFY.NS"] * 10,
        "Date": dates,
        "Open": np.linspace(1400, 1500, 10),
        "High": np.linspace(1450, 1550, 10),
        "Low": np.linspace(1350, 1450, 10),
        "Close": np.linspace(1420, 1520, 10),
        "Volume": [200000] * 10,
    })
    return pd.concat([df1, df2], ignore_index=True)


@pytest.fixture
def sample_weekly_bars():
    dates = pd.date_range(end=pd.Timestamp.now(), periods=5, freq="W")
    return pd.DataFrame({
        "Ticker": ["TCS.NS"] * 5,
        "Date": dates,
        "Open": np.linspace(3000, 3100, 5),
        "High": np.linspace(3050, 3150, 5),
        "Low": np.linspace(2950, 3050, 5),
        "Close": np.linspace(3020, 3120, 5),
        "Volume": [500000] * 5,
    })


@pytest.fixture
def sample_metadata():
    return pd.DataFrame({
        "Ticker": ["TCS.NS", "INFY.NS", "RELIANCE.NS"],
        "Name": ["Tata Consultancy Services", "Infosys Limited", "Reliance Industries"],
        "Sector": ["IT", "IT", "Energy"],
    })


@pytest.fixture
def sample_sector_bars():
    dates = pd.date_range(end=pd.Timestamp.now(), periods=10, freq="D")
    return pd.DataFrame({
        "Ticker": ["NIFTY_IT"] * 10,
        "Date": dates,
        "Open": np.linspace(35000, 36000, 10),
        "High": np.linspace(35500, 36500, 10),
        "Low": np.linspace(34500, 35500, 10),
        "Close": np.linspace(35200, 36200, 10),
        "Volume": [1000000] * 10,
    })


class TestDataLakeClientInit:
    def test_init_with_explicit_local_path(self):
        client = DataLakeClient(local_path="/custom/lake/path")
        assert client.base_path == "/custom/lake/path"

    def test_init_with_config_lake_path(self, monkeypatch):
        monkeypatch.setattr(Config, "LAKE_PATH", "/config/lake/path")
        client = DataLakeClient()
        assert client.base_path == "/config/lake/path"

    def test_init_fallback_to_github_url(self, monkeypatch):
        monkeypatch.setattr(Config, "LAKE_PATH", None)
        client = DataLakeClient()
        assert client.base_path == Config.LAKE_GITHUB_URL


class TestDataLakeClientMethods:
    @pytest.fixture
    def mock_client(self, sample_daily_bars, sample_weekly_bars, sample_metadata, sample_sector_bars):
        client = DataLakeClient(local_path="/fake/path")
        # Inject mock data loaders directly
        client._daily_bars = sample_daily_bars
        client._weekly_bars = sample_weekly_bars
        client._stock_metadata = sample_metadata
        client._sector_daily_bars = sample_sector_bars
        return client

    def test_get_daily_bars_success(self, mock_client):
        df = mock_client.get_daily_bars("TCS.NS", days=5)
        assert df is not None
        assert len(df) <= 5
        assert (df["Ticker"] == "TCS.NS").all()
        expected_cols = {"Ticker", "Date", "Open", "High", "Low", "Close", "Volume"}
        assert expected_cols.issubset(df.columns)

    def test_get_daily_bars_unknown_symbol(self, mock_client):
        df = mock_client.get_daily_bars("UNKNOWN.NS")
        assert df is None

    def test_get_weekly_bars_success(self, mock_client):
        df = mock_client.get_weekly_bars("TCS.NS")
        assert df is not None
        assert len(df) == 5
        assert (df["Ticker"] == "TCS.NS").all()

    def test_get_weekly_bars_unknown_symbol(self, mock_client):
        df = mock_client.get_weekly_bars("NONEXISTENT.NS")
        assert df is None

    def test_get_stock_metadata(self, mock_client):
        df = mock_client.get_stock_metadata()
        assert df is not None
        assert len(df) == 3
        assert list(df["Ticker"]) == ["TCS.NS", "INFY.NS", "RELIANCE.NS"]

    def test_get_sector_index(self, mock_client):
        df = mock_client.get_sector_index("NIFTY_IT", days=5)
        assert df is not None
        assert len(df) <= 5

    def test_get_sector_index_not_found(self, mock_client):
        df = mock_client.get_sector_index("NIFTY_PHARMA")
        assert df is None

    def test_get_all_tickers(self, mock_client):
        tickers = mock_client.get_all_tickers()
        assert tickers == ["TCS.NS", "INFY.NS", "RELIANCE.NS"]

    def test_get_stock_name_found(self, mock_client):
        name = mock_client.get_stock_name("TCS.NS")
        assert name == "Tata Consultancy Services"

    def test_get_stock_name_missing_fallback(self, mock_client):
        name = mock_client.get_stock_name("UNKNOWN.NS")
        assert name == "UNKNOWN.NS"


class TestDataLakeClientParquetLoading:
    @patch("pandas.read_parquet")
    def test_lazy_loading_local_file(self, mock_read_parquet, sample_daily_bars):
        mock_read_parquet.return_value = sample_daily_bars
        client = DataLakeClient(local_path="d:/fake/lake")

        df = client.get_daily_bars("TCS.NS")
        assert df is not None
        mock_read_parquet.assert_called_once()
        expected_path = os.path.join("d:/fake/lake", "DailyBars.parquet")
        assert mock_read_parquet.call_args[0][0].replace("\\", "/") == expected_path.replace("\\", "/")

    @patch("pandas.read_parquet")
    def test_lazy_loading_github_url(self, mock_read_parquet, sample_daily_bars, monkeypatch):
        monkeypatch.setattr(Config, "LAKE_PATH", None)
        mock_read_parquet.return_value = sample_daily_bars
        client = DataLakeClient()

        df = client.get_daily_bars("TCS.NS")
        assert df is not None
        mock_read_parquet.assert_called_once()
        assert mock_read_parquet.call_args[0][0] == f"{Config.LAKE_GITHUB_URL}/DailyBars.parquet"

    @patch("pandas.read_parquet", side_effect=Exception("Network error"))
    def test_graceful_failure_on_read_error(self, mock_read_parquet):
        client = DataLakeClient(local_path="d:/fake/lake")
        df = client.get_daily_bars("TCS.NS")
        assert df is None
        assert client.get_all_tickers() == []
        assert client.get_stock_name("TCS.NS") == "TCS.NS"
