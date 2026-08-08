"""Multibagger Scanner module with fundamental scoring and adjusted return calculation."""

import logging
import math
from typing import Dict, Optional

import pandas as pd

from breakoutstocks.config import Config
from breakoutstocks.data.client import MarketDataClient
from breakoutstocks.scanners.base import BaseScanner

logger = logging.getLogger(__name__)


def _safe_float(val: Any) -> Optional[float]:
    """Safely parse value to float, returning None on failure or NaN."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else f
    except (ValueError, TypeError):
        return None


def score_fundamentals(fundamentals: Dict, config: Optional[Config] = None) -> float:
    """Evaluate fundamental metrics against Config thresholds.

    Scoring (0.0 to 5.0):
    - PE ratio > 0 and < MAX_PE (30.0) -> +1.0
    - Revenue growth > MIN_REVENUE_GROWTH (0.15) -> +1.0
    - Profit margin > MIN_PROFIT_MARGIN (0.10) -> +1.0
    - Debt to Equity >= 0 and < MAX_DEBT_EQUITY (1.0) -> +1.0
    - ROE > MIN_ROE (0.15) -> +1.0

    Args:
        fundamentals: Dictionary containing fundamental metrics.
        config: Optional Config instance.

    Returns:
        float fundamental score between 0.0 and 5.0.
    """
    cfg = config or Config()
    score = 0.0

    # 1. PE Ratio (< MAX_PE and > 0)
    pe = _safe_float(
        fundamentals.get("pe_ratio")
        or fundamentals.get("pe")
        or fundamentals.get("trailingPE")
    )
    if pe is not None and 0.0 < pe < cfg.MAX_PE:
        score += 1.0

    # 2. Revenue Growth (> MIN_REVENUE_GROWTH)
    rev_growth = _safe_float(
        fundamentals.get("revenue_growth")
        or fundamentals.get("revenueGrowth")
    )
    if rev_growth is not None and rev_growth > cfg.MIN_REVENUE_GROWTH:
        score += 1.0

    # 3. Profit Margin (> MIN_PROFIT_MARGIN)
    margin = _safe_float(
        fundamentals.get("profit_margin")
        or fundamentals.get("profitMargin")
        or fundamentals.get("profitMargins")
    )
    if margin is not None and margin > cfg.MIN_PROFIT_MARGIN:
        score += 1.0

    # 4. Debt to Equity (< MAX_DEBT_EQUITY and >= 0)
    d_e = _safe_float(
        fundamentals.get("debt_to_equity")
        or fundamentals.get("debtToEquity")
        or fundamentals.get("debt_equity")
    )
    if d_e is not None and 0.0 <= d_e < cfg.MAX_DEBT_EQUITY:
        score += 1.0

    # 5. ROE (> MIN_ROE)
    roe = _safe_float(
        fundamentals.get("roe")
        or fundamentals.get("returnOnEquity")
    )
    if roe is not None and roe > cfg.MIN_ROE:
        score += 1.0

    return float(score)


class MultibaggerScanner(BaseScanner):
    """Scanner to identify multibagger stocks based on adjusted price return and fundamentals."""

    def __init__(
        self,
        years: int = 5,
        data_client: Optional[MarketDataClient] = None,
        config: Optional[Config] = None,
        **kwargs,
    ):
        """Initialize MultibaggerScanner.

        Args:
            years: Number of historical years to evaluate for multibagger return.
            data_client: Optional MarketDataClient instance.
            config: Optional Config instance.
        """
        super().__init__(data_client=data_client, config=config, **kwargs)
        self.years = years

    def _fetch_fundamentals(self, symbol: str) -> Dict:
        """Fetch fundamental metrics for symbol using yfinance with safety fallbacks.

        Args:
            symbol: Ticker symbol.

        Returns:
            Dictionary containing fundamental metric values.
        """
        symbol_clean = str(symbol).strip()
        if not symbol_clean.startswith("^") and "." not in symbol_clean:
            yf_symbol = f"{symbol_clean}.NS"
        else:
            yf_symbol = symbol_clean

        fundamentals: Dict = {
            "symbol": symbol,
            "name": self.data.get_stock_name(symbol) if self.data else symbol,
            "pe_ratio": None,
            "revenue_growth": None,
            "profit_margin": None,
            "debt_to_equity": None,
            "roe": None,
            "market_cap": None,
        }

        try:
            import yfinance as yf

            ticker = yf.Ticker(yf_symbol)
            info = ticker.info or {}

            fundamentals["name"] = (
                info.get("shortName")
                or info.get("longName")
                or fundamentals["name"]
            )
            fundamentals["pe_ratio"] = info.get("trailingPE") or info.get("pe_ratio")
            fundamentals["revenue_growth"] = info.get("revenueGrowth") or info.get("revenue_growth")
            fundamentals["profit_margin"] = info.get("profitMargins") or info.get("profit_margin")

            d_e = info.get("debtToEquity") if info.get("debtToEquity") is not None else info.get("debt_to_equity")
            if d_e is not None:
                try:
                    d_e_val = float(d_e)
                    # If debtToEquity returned as percentage (e.g. 50.0 = 50%), convert to decimal
                    if d_e_val > 10.0:
                        d_e_val = d_e_val / 100.0
                    fundamentals["debt_to_equity"] = d_e_val
                except (ValueError, TypeError):
                    fundamentals["debt_to_equity"] = None

            fundamentals["roe"] = info.get("returnOnEquity") or info.get("roe")
            fundamentals["market_cap"] = info.get("marketCap") or info.get("market_cap")
        except Exception as err:
            logger.warning(f"Error fetching fundamentals for {symbol}: {err}")

        return fundamentals

    def analyze_stock(self, symbol: str) -> Optional[Dict]:
        """Analyze a stock symbol for multibagger characteristics.

        Fetches historical OHLCV data over `self.years` horizon, computes percentage returns
        using **Adjusted Close** (accounting for corporate actions and stock splits), scores
        fundamental metrics, and checks if return_pct >= MULTIBAGGER_RETURN_THRESHOLD.

        Args:
            symbol: Ticker symbol to analyze.

        Returns:
            Dictionary of scan results if stock meets criteria, else None.
        """
        days = self.years * 365
        df = self.data.get_stock_ohlcv(symbol, days=days)

        if df is None or df.empty or len(df) < 2:
            return None

        # Determine Adjusted Close series to account for corporate actions & splits
        adj_col = None
        for col in ["Adj Close", "Adj_Close", "adjusted_close", "Close"]:
            if col in df.columns:
                adj_col = col
                break

        if not adj_col:
            return None

        prices = df[adj_col].dropna()
        if len(prices) < 2:
            return None

        start_price = float(prices.iloc[0])
        latest_price = float(prices.iloc[-1])

        if start_price <= 0:
            return None

        return_pct = (latest_price - start_price) / start_price

        # Threshold check from Config
        threshold = getattr(self.config, "MULTIBAGGER_RETURN_THRESHOLD", 1.0)
        if return_pct < threshold:
            return None

        fundamentals = self._fetch_fundamentals(symbol)
        fund_score = score_fundamentals(fundamentals, self.config)

        pe = _safe_float(fundamentals.get("pe_ratio")) or 0.0
        rev_g = _safe_float(fundamentals.get("revenue_growth")) or 0.0
        p_margin = _safe_float(fundamentals.get("profit_margin")) or 0.0
        d_e = _safe_float(fundamentals.get("debt_to_equity")) or 0.0
        roe = _safe_float(fundamentals.get("roe")) or 0.0
        market_cap = _safe_float(fundamentals.get("market_cap")) or 0.0
        name = str(fundamentals.get("name") or self.data.get_stock_name(symbol))

        return {
            "symbol": symbol,
            "name": name,
            "pe_ratio": pe,
            "revenue_growth": rev_g,
            "profit_margin": p_margin,
            "debt_to_equity": d_e,
            "roe": roe,
            "market_cap": market_cap,
            "return_pct": return_pct,
            "fundamental_score": fund_score,
            "composite_score": fund_score,
            "strength_score": fund_score,
            "is_multibagger": True,
        }
