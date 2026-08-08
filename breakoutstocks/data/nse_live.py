"""NSE Live Data Client for option chain, FII/DII activity, and F&O ban list."""

import logging
from typing import Dict, List, Optional
import pandas as pd
import requests

from breakoutstocks.config import Config

logger = logging.getLogger(__name__)


def _parse_float(val) -> float:
    """Safely parse float from numeric or string value containing commas."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    clean_str = str(val).replace(",", "").strip()
    try:
        return float(clean_str)
    except ValueError:
        return 0.0


class NSELiveClient:
    """Client for fetching live derivatives data from NSE India APIs."""

    BASE_URL = "https://www.nseindia.com"

    def __init__(self, timeout: int = 10):
        """Initialize requests session with standard browser headers and initial cookies."""
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": self.BASE_URL,
            }
        )
        self._refresh_session()

    def _refresh_session(self) -> None:
        """Visit NSE home page to establish/refresh session cookies."""
        try:
            self.session.get(self.BASE_URL, timeout=self.timeout)
        except Exception as err:
            logger.warning(f"Failed to refresh NSE session cookies: {err}")

    def _get(self, url: str) -> Optional[requests.Response]:
        """Execute GET request with automatic 403 retry session refresh."""
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 403:
                logger.info("Received 403 Forbidden from NSE. Refreshing session...")
                self._refresh_session()
                resp = self.session.get(url, timeout=self.timeout)

            if resp.status_code == 200:
                return resp
            logger.warning(f"NSE request to {url} returned status code {resp.status_code}")
            return None
        except requests.RequestException as err:
            logger.warning(f"NSE request failed for {url}: {err}")
            return None

    def get_option_chain(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch option chain for a stock/index symbol.

        Args:
            symbol: Stock symbol (e.g., 'RELIANCE', 'TCS')

        Returns:
            pd.DataFrame with option chain metrics or None if request fails
        """
        symbol_clean = str(symbol).strip().upper()
        url = Config.NSE_OPTION_CHAIN_URL.format(symbol=symbol_clean)
        resp = self._get(url)
        if resp is None:
            return None

        try:
            data = resp.json()
            records = data.get("records", {})
            raw_data = records.get("data", [])
            if not isinstance(raw_data, list) or not raw_data:
                return None

            rows = []
            for item in raw_data:
                strike = item.get("strikePrice")
                if strike is None:
                    continue

                ce = item.get("CE", {}) or {}
                pe = item.get("PE", {}) or {}

                rows.append(
                    {
                        "strikePrice": strike,
                        "CE_OI": _parse_float(ce.get("openInterest")),
                        "CE_changeinOI": _parse_float(ce.get("changeinOpenInterest")),
                        "CE_IV": _parse_float(ce.get("impliedVolatility")),
                        "CE_LTP": _parse_float(ce.get("lastPrice")),
                        "PE_OI": _parse_float(pe.get("openInterest")),
                        "PE_changeinOI": _parse_float(pe.get("changeinOpenInterest")),
                        "PE_IV": _parse_float(pe.get("impliedVolatility")),
                        "PE_LTP": _parse_float(pe.get("lastPrice")),
                    }
                )

            if not rows:
                return None

            columns = [
                "strikePrice",
                "CE_OI",
                "CE_changeinOI",
                "CE_IV",
                "CE_LTP",
                "PE_OI",
                "PE_changeinOI",
                "PE_IV",
                "PE_LTP",
            ]
            return pd.DataFrame(rows, columns=columns)
        except Exception as err:
            logger.warning(f"Error parsing option chain JSON for {symbol_clean}: {err}")
            return None

    def get_fii_dii(self) -> Optional[Dict]:
        """Fetch daily FII and DII trading activity summary.

        Returns:
            Dict containing fii_buy, fii_sell, fii_net, fii_trend, dii_buy, dii_sell, dii_net, dii_trend or None
        """
        url = Config.NSE_FII_DII_URL
        resp = self._get(url)
        if resp is None:
            return None

        try:
            data = resp.json()
            if not isinstance(data, list):
                return None

            fii_item = None
            dii_item = None

            for item in data:
                category = str(item.get("category", "")).upper()
                if "FII" in category or "FPI" in category:
                    fii_item = item
                elif "DII" in category:
                    dii_item = item

            if not fii_item and not dii_item:
                return None

            fii_buy = _parse_float(fii_item.get("buyValue")) if fii_item else 0.0
            fii_sell = _parse_float(fii_item.get("sellValue")) if fii_item else 0.0
            fii_net = _parse_float(fii_item.get("netValue")) if fii_item else 0.0

            dii_buy = _parse_float(dii_item.get("buyValue")) if dii_item else 0.0
            dii_sell = _parse_float(dii_item.get("sellValue")) if dii_item else 0.0
            dii_net = _parse_float(dii_item.get("netValue")) if dii_item else 0.0

            fii_trend = "BUY" if fii_net > 0 else ("SELL" if fii_net < 0 else "NEUTRAL")
            dii_trend = "BUY" if dii_net > 0 else ("SELL" if dii_net < 0 else "NEUTRAL")

            return {
                "fii_buy": fii_buy,
                "fii_sell": fii_sell,
                "fii_net": fii_net,
                "dii_buy": dii_buy,
                "dii_sell": dii_sell,
                "dii_net": dii_net,
                "fii_trend": fii_trend,
                "dii_trend": dii_trend,
            }
        except Exception as err:
            logger.warning(f"Error parsing FII/DII data: {err}")
            return None

    def get_fo_ban_list(self) -> List[str]:
        """Fetch the list of stock symbols currently under F&O ban.

        Returns:
            List of banned stock symbol strings
        """
        url = Config.NSE_FO_BAN_URL
        resp = self._get(url)
        if resp is None:
            return []

        try:
            text = resp.text
            banned_symbols = []
            for line in text.splitlines():
                line = line.strip()
                if (
                    not line
                    or "symbol" in line.lower()
                    or "secban" in line.lower()
                    or "security" in line.lower()
                ):
                    continue
                parts = [p.strip().upper() for p in line.split(",") if p.strip()]
                for part in parts:
                    clean_part = part.replace("&", "").replace("-", "").replace("_", "")
                    if clean_part.isalnum() and not clean_part.isdigit() and len(part) >= 2:
                        if part not in banned_symbols:
                            banned_symbols.append(part)
            return banned_symbols
        except Exception as err:
            logger.warning(f"Error parsing F&O ban list CSV: {err}")
            return []
