"""Breakout and Reversal Scanner module."""

import logging
from typing import Dict, List, Optional

import pandas as pd

from breakoutstocks.config import Config
from breakoutstocks.indicators.technical import calculate_all_indicators
from breakoutstocks.scanners.base import BaseScanner

logger = logging.getLogger(__name__)


def _ensure_indicators(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Ensure technical indicators exist in DataFrame."""
    if df is None or len(df) < 50:
        return None

    required_cols = ["SMA_50", "SMA_200", "BB_Upper", "RSI", "MACD", "MACD_Signal", "Volume_Ratio"]
    if not all(col in df.columns for col in required_cols):
        return calculate_all_indicators(df)
    return df


def detect_breakout_signals(
    df: Optional[pd.DataFrame], symbol: str, config: Optional[Config] = None
) -> List[Dict]:
    """Detect breakout pattern signals.

    Args:
        df: Enriched or raw OHLCV DataFrame.
        symbol: Ticker symbol.
        config: Optional Config instance.

    Returns:
        List of detected breakout signal dictionaries.
    """
    signals: List[Dict] = []
    df_ind = _ensure_indicators(df)
    if df_ind is None or len(df_ind) < 50:
        return signals

    cfg = config or Config()
    vol_breakout_thresh = cfg.VOLUME_RATIO_BREAKOUT
    vol_sma_cross_thresh = cfg.VOLUME_RATIO_SMA_CROSS

    latest = df_ind.iloc[-1]
    prev = df_ind.iloc[-2] if len(df_ind) > 1 else latest

    adx = latest.get("ADX", 0)
    if adx < getattr(cfg, "ADX_TREND_MIN", 20.0):
        return signals

    # 1. BREAKOUT_20DAY_HIGH
    if len(df_ind) >= 21:
        high_20 = df_ind["High"].iloc[-21:-1].max()
        if latest["Close"] > high_20 and latest.get("Volume_Ratio", 0.0) > vol_breakout_thresh:
            signals.append(
                {
                    "type": "BREAKOUT_20DAY_HIGH",
                    "strength": "STRONG" if latest.get("Volume_Ratio", 0.0) > 2.0 else "MODERATE",
                    "description": f"Price broke above 20-day high ({high_20:.2f}) with {latest.get('Volume_Ratio', 0.0):.2f}x volume",
                }
            )

    # 2. BREAKOUT_SMA50
    if "SMA_50" in df_ind.columns:
        if (
            latest["Close"] > latest["SMA_50"]
            and prev["Close"] <= prev["SMA_50"]
            and latest.get("Volume_Ratio", 0.0) > vol_sma_cross_thresh
        ):
            signals.append(
                {
                    "type": "BREAKOUT_SMA50",
                    "strength": "STRONG" if latest.get("Volume_Ratio", 0.0) > 2.0 else "MODERATE",
                    "description": f"Price crossed above 50-day SMA ({latest['SMA_50']:.2f}) with volume confirmation",
                }
            )

    # 3. BOLLINGER_BREAKOUT
    if "BB_Upper" in df_ind.columns:
        if (
            latest["Close"] > latest["BB_Upper"]
            and latest.get("Volume_Ratio", 0.0) > vol_breakout_thresh
        ):
            signals.append(
                {
                    "type": "BOLLINGER_BREAKOUT",
                    "strength": "STRONG",
                    "description": f"Price broke above upper Bollinger Band ({latest['BB_Upper']:.2f})",
                }
            )

    # 4. GOLDEN_CROSS
    if len(df_ind) >= 200 and "SMA_50" in df_ind.columns and "SMA_200" in df_ind.columns:
        prev_sma50 = prev["SMA_50"]
        prev_sma200 = prev["SMA_200"]
        curr_sma50 = latest["SMA_50"]
        curr_sma200 = latest["SMA_200"]

        if prev_sma50 <= prev_sma200 and curr_sma50 > curr_sma200:
            signals.append(
                {
                    "type": "GOLDEN_CROSS",
                    "strength": "VERY_STRONG",
                    "description": "Golden Cross detected - 50-day SMA crossed above 200-day SMA",
                }
            )

    return signals


def detect_reversal_signals(
    df: Optional[pd.DataFrame], symbol: str, config: Optional[Config] = None
) -> List[Dict]:
    """Detect trend reversal signals.

    Args:
        df: Enriched or raw OHLCV DataFrame.
        symbol: Ticker symbol.
        config: Optional Config instance.

    Returns:
        List of detected reversal signal dictionaries.
    """
    signals: List[Dict] = []
    df_ind = _ensure_indicators(df)
    if df_ind is None or len(df_ind) < 50:
        return signals

    cfg = config or Config()
    rsi_oversold_thresh = cfg.RSI_OVERSOLD
    rsi_overbought_thresh = cfg.RSI_OVERBOUGHT

    latest = df_ind.iloc[-1]
    prev = df_ind.iloc[-2] if len(df_ind) > 1 else latest

    # 1. RSI Oversold/Overbought Reversal
    if "RSI" in df_ind.columns:
        curr_rsi = latest["RSI"]
        prev_rsi = prev["RSI"]

        if curr_rsi < rsi_oversold_thresh and prev_rsi < (rsi_oversold_thresh + 10.0):
            signals.append(
                {
                    "type": "RSI_OVERSOLD_REVERSAL",
                    "strength": "MODERATE" if curr_rsi > 25.0 else "STRONG",
                    "description": f"RSI oversold at {curr_rsi:.2f}, potential bullish reversal",
                }
            )
        elif curr_rsi > rsi_overbought_thresh and prev_rsi > (rsi_overbought_thresh - 10.0):
            signals.append(
                {
                    "type": "RSI_OVERBOUGHT_REVERSAL",
                    "strength": "MODERATE" if curr_rsi < 75.0 else "STRONG",
                    "description": f"RSI overbought at {curr_rsi:.2f}, potential bearish reversal",
                }
            )

    # 2. MACD Crossover
    if "MACD" in df_ind.columns and "MACD_Signal" in df_ind.columns:
        curr_macd = latest["MACD"]
        curr_sig = latest["MACD_Signal"]
        prev_macd = prev["MACD"]
        prev_sig = prev["MACD_Signal"]

        if curr_macd > curr_sig and prev_macd <= prev_sig:
            signals.append(
                {
                    "type": "MACD_BULLISH_CROSSOVER",
                    "strength": "MODERATE",
                    "description": "MACD bullish crossover detected",
                }
            )
        elif curr_macd < curr_sig and prev_macd >= prev_sig:
            signals.append(
                {
                    "type": "MACD_BEARISH_CROSSOVER",
                    "strength": "MODERATE",
                    "description": "MACD bearish crossover detected",
                }
            )

    # 3. Hammer / Shooting Star Candlestick Patterns
    body = abs(latest["Close"] - latest["Open"])
    range_hl = latest["High"] - latest["Low"]
    lower_shadow = min(latest["Open"], latest["Close"]) - latest["Low"]
    upper_shadow = latest["High"] - max(latest["Open"], latest["Close"])

    if range_hl > 0:
        # Hammer (Bullish Reversal)
        if lower_shadow >= 2 * body and upper_shadow < body and prev["Close"] < prev["Open"]:
            signals.append(
                {
                    "type": "HAMMER_PATTERN",
                    "strength": "MODERATE",
                    "description": "Hammer candlestick pattern - potential bullish reversal",
                }
            )
        # Shooting Star (Bearish Reversal)
        elif upper_shadow >= 2 * body and lower_shadow < body and prev["Close"] > prev["Open"]:
            signals.append(
                {
                    "type": "SHOOTING_STAR_PATTERN",
                    "strength": "MODERATE",
                    "description": "Shooting Star candlestick pattern - potential bearish reversal",
                }
            )

    # 4. Price-RSI Divergence
    if len(df_ind) >= 30 and "RSI" in df_ind.columns:
        price_trend = latest["Close"] - df_ind["Close"].iloc[-10]
        rsi_trend = latest["RSI"] - df_ind["RSI"].iloc[-10]

        if price_trend < 0 and rsi_trend > 0:
            signals.append(
                {
                    "type": "BULLISH_DIVERGENCE",
                    "strength": "STRONG",
                    "description": "Bullish divergence: Price down but RSI up",
                }
            )
        elif price_trend > 0 and rsi_trend < 0:
            signals.append(
                {
                    "type": "BEARISH_DIVERGENCE",
                    "strength": "STRONG",
                    "description": "Bearish divergence: Price up but RSI down",
                }
            )

    return signals


class BreakoutReversalScanner(BaseScanner):
    """Scanner for detecting breakout and reversal signals on stock universe."""

    def analyze_stock(self, symbol: str) -> Optional[Dict]:
        """Analyze a single stock symbol for breakout and reversal patterns.

        Args:
            symbol: Ticker symbol (e.g. 'TCS.NS' or '500325.BO').

        Returns:
            Dictionary of analysis result or None if no signals / invalid data.
        """
        try:
            df = self.data.get_stock_ohlcv(symbol, days=self.config.DEFAULT_LOOKBACK_DAYS)
            if df is None or len(df) < 50:
                return None

            df_ind = calculate_all_indicators(df)
            if df_ind is None or len(df_ind) < 50:
                return None

            breakout_signals = detect_breakout_signals(df_ind, symbol, self.config)
            reversal_signals = detect_reversal_signals(df_ind, symbol, self.config)
            all_signals = breakout_signals + reversal_signals

            if not all_signals:
                return None

            weights = getattr(
                self.config,
                "SIGNAL_STRENGTH_WEIGHTS",
                {"VERY_STRONG": 4.0, "STRONG": 3.0, "MODERATE": 2.0, "WEAK": 1.0},
            )
            strength_score = sum(weights.get(s.get("strength", "WEAK"), 1.0) for s in all_signals)

            if breakout_signals and reversal_signals:
                signal_type = "BREAKOUT_AND_REVERSAL"
            elif breakout_signals:
                signal_type = "BREAKOUT"
            else:
                signal_type = "REVERSAL"

            company_name = self.data.get_stock_name(symbol)
            latest = df_ind.iloc[-1]
            prev = df_ind.iloc[-2] if len(df_ind) > 1 else latest

            current_price = float(round(latest["Close"], 2))
            prev_close = float(prev["Close"])
            change_pct = (
                float(round(((current_price / prev_close) - 1.0) * 100.0, 2))
                if prev_close > 0
                else 0.0
            )

            return {
                "symbol": symbol,
                "name": company_name,
                "company_name": company_name,
                "signal_type": signal_type,
                "current_price": current_price,
                "change_percent": change_pct,
                "volume": int(latest["Volume"]),
                "volume_ratio": float(round(latest.get("Volume_Ratio", 0.0), 2)),
                "rsi": float(round(latest.get("RSI", 0.0), 2)),
                "macd": float(round(latest.get("MACD", 0.0), 4)),
                "signals": all_signals,
                "signal_count": len(all_signals),
                "strength_score": float(round(strength_score, 2)),
            }

        except Exception as err:
            self.logger.warning(f"Error analyzing stock {symbol}: {err}")
            return None
