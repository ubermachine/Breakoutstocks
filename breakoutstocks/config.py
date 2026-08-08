"""Global configuration dataclass and constants."""

import os
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Config:
    """All system configuration constants, endpoints, thresholds, and scoring weights."""

    # Data sources
    LAKE_PATH: Optional[str] = os.environ.get("MARKET_DATA_LAKE_PATH", None)
    LAKE_GITHUB_URL: str = "https://raw.githubusercontent.com/ubermachine/market-data-lake/main/data"
    NSE_OPTION_CHAIN_URL: str = "https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    NSE_FII_DII_URL: str = "https://www.nseindia.com/api/fiidiiTradeReact"
    NSE_FO_BAN_URL: str = "https://nsearchives.nseindia.com/content/fo/fo_secban.csv"
    YFINANCE_FALLBACK: bool = True

    # F&O Scoring weights (max points per section)
    CASH_SCORE_MAX: float = 20.0
    PRICE_SCORE_MAX: float = 20.0
    DELIVERY_SCORE_MAX: float = 10.0
    FUTURES_SCORE_MAX: float = 15.0
    OPTIONS_SCORE_MAX: float = 20.0
    MARKET_SCORE_MAX: float = 10.0
    RISK_PENALTY_MAX: float = 15.0

    # Decision score thresholds
    STRONG_BUY_THRESHOLD: float = 80.0
    BUY_THRESHOLD: float = 65.0
    WATCH_THRESHOLD: float = 50.0
    WAIT_THRESHOLD: float = 35.0

    # Volume and Liquidity thresholds
    MIN_VOLUME: float = 200000.0
    VOLUME_RATIO_THRESHOLD: float = 2.0

    # Cash Score parameters
    CASH_VOL_RATIO_LOW: float = 2.0
    CASH_VOL_RATIO_HIGH: float = 3.0
    CASH_VOL_RATIO_LOW_PTS: float = 8.0
    CASH_VOL_RATIO_HIGH_PTS: float = 4.0
    CASH_AVG_VOL_PTS: float = 4.0
    CASH_BULLISH_CLOSE_PTS: float = 4.0

    # Price Score parameters
    PRICE_BREAKOUT_HIGH_PTS: float = 8.0
    PRICE_CLOSE_ABOVE_PREV_PTS: float = 4.0
    PRICE_ABOVE_EMA_PTS: float = 4.0
    PRICE_RSI_MOMENTUM_PTS: float = 4.0
    RSI_MOMENTUM_MIN: float = 45.0

    # Delivery Score parameters
    DELIVERY_RATIO_MIN: float = 1.3
    DELIVERY_RATIO_PTS: float = 5.0
    DELIVERY_PCT_MIN: float = 0.5
    DELIVERY_PCT_PTS: float = 5.0

    # Futures Score parameters
    FUTURES_CLOSE_UP_PTS: float = 5.0
    FUTURES_OI_UP_PTS: float = 5.0
    FUTURES_PREMIUM_PTS: float = 5.0

    # Options Score parameters
    OPTIONS_PCR_RISING_PTS: float = 5.0
    OPTIONS_PUT_WRITING_PTS: float = 6.0
    OPTIONS_CALL_UNWINDING_PTS: float = 5.0
    OPTIONS_SAFE_IV_PTS: float = 4.0
    IV_PERCENTILE_SAFE_MAX: float = 80.0

    # Market Score parameters
    MARKET_NIFTY_20SMA_PTS: float = 3.0
    MARKET_VIX_DROP_PTS: float = 3.0
    MARKET_FII_DII_PTS: float = 4.0

    # Risk Penalty parameters
    RISK_EARNINGS_PENALTY: float = 10.0
    RISK_FNO_BAN_PENALTY: float = 10.0
    RISK_HIGH_IV_PENALTY: float = 5.0
    RISK_PUT_UNWINDING_PENALTY: float = 5.0
    RISK_RESISTANCE_CLOSE_PENALTY: float = 5.0
    IV_PERCENTILE_EXTREME: float = 90.0
    EARNINGS_RISK_DAYS: int = 3
    RESISTANCE_ATR_MULT: float = 0.5

    # Regime Downgrade & Warnings
    REGIME_DOWNGRADE_STRONG_BUY: float = 10.0
    REGIME_DOWNGRADE_BUY: float = 15.0
    REGIME_DOWNGRADE_OTHER: float = 20.0
    MAX_WARNINGS_FOR_UPPER_TIERS: int = 3

    # Trade Plan parameters
    TRADE_PLAN_ATR_MULT_SL: float = 1.5
    TRADE_PLAN_ATR_MULT_T1: float = 1.5
    TRADE_PLAN_ATR_MULT_T2: float = 2.5
    TRADE_PLAN_PUT_SUPPORT_MULT: float = 1.002
    TRADE_PLAN_CALL_RESISTANCE_MULT: float = 0.998
    DEFAULT_ATR_FALLBACK_MULT: float = 0.02
    DEFAULT_PUT_SUPPORT_FALLBACK_MULT: float = 0.95
    DEFAULT_CALL_RESISTANCE_FALLBACK_MULT: float = 1.05
    DEFAULT_LOW_FALLBACK_MULT: float = 0.98
    DEFAULT_DISTANCE_FALLBACK: float = 999.0
    DEFAULT_ATR_FALLBACK: float = 1.0
    RR_MEDIUM_THRESHOLD: float = 1.5
    RR_SMALL_THRESHOLD: float = 1.2

    # Breakout & Reversal thresholds
    VOLUME_RATIO_BREAKOUT: float = 1.5
    VOLUME_RATIO_SMA_CROSS: float = 1.3
    RSI_OVERSOLD: float = 30.0
    RSI_OVERBOUGHT: float = 70.0
    SIGNAL_STRENGTH_WEIGHTS: Dict[str, float] = field(
        default_factory=lambda: {
            "VERY_STRONG": 4.0,
            "STRONG": 3.0,
            "MODERATE": 2.0,
            "WEAK": 1.0,
        }
    )

    # Fundamental Multibagger criteria
    MAX_PE: float = 30.0
    MIN_REVENUE_GROWTH: float = 0.15
    MIN_PROFIT_MARGIN: float = 0.10
    MAX_DEBT_EQUITY: float = 1.0
    MIN_ROE: float = 0.15
    MULTIBAGGER_RETURN_THRESHOLD: float = 1.0

    # Execution & Directory settings
    MAX_WORKERS: int = 10
    DEFAULT_LOOKBACK_DAYS: int = 180
    OUTPUT_DIR: str = "output"
