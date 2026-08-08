"""Data models and enums for Breakoutstocks."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Advice(Enum):
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    WATCH = "Watch"
    WAIT = "Wait"
    AVOID = "Avoid"


class Confidence(Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass
class TradePlan:
    entry: float
    entry_type: str
    stop_loss: float
    target_1: float
    target_2: float
    risk_reward: float
    position_size: str
    invalidation: str


@dataclass
class StockAnalysis:
    symbol: str
    advice: Advice
    confidence: Confidence
    final_score: float
    trade_plan: Optional[TradePlan] = None
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    name: str = ""
    cash_score: float = 0.0
    price_score: float = 0.0
    delivery_score: float = 0.0
    futures_score: float = 0.0
    options_score: float = 0.0
    market_score: float = 0.0
    risk_penalty: float = 0.0
    component_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class ScanResult:
    symbol: str
    name: str
    signal_type: str
    confidence: float
    current_price: float
    volume_ratio: float
    signals: List[Dict[str, Any]] = field(default_factory=list)
    strength_score: float = 0.0


@dataclass
class MultibaggerResult:
    symbol: str
    name: str
    pe_ratio: float
    revenue_growth: float
    profit_margin: float
    debt_to_equity: float
    roe: float
    market_cap: float
    return_pct: float
    composite_score: float


@dataclass
class MarketRegime:
    nifty_trend: str = "SIDEWAYS"
    nifty_change_pct: float = 0.0
    vix_level: float = 0.0
    vix_change_pct: float = 0.0
    fii_net: float = 0.0
    dii_net: float = 0.0
    fii_trend: str = "NEUTRAL"
    dii_trend: str = "NEUTRAL"
    regime_score: float = 0.0
    nifty_above_20_sma: bool = True
    india_vix_change: float = 0.0
    fii_dii_bias_positive: bool = True
