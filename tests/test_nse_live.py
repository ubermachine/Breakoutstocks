"""Unit tests for NSELiveClient."""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
import requests

from breakoutstocks.config import Config
from breakoutstocks.data import NSELiveClient as PackageNSELiveClient
from breakoutstocks.data.nse_live import NSELiveClient


def test_package_export():
    assert PackageNSELiveClient is NSELiveClient



@pytest.fixture
def mock_session_init():
    """Mock requests.Session.get for initialization."""
    with patch.object(requests.Session, "get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        yield mock_get


class TestNSELiveClientInit:
    def test_init_session_headers_and_cookies(self, mock_session_init):
        client = NSELiveClient()
        assert "User-Agent" in client.session.headers
        assert "Mozilla" in client.session.headers["User-Agent"]
        # Verify visiting nseindia.com to get cookies
        mock_session_init.assert_called_with("https://www.nseindia.com", timeout=10)

    def test_custom_timeout(self, mock_session_init):
        client = NSELiveClient(timeout=15)
        assert client.timeout == 15
        mock_session_init.assert_called_with("https://www.nseindia.com", timeout=15)


class TestNSELiveClientOptionChain:
    @patch.object(requests.Session, "get")
    def test_get_option_chain_success(self, mock_get):
        # Initial response for session init
        init_resp = MagicMock()
        init_resp.status_code = 200

        # API response for option chain
        api_resp = MagicMock()
        api_resp.status_code = 200
        api_resp.json.return_value = {
            "records": {
                "data": [
                    {
                        "strikePrice": 2500,
                        "CE": {"openInterest": 1000, "changeinOpenInterest": 150, "impliedVolatility": 18.5, "lastPrice": 45.2},
                        "PE": {"openInterest": 2000, "changeinOpenInterest": -50, "impliedVolatility": 19.1, "lastPrice": 30.1},
                    },
                    {
                        "strikePrice": 2550,
                        "CE": {"openInterest": 500, "changeinOpenInterest": 20, "impliedVolatility": 17.2, "lastPrice": 20.0},
                    },
                ]
            }
        }
        mock_get.side_effect = [init_resp, api_resp]

        client = NSELiveClient()
        df = client.get_option_chain("RELIANCE")

        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        expected_cols = ["strikePrice", "CE_OI", "CE_changeinOI", "CE_IV", "CE_LTP", "PE_OI", "PE_changeinOI", "PE_IV", "PE_LTP"]
        assert list(df.columns) == expected_cols
        assert df.iloc[0]["strikePrice"] == 2500
        assert df.iloc[0]["CE_OI"] == 1000
        assert df.iloc[0]["PE_LTP"] == 30.1
        # Second row PE missing, should be 0.0 or default
        assert df.iloc[1]["PE_OI"] == 0.0

    @patch.object(requests.Session, "get")
    def test_get_option_chain_network_failure(self, mock_get):
        init_resp = MagicMock()
        init_resp.status_code = 200
        api_resp = MagicMock()
        api_resp.status_code = 500
        mock_get.side_effect = [init_resp, api_resp, api_resp]

        client = NSELiveClient()
        df = client.get_option_chain("RELIANCE")
        assert df is None

    @patch.object(requests.Session, "get")
    def test_get_option_chain_invalid_payload(self, mock_get):
        init_resp = MagicMock()
        init_resp.status_code = 200
        api_resp = MagicMock()
        api_resp.status_code = 200
        api_resp.json.return_value = {"invalid": "structure"}
        mock_get.side_effect = [init_resp, api_resp]

        client = NSELiveClient()
        df = client.get_option_chain("RELIANCE")
        assert df is None


class TestNSELiveClientFIIDII:
    @patch.object(requests.Session, "get")
    def test_get_fii_dii_success(self, mock_get):
        init_resp = MagicMock()
        init_resp.status_code = 200

        api_resp = MagicMock()
        api_resp.status_code = 200
        api_resp.json.return_value = [
            {"category": "FII/FPI *", "buyValue": "1,234.56", "sellValue": "1,000.00", "netValue": "234.56"},
            {"category": "DII **", "buyValue": "500.00", "sellValue": "800.00", "netValue": "-300.00"},
        ]
        mock_get.side_effect = [init_resp, api_resp]

        client = NSELiveClient()
        result = client.get_fii_dii()

        assert result is not None
        assert result["fii_buy"] == 1234.56
        assert result["fii_sell"] == 1000.00
        assert result["fii_net"] == 234.56
        assert result["fii_trend"] == "BUY"
        assert result["dii_buy"] == 500.00
        assert result["dii_sell"] == 800.00
        assert result["dii_net"] == -300.00
        assert result["dii_trend"] == "SELL"

    @patch.object(requests.Session, "get")
    def test_get_fii_dii_network_failure(self, mock_get):
        init_resp = MagicMock()
        init_resp.status_code = 200
        api_resp = MagicMock()
        api_resp.status_code = 500
        mock_get.side_effect = [init_resp, api_resp, api_resp]

        client = NSELiveClient()
        result = client.get_fii_dii()
        assert result is None


class TestNSELiveClientFOBanList:
    @patch.object(requests.Session, "get")
    def test_get_fo_ban_list_success(self, mock_get):
        init_resp = MagicMock()
        init_resp.status_code = 200

        api_resp = MagicMock()
        api_resp.status_code = 200
        api_resp.text = "1,ZEEL\n2,NATIONALUM\n3,GNFC\n"
        mock_get.side_effect = [init_resp, api_resp]

        client = NSELiveClient()
        ban_list = client.get_fo_ban_list()

        assert isinstance(ban_list, list)
        assert set(ban_list) == {"ZEEL", "NATIONALUM", "GNFC"}

    @patch.object(requests.Session, "get")
    def test_get_fo_ban_list_failure(self, mock_get):
        init_resp = MagicMock()
        init_resp.status_code = 200

        api_resp = MagicMock()
        api_resp.status_code = 404
        mock_get.side_effect = [init_resp, api_resp]

        client = NSELiveClient()
        ban_list = client.get_fo_ban_list()
        assert ban_list == []


class TestNSELiveClientSessionRefresh:
    @patch.object(requests.Session, "get")
    def test_403_triggers_refresh_and_retry(self, mock_get):
        init_resp = MagicMock()
        init_resp.status_code = 200

        forbidden_resp = MagicMock()
        forbidden_resp.status_code = 403

        refresh_resp = MagicMock()
        refresh_resp.status_code = 200

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = [
            {"category": "FII/FPI *", "buyValue": "100", "sellValue": "50", "netValue": "50"},
            {"category": "DII **", "buyValue": "80", "sellValue": "80", "netValue": "0"},
        ]

        # Sequence: init -> GET api (403) -> refresh session init (200) -> retry GET api (200)
        mock_get.side_effect = [init_resp, forbidden_resp, refresh_resp, success_resp]

        client = NSELiveClient()
        result = client.get_fii_dii()

        assert result is not None
        assert result["fii_net"] == 50.0
        # Check call count: 1 (init) + 1 (first attempt 403) + 1 (refresh) + 1 (retry success) = 4
        assert mock_get.call_count == 4
