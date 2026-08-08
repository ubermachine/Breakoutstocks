"""Global configuration dataclass and constants."""

import os
from dataclasses import dataclass
from typing import Optional


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

    # Breakout & Reversal thresholds
    VOLUME_RATIO_BREAKOUT: float = 1.5
    VOLUME_RATIO_SMA_CROSS: float = 1.3
    RSI_OVERSOLD: float = 30.0
    RSI_OVERBOUGHT: float = 70.0

    # Fundamental Multibagger criteria
    MAX_PE: float = 30.0
    MIN_REVENUE_GROWTH: float = 0.15
    MIN_PROFIT_MARGIN: float = 0.10
    MAX_DEBT_EQUITY: float = 1.0
    MIN_ROE: float = 0.15

    # Execution & Directory settings
    MAX_WORKERS: int = 10
    DEFAULT_LOOKBACK_DAYS: int = 180
    OUTPUT_DIR: str = "output"
