"""Unified Market Data Client combining data lake and live NSE APIs."""

import logging
from typing import Dict, List, Optional
import pandas as pd

from breakoutstocks.config import Config
from breakoutstocks.data.lake_client import DataLakeClient
from breakoutstocks.data.nse_live import NSELiveClient
from breakoutstocks.models.types import MarketRegime

logger = logging.getLogger(__name__)


class MarketDataClient:
    """Unified facade combining DataLakeClient (OHLCV, metadata) and NSELiveClient (F&O, live APIs)."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize MarketDataClient with optional Config."""
        self.config = config or Config()
        self.lake = DataLakeClient(local_path=self.config.LAKE_PATH)
        self.nse = NSELiveClient()

    def get_stock_ohlcv(self, symbol: str, days: int = 180) -> Optional[pd.DataFrame]:
        """Fetch stock/index OHLCV daily bars.

        Tries data lake first; if unavailable, falls back to yfinance (if enabled).

        Args:
            symbol: Ticker symbol (e.g. 'TCS.NS', '^NSEI', '^INDIAVIX')
            days: Number of lookback days

        Returns:
            pd.DataFrame or None if fetch fails
        """
        # Try DataLakeClient first
        lake_df = self.lake.get_daily_bars(symbol, days=days)
        if lake_df is not None and not lake_df.empty:
            return lake_df

        # Fallback to yfinance if enabled
        if getattr(self.config, "YFINANCE_FALLBACK", True):
            try:
                import yfinance as yf

                symbol_clean = str(symbol).strip()
                if not symbol_clean.startswith("^") and "." not in symbol_clean:
                    yf_symbol = f"{symbol_clean}.NS"
                else:
                    yf_symbol = symbol_clean

                ticker = yf.Ticker(yf_symbol)
                df = ticker.history(period=f"{days}d")
                if df is not None and not df.empty:
                    df = df.reset_index()
                    if "Date" in df.columns:
                        df["Date"] = pd.to_datetime(df["Date"])
                    df["Ticker"] = symbol
                    cols = [
                        c
                        for c in ["Date", "Open", "High", "Low", "Close", "Volume", "Ticker"]
                        if c in df.columns
                    ]
                    return df[cols]
            except Exception as err:
                logger.warning(f"yfinance fallback failed for {symbol}: {err}")

        return None

    def get_stock_name(self, symbol: str) -> str:
        """Get company name for symbol. Delegates to DataLakeClient."""
        return self.lake.get_stock_name(symbol)

    def get_all_nse_tickers(self) -> List[str]:
        """Get list of available stock tickers. Delegates to DataLakeClient."""
        return self.lake.get_all_tickers()

    def get_option_chain(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get option chain snapshot for symbol. Delegates to NSELiveClient."""
        return self.nse.get_option_chain(symbol)

    def get_fii_dii(self) -> Optional[Dict]:
        """Get live FII/DII activity summary. Delegates to NSELiveClient."""
        return self.nse.get_fii_dii()

    def get_fo_ban_list(self) -> List[str]:
        """Get F&O security ban list. Delegates to NSELiveClient."""
        return self.nse.get_fo_ban_list()

    def get_nifty_data(self, days: int = 30) -> Optional[pd.DataFrame]:
        """Get Nifty 50 index daily bars using ^NSEI ticker."""
        return self.get_stock_ohlcv("^NSEI", days=days)

    def get_vix_data(self, days: int = 30) -> Optional[pd.DataFrame]:
        """Get India VIX daily bars using ^INDIAVIX ticker."""
        return self.get_stock_ohlcv("^INDIAVIX", days=days)

    def get_market_regime(self) -> MarketRegime:
        """Aggregate market regime metrics (Nifty trend, VIX change, FII/DII bias, regime score).

        Returns:
            Populated MarketRegime object
        """
        nifty_df = self.get_nifty_data(days=30)
        vix_df = self.get_vix_data(days=30)
        fii_dii = self.get_fii_dii()

        nifty_trend = "SIDEWAYS"
        nifty_change_pct = 0.0
        nifty_above_20_sma = True

        vix_level = 0.0
        vix_change_pct = 0.0
        india_vix_change = 0.0

        fii_net = 0.0
        dii_net = 0.0
        fii_trend = "NEUTRAL"
        dii_trend = "NEUTRAL"
        fii_dii_bias_positive = True

        # Process Nifty data
        if nifty_df is not None and not nifty_df.empty and "Close" in nifty_df.columns:
            closes = nifty_df["Close"].dropna()
            if len(closes) > 0:
                latest_close = float(closes.iloc[-1])
                if len(closes) >= 2:
                    prev_close = float(closes.iloc[-2])
                    if prev_close > 0:
                        nifty_change_pct = float(((latest_close - prev_close) / prev_close) * 100.0)

                sma_20 = float(closes.tail(20).mean())
                nifty_above_20_sma = bool(latest_close >= sma_20)

                if nifty_above_20_sma and nifty_change_pct >= 0:
                    nifty_trend = "BULLISH"
                elif not nifty_above_20_sma and nifty_change_pct < 0:
                    nifty_trend = "BEARISH"
                else:
                    nifty_trend = "SIDEWAYS"

        # Process VIX data
        if vix_df is not None and not vix_df.empty and "Close" in vix_df.columns:
            vix_closes = vix_df["Close"].dropna()
            if len(vix_closes) > 0:
                vix_level = float(vix_closes.iloc[-1])
                if len(vix_closes) >= 2:
                    prev_vix = float(vix_closes.iloc[-2])
                    india_vix_change = float(vix_level - prev_vix)
                    if prev_vix > 0:
                        vix_change_pct = float(((vix_level - prev_vix) / prev_vix) * 100.0)

        # Process FII/DII data
        if isinstance(fii_dii, dict):
            fii_net = float(fii_dii.get("fii_net") or 0.0)
            dii_net = float(fii_dii.get("dii_net") or 0.0)
            fii_trend = str(fii_dii.get("fii_trend") or "NEUTRAL")
            dii_trend = str(fii_dii.get("dii_trend") or "NEUTRAL")
            fii_dii_bias_positive = bool((fii_net + dii_net) > 0)

        # Calculate composite regime_score (0.0 to 10.0 scale)
        base_score = 5.0

        # Nifty component (max +3.0 / -3.0)
        nifty_pts = 0.0
        if nifty_df is not None and not nifty_df.empty:
            if nifty_above_20_sma:
                nifty_pts += 2.0
            else:
                nifty_pts -= 2.0

            if nifty_change_pct > 0.5:
                nifty_pts += 1.0
            elif nifty_change_pct < -0.5:
                nifty_pts -= 1.0
            elif nifty_change_pct > 0.0:
                nifty_pts += 0.5

        # VIX component (max +2.0 / -2.0)
        vix_pts = 0.0
        if vix_df is not None and not vix_df.empty:
            if vix_level > 0:
                if vix_level < 15.0:
                    vix_pts += 1.0
                elif vix_level > 22.0:
                    vix_pts -= 1.0

            if india_vix_change < 0:
                vix_pts += 1.0
            elif india_vix_change > 1.0:
                vix_pts -= 1.0

        # FII/DII component (max +2.0 / -2.0)
        flow_pts = 0.0
        if isinstance(fii_dii, dict):
            if fii_dii_bias_positive:
                flow_pts += 1.5
            else:
                flow_pts -= 1.5

            if fii_trend == "BUY":
                flow_pts += 0.5
            elif fii_trend == "SELL":
                flow_pts -= 0.5

        regime_score = base_score + nifty_pts + vix_pts + flow_pts
        regime_score = max(0.0, min(10.0, float(round(regime_score, 1))))

        return MarketRegime(
            nifty_trend=nifty_trend,
            nifty_change_pct=round(nifty_change_pct, 2),
            vix_level=round(vix_level, 2),
            vix_change_pct=round(vix_change_pct, 2),
            fii_net=round(fii_net, 2),
            dii_net=round(dii_net, 2),
            fii_trend=fii_trend,
            dii_trend=dii_trend,
            regime_score=regime_score,
            nifty_above_20_sma=nifty_above_20_sma,
            india_vix_change=round(india_vix_change, 2),
            fii_dii_bias_positive=fii_dii_bias_positive,
        )
