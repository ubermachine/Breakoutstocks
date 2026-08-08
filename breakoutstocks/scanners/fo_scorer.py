"""F&O Scoring engine (TestableScorer) for Breakoutstocks."""

from typing import List, Optional, Tuple
import numpy as np
import pandas as pd

from breakoutstocks.config import Config
from breakoutstocks.models.types import Advice, Confidence, StockAnalysis, TradePlan


class TestableScorer:
    """Test-driven scoring engine for NSE F&O stocks."""
    __test__ = False

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def calculate_cash_score(self, row: pd.Series) -> float:
        """Calculate cash market score (0-20 points)."""
        score = 0.0
        vol_ratio = row.get('volume_ratio', 0)

        if vol_ratio > self.config.CASH_VOL_RATIO_LOW:
            score += self.config.CASH_VOL_RATIO_LOW_PTS
        if vol_ratio > self.config.CASH_VOL_RATIO_HIGH:
            score += self.config.CASH_VOL_RATIO_HIGH_PTS

        if row.get('avg_volume_20d', 0) > self.config.MIN_VOLUME:
            score += self.config.CASH_AVG_VOL_PTS

        if row.get('close', 0) > row.get('open', 0):
            score += self.config.CASH_BULLISH_CLOSE_PTS

        return min(score, self.config.CASH_SCORE_MAX)

    def calculate_price_score(self, row: pd.Series) -> float:
        """Calculate price reversal score (0-20 points)."""
        score = 0.0
        close = row.get('close', 0)

        if close > row.get('prev_high', 0):
            score += self.config.PRICE_BREAKOUT_HIGH_PTS

        if close > row.get('prev_close', 0):
            score += self.config.PRICE_CLOSE_ABOVE_PREV_PTS

        if close > row.get('ema_10', 0):
            score += self.config.PRICE_ABOVE_EMA_PTS

        rsi = row.get('rsi', 0)
        prev_rsi = row.get('prev_rsi', 0)
        if rsi > self.config.RSI_MOMENTUM_MIN and rsi > prev_rsi:
            score += self.config.PRICE_RSI_MOMENTUM_PTS

        return min(score, self.config.PRICE_SCORE_MAX)

    def calculate_delivery_score(self, row: pd.Series) -> float:
        """Calculate delivery confirmation score (0-10 points)."""
        score = 0.0

        if row.get('delivery_ratio', 0) > self.config.DELIVERY_RATIO_MIN:
            score += self.config.DELIVERY_RATIO_PTS

        if row.get('delivery_pct', 0) > self.config.DELIVERY_PCT_MIN:
            score += self.config.DELIVERY_PCT_PTS

        return min(score, self.config.DELIVERY_SCORE_MAX)

    def calculate_futures_score(self, row: pd.Series) -> float:
        """Calculate futures confirmation score (0-15 points)."""
        score = 0.0

        if row.get('futures_close', 0) > row.get('futures_prev_close', 0):
            score += self.config.FUTURES_CLOSE_UP_PTS

        if row.get('futures_oi_change', 0) > 0:
            score += self.config.FUTURES_OI_UP_PTS

        if row.get('futures_premium', 0) > 0:
            score += self.config.FUTURES_PREMIUM_PTS

        return min(score, self.config.FUTURES_SCORE_MAX)

    def calculate_options_score(self, row: pd.Series) -> float:
        """Calculate options positioning score (0-20 points)."""
        score = 0.0

        if row.get('pcr_oi_change', 0) > 0:
            score += self.config.OPTIONS_PCR_RISING_PTS

        if row.get('put_oi_change_below_spot', 0) > 0:
            score += self.config.OPTIONS_PUT_WRITING_PTS

        if row.get('call_oi_change_above_spot', 0) <= 0:
            score += self.config.OPTIONS_CALL_UNWINDING_PTS

        if row.get('atm_iv_percentile', 100) < self.config.IV_PERCENTILE_SAFE_MAX:
            score += self.config.OPTIONS_SAFE_IV_PTS

        return min(score, self.config.OPTIONS_SCORE_MAX)

    def calculate_market_score(self, row: pd.Series) -> float:
        """Calculate market regime score (0-10 points)."""
        score = 0.0

        if row.get('nifty_above_20_sma', False):
            score += self.config.MARKET_NIFTY_20SMA_PTS

        if row.get('india_vix_change', 0) <= 0:
            score += self.config.MARKET_VIX_DROP_PTS

        if row.get('fii_dii_bias_positive', False):
            score += self.config.MARKET_FII_DII_PTS

        return min(score, self.config.MARKET_SCORE_MAX)

    def calculate_risk_penalty(self, row: pd.Series) -> float:
        """Calculate risk penalties (0-15 points)."""
        penalty = 0.0

        if row.get('earnings_within_3_days', False):
            penalty += self.config.RISK_EARNINGS_PENALTY

        if row.get('stock_in_fno_ban', False):
            penalty += self.config.RISK_FNO_BAN_PENALTY

        if row.get('atm_iv_percentile', 0) > self.config.IV_PERCENTILE_EXTREME:
            penalty += self.config.RISK_HIGH_IV_PENALTY

        if row.get('put_oi_change_below_spot', 0) < 0:
            penalty += self.config.RISK_PUT_UNWINDING_PENALTY

        distance = row.get('distance_to_call_resistance', 999)
        atr = row.get('atr', 1)
        if distance < self.config.RESISTANCE_ATR_MULT * atr:
            penalty += self.config.RISK_RESISTANCE_CLOSE_PENALTY

        return min(penalty, self.config.RISK_PENALTY_MAX)

    def calculate_final_score(self, row: pd.Series) -> float:
        """Calculate final consolidated score (0-100)."""
        cash = self.calculate_cash_score(row)
        price = self.calculate_price_score(row)
        delivery = self.calculate_delivery_score(row)
        futures = self.calculate_futures_score(row)
        options = self.calculate_options_score(row)
        market = self.calculate_market_score(row)
        risk = self.calculate_risk_penalty(row)

        row['cash_score'] = cash
        row['price_score'] = price
        row['delivery_score'] = delivery
        row['futures_score'] = futures
        row['options_score'] = options
        row['market_score'] = market
        row['risk_penalty'] = risk

        final = cash + price + delivery + futures + options + market - risk
        return float(np.clip(final, 0.0, 100.0))

    def generate_advice(self, row: pd.Series) -> Tuple[Advice, List[str]]:
        """Generate final advice based on score and rules."""
        warnings = []
        score = float(row.get('final_score', 0.0))

        # Hard vetoes
        if row.get('stock_in_fno_ban', False):
            return Advice.AVOID, ["F&O ban risk"]

        if row.get('earnings_within_3_days', False):
            warnings.append("Earnings event risk")

        if row.get('atm_iv_percentile', 0) > self.config.IV_PERCENTILE_EXTREME:
            warnings.append("Very high implied volatility")

        if row.get('put_oi_change_below_spot', 0) < 0:
            warnings.append("Put writers may be exiting")

        distance = row.get('distance_to_call_resistance', 999)
        atr = row.get('atr', 1)
        if distance < self.config.RESISTANCE_ATR_MULT * atr:
            warnings.append("Call resistance is very close")

        # Market regime downgrade
        if not row.get('nifty_above_20_sma', True):
            if score >= self.config.STRONG_BUY_THRESHOLD:
                score -= self.config.REGIME_DOWNGRADE_STRONG_BUY
            elif score >= self.config.BUY_THRESHOLD:
                score -= self.config.REGIME_DOWNGRADE_BUY
            else:
                score -= self.config.REGIME_DOWNGRADE_OTHER

        # Determine advice
        if score >= self.config.STRONG_BUY_THRESHOLD:
            advice = Advice.STRONG_BUY
        elif score >= self.config.BUY_THRESHOLD:
            advice = Advice.BUY
        elif score >= self.config.WATCH_THRESHOLD:
            advice = Advice.WATCH
        elif score >= self.config.WAIT_THRESHOLD:
            advice = Advice.WAIT
        else:
            advice = Advice.AVOID

        # Downgrade if too many warnings
        if len(warnings) >= self.config.MAX_WARNINGS_FOR_UPPER_TIERS and advice in [Advice.STRONG_BUY, Advice.BUY]:
            advice = Advice.WATCH

        return advice, warnings

    def generate_trade_plan(self, row: pd.Series, advice: Advice) -> Optional[TradePlan]:
        """Generate entry, stop, targets, and risk-reward."""
        if advice not in [Advice.STRONG_BUY, Advice.BUY, Advice.WATCH]:
            return None

        close = float(row.get('close', 0.0))
        prev_high = float(row.get('prev_high', close))
        atr = float(row.get('atr', close * 0.02))
        put_support = float(row.get('put_support_strike', close * 0.95))
        call_resistance = float(row.get('call_resistance_strike', close * 1.05))
        low = float(row.get('low', close * 0.98))

        # Entry logic
        if advice in [Advice.STRONG_BUY, Advice.BUY]:
            entry = max(close, prev_high)
            entry_type = "Buy above previous day high"
        else:  # WATCH
            entry = prev_high
            entry_type = "Wait for breakout confirmation"

        # Stop loss candidates
        stop_candidates = [
            close - self.config.TRADE_PLAN_ATR_MULT_SL * atr,
            low,
        ]

        if pd.notna(put_support) and put_support > 0:
            stop_candidates.append(put_support * self.config.TRADE_PLAN_PUT_SUPPORT_MULT)

        stop_loss = max(stop_candidates)

        # Risk calculation
        risk = entry - stop_loss if entry > stop_loss else atr

        # Targets
        target_1 = entry + self.config.TRADE_PLAN_ATR_MULT_T1 * risk
        target_2 = entry + self.config.TRADE_PLAN_ATR_MULT_T2 * risk

        # Cap targets at resistance
        if pd.notna(call_resistance) and call_resistance > 0:
            target_1 = min(target_1, call_resistance * self.config.TRADE_PLAN_CALL_RESISTANCE_MULT)

        # Risk-reward ratio
        rr = round((target_1 - entry) / risk, 2) if risk > 0 else 0.0

        # Position size recommendation
        if rr >= self.config.RR_MEDIUM_THRESHOLD:
            position_size = "Medium"
        elif rr >= self.config.RR_SMALL_THRESHOLD:
            position_size = "Small"
        else:
            position_size = "Very Small"

        # Invalidation conditions
        invalidation = f"Close below {stop_loss:.2f} or put support breaks"

        return TradePlan(
            entry=round(entry, 2),
            entry_type=entry_type,
            stop_loss=round(stop_loss, 2),
            target_1=round(target_1, 2),
            target_2=round(target_2, 2),
            risk_reward=rr,
            position_size=position_size,
            invalidation=invalidation,
        )

    def generate_reasons(self, row: pd.Series) -> List[str]:
        """Generate bullish reasons list."""
        reasons = []

        if row.get('volume_ratio', 0) > self.config.VOLUME_RATIO_THRESHOLD:
            reasons.append(f"Volume burst: {row['volume_ratio']:.2f}x average")

        if row.get('close', 0) > row.get('prev_high', 0):
            reasons.append("Closed above previous high")

        if row.get('close', 0) > row.get('ema_10', 0):
            reasons.append("Above 10 EMA")

        if row.get('rsi', 0) > row.get('prev_rsi', 0):
            reasons.append("RSI rising")

        if row.get('futures_close', 0) > row.get('futures_prev_close', 0):
            reasons.append("Futures price supportive")

        if row.get('put_oi_change_below_spot', 0) > 0:
            reasons.append("Put OI increasing below spot")

        if row.get('call_oi_change_above_spot', 0) <= 0:
            reasons.append("Call OI not aggressive above spot")

        if row.get('pcr_oi_change', 0) > 0:
            reasons.append("PCR rising")

        if row.get('nifty_above_20_sma', False):
            reasons.append("Market trend positive")

        if not reasons:
            reasons.append("No strong bullish confirmation found")

        return reasons

    def determine_confidence(self, row: pd.Series, advice: Advice, warnings: List[str]) -> Confidence:
        """Determine confidence level."""
        if advice == Advice.AVOID:
            return Confidence.LOW

        score = float(row.get('final_score', 0.0))

        if score >= self.config.STRONG_BUY_THRESHOLD and len(warnings) == 0:
            return Confidence.HIGH
        elif score >= self.config.BUY_THRESHOLD and len(warnings) <= 1:
            return Confidence.MEDIUM
        else:
            return Confidence.LOW

    def analyze_stock(self, row: pd.Series) -> StockAnalysis:
        """Complete analysis pipeline for one stock."""
        final_score = self.calculate_final_score(row)
        row['final_score'] = final_score

        advice, warnings = self.generate_advice(row)
        trade_plan = self.generate_trade_plan(row, advice)
        reasons = self.generate_reasons(row)
        confidence = self.determine_confidence(row, advice, warnings)

        return StockAnalysis(
            symbol=row.get('symbol', 'UNKNOWN'),
            advice=advice,
            confidence=confidence,
            final_score=final_score,
            trade_plan=trade_plan,
            reasons=reasons,
            warnings=warnings,
            cash_score=float(row.get('cash_score', 0.0)),
            price_score=float(row.get('price_score', 0.0)),
            delivery_score=float(row.get('delivery_score', 0.0)),
            futures_score=float(row.get('futures_score', 0.0)),
            options_score=float(row.get('options_score', 0.0)),
            market_score=float(row.get('market_score', 0.0)),
            risk_penalty=float(row.get('risk_penalty', 0.0)),
        )
