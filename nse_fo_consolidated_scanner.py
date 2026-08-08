"""
NSE F&O All-in-One Scanner with Consolidated Trading Advice
Test-Driven Development Approach
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import yfinance as yf
from dataclasses import dataclass
from enum import Enum


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
    trade_plan: Optional[TradePlan]
    reasons: List[str]
    warnings: List[str]
    cash_score: float
    price_score: float
    delivery_score: float
    futures_score: float
    options_score: float
    market_score: float
    risk_penalty: float


class TestableScorer:
    """Test-driven scoring engine for NSE F&O stocks"""
    
    def __init__(self):
        self.min_volume = 200000
        self.volume_ratio_threshold = 2.0
        
    def calculate_cash_score(self, row: pd.Series) -> float:
        """Calculate cash market score (0-20 points)"""
        score = 0.0
        
        # Volume burst detection
        if row.get('volume_ratio', 0) > 2.0:
            score += 8.0
        if row.get('volume_ratio', 0) > 3.0:
            score += 4.0
            
        # Average volume filter
        if row.get('avg_volume_20d', 0) > self.min_volume:
            score += 4.0
            
        # Bullish close
        if row.get('close', 0) > row.get('open', 0):
            score += 4.0
            
        return min(score, 20.0)
    
    def calculate_price_score(self, row: pd.Series) -> float:
        """Calculate price reversal score (0-20 points)"""
        score = 0.0
        
        # Breakout above previous high
        if row.get('close', 0) > row.get('prev_high', 0):
            score += 8.0
            
        # Close above previous close
        if row.get('close', 0) > row.get('prev_close', 0):
            score += 4.0
            
        # Above EMA 10
        if row.get('close', 0) > row.get('ema_10', 0):
            score += 4.0
            
        # RSI momentum
        if row.get('rsi', 0) > 45 and row.get('rsi', 0) > row.get('prev_rsi', 0):
            score += 4.0
            
        return min(score, 20.0)
    
    def calculate_delivery_score(self, row: pd.Series) -> float:
        """Calculate delivery confirmation score (0-10 points)"""
        score = 0.0
        
        if row.get('delivery_ratio', 0) > 1.3:
            score += 5.0
            
        if row.get('delivery_pct', 0) > 0.5:
            score += 5.0
            
        return min(score, 10.0)
    
    def calculate_futures_score(self, row: pd.Series) -> float:
        """Calculate futures confirmation score (0-15 points)"""
        score = 0.0
        
        if row.get('futures_close', 0) > row.get('futures_prev_close', 0):
            score += 5.0
            
        if row.get('futures_oi_change', 0) > 0:
            score += 5.0
            
        if row.get('futures_premium', 0) > 0:
            score += 5.0
            
        return min(score, 15.0)
    
    def calculate_options_score(self, row: pd.Series) -> float:
        """Calculate options positioning score (0-20 points)"""
        score = 0.0
        
        # PCR rising
        if row.get('pcr_oi_change', 0) > 0:
            score += 5.0
            
        # Put writing below spot
        if row.get('put_oi_change_below_spot', 0) > 0:
            score += 6.0
            
        # Call unwinding above spot
        if row.get('call_oi_change_above_spot', 0) <= 0:
            score += 5.0
            
        # IV not extreme
        if row.get('atm_iv_percentile', 100) < 80:
            score += 4.0
            
        return min(score, 20.0)
    
    def calculate_market_score(self, row: pd.Series) -> float:
        """Calculate market regime score (0-10 points)"""
        score = 0.0
        
        if row.get('nifty_above_20_sma', False):
            score += 3.0
            
        if row.get('india_vix_change', 0) <= 0:
            score += 3.0
            
        if row.get('fii_dii_bias_positive', False):
            score += 4.0
            
        return min(score, 10.0)
    
    def calculate_risk_penalty(self, row: pd.Series) -> float:
        """Calculate risk penalties (0-15 points)"""
        penalty = 0.0
        
        # Earnings event risk
        if row.get('earnings_within_3_days', False):
            penalty += 10.0
            
        # F&O ban
        if row.get('stock_in_fno_ban', False):
            penalty += 10.0
            
        # High IV
        if row.get('atm_iv_percentile', 0) > 90:
            penalty += 5.0
            
        # Put unwinding
        if row.get('put_oi_change_below_spot', 0) < 0:
            penalty += 5.0
            
        # Call resistance too close
        distance = row.get('distance_to_call_resistance', 999)
        atr = row.get('atr', 1)
        if distance < 0.5 * atr:
            penalty += 5.0
            
        return min(penalty, 15.0)
    
    def calculate_final_score(self, row: pd.Series) -> float:
        """Calculate final consolidated score (0-100)"""
        cash = self.calculate_cash_score(row)
        price = self.calculate_price_score(row)
        delivery = self.calculate_delivery_score(row)
        futures = self.calculate_futures_score(row)
        options = self.calculate_options_score(row)
        market = self.calculate_market_score(row)
        risk = self.calculate_risk_penalty(row)
        
        # Store individual scores
        row['cash_score'] = cash
        row['price_score'] = price
        row['delivery_score'] = delivery
        row['futures_score'] = futures
        row['options_score'] = options
        row['market_score'] = market
        row['risk_penalty'] = risk
        
        final = cash + price + delivery + futures + options + market - risk
        return max(0.0, min(100.0, final))
    
    def generate_advice(self, row: pd.Series) -> Tuple[Advice, List[str]]:
        """Generate final advice based on score and rules"""
        warnings = []
        score = row['final_score']
        
        # Hard vetoes
        if row.get('stock_in_fno_ban', False):
            return Advice.AVOID, ["F&O ban risk"]
            
        if row.get('earnings_within_3_days', False):
            warnings.append("Earnings event risk")
            
        if row.get('atm_iv_percentile', 0) > 90:
            warnings.append("Very high implied volatility")
            
        if row.get('put_oi_change_below_spot', 0) < 0:
            warnings.append("Put writers may be exiting")
            
        distance = row.get('distance_to_call_resistance', 999)
        atr = row.get('atr', 1)
        if distance < 0.5 * atr:
            warnings.append("Call resistance is very close")
        
        # Market regime downgrade
        if not row.get('nifty_above_20_sma', True):
            if score >= 80:
                score -= 10
            elif score >= 65:
                score -= 15
            else:
                score -= 20
        
        # Determine advice
        if score >= 80:
            advice = Advice.STRONG_BUY
        elif score >= 65:
            advice = Advice.BUY
        elif score >= 50:
            advice = Advice.WATCH
        elif score >= 35:
            advice = Advice.WAIT
        else:
            advice = Advice.AVOID
        
        # Downgrade if too many warnings
        if len(warnings) >= 3 and advice in [Advice.STRONG_BUY, Advice.BUY]:
            advice = Advice.WATCH
            
        return advice, warnings
    
    def generate_trade_plan(self, row: pd.Series, advice: Advice) -> Optional[TradePlan]:
        """Generate entry, stop, targets, and risk-reward"""
        if advice not in [Advice.STRONG_BUY, Advice.BUY, Advice.WATCH]:
            return None
            
        close = row.get('close', 0)
        prev_high = row.get('prev_high', close)
        atr = row.get('atr', close * 0.02)
        put_support = row.get('put_support_strike', close * 0.95)
        call_resistance = row.get('call_resistance_strike', close * 1.05)
        low = row.get('low', close * 0.98)
        
        # Entry logic
        if advice in [Advice.STRONG_BUY, Advice.BUY]:
            entry = max(close, prev_high)
            entry_type = "Buy above previous day high"
        else:  # WATCH
            entry = prev_high
            entry_type = "Wait for breakout confirmation"
        
        # Stop loss candidates
        stop_candidates = [
            close - 1.5 * atr,
            low,
        ]
        
        if pd.notna(put_support) and put_support > 0:
            stop_candidates.append(put_support * 1.002)
            
        stop_loss = max(stop_candidates)
        
        # Risk calculation
        risk = entry - stop_loss if entry > stop_loss else atr
        
        # Targets
        target_1 = entry + 1.5 * risk
        target_2 = entry + 2.5 * risk
        
        # Cap targets at resistance
        if pd.notna(call_resistance) and call_resistance > 0:
            target_1 = min(target_1, call_resistance * 0.998)
            
        # Risk-reward ratio
        rr = round((target_1 - entry) / risk, 2) if risk > 0 else 0
        
        # Position size recommendation
        if rr >= 1.5:
            position_size = "Medium"
        elif rr >= 1.2:
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
            invalidation=invalidation
        )
    
    def generate_reasons(self, row: pd.Series) -> List[str]:
        """Generate bullish reasons list"""
        reasons = []
        
        if row.get('volume_ratio', 0) > 2:
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
        """Determine confidence level"""
        if advice == Advice.AVOID:
            return Confidence.LOW
            
        score = row['final_score']
        
        if score >= 80 and len(warnings) == 0:
            return Confidence.HIGH
        elif score >= 65 and len(warnings) <= 1:
            return Confidence.MEDIUM
        else:
            return Confidence.LOW
    
    def analyze_stock(self, row: pd.Series) -> StockAnalysis:
        """Complete analysis for one stock"""
        # Calculate final score
        final_score = self.calculate_final_score(row)
        row['final_score'] = final_score
        
        # Generate advice
        advice, warnings = self.generate_advice(row)
        
        # Generate trade plan
        trade_plan = self.generate_trade_plan(row, advice)
        
        # Generate reasons
        reasons = self.generate_reasons(row)
        
        # Determine confidence
        confidence = self.determine_confidence(row, advice, warnings)
        
        return StockAnalysis(
            symbol=row.get('symbol', 'UNKNOWN'),
            advice=advice,
            confidence=confidence,
            final_score=final_score,
            trade_plan=trade_plan,
            reasons=reasons,
            warnings=warnings,
            cash_score=row['cash_score'],
            price_score=row['price_score'],
            delivery_score=row['delivery_score'],
            futures_score=row['futures_score'],
            options_score=row['options_score'],
            market_score=row['market_score'],
            risk_penalty=row['risk_penalty']
        )


# Test Suite
def test_scoring_engine():
    """Comprehensive test suite for the scoring engine"""
    print("Running Test Suite...")
    print("=" * 60)
    
    scorer = TestableScorer()
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Cash Score Calculation
    print("\n[Test 1] Cash Score Calculation")
    tests_total += 1
    test_row = pd.Series({
        'volume_ratio': 3.5,
        'avg_volume_20d': 300000,
        'close': 100,
        'open': 98
    })
    cash_score = scorer.calculate_cash_score(test_row)
    expected = 20.0  # 8+4+4+4 = 20
    if abs(cash_score - expected) < 0.01:
        print(f"✓ PASSED: Cash score = {cash_score}")
        tests_passed += 1
    else:
        print(f"✗ FAILED: Expected {expected}, got {cash_score}")
    
    # Test 2: Price Score Calculation
    print("\n[Test 2] Price Score Calculation")
    tests_total += 1
    test_row = pd.Series({
        'close': 105,
        'prev_high': 100,
        'prev_close': 102,
        'ema_10': 103,
        'rsi': 55,
        'prev_rsi': 50
    })
    price_score = scorer.calculate_price_score(test_row)
    expected = 20.0  # 8+4+4+4 = 20
    if abs(price_score - expected) < 0.01:
        print(f"✓ PASSED: Price score = {price_score}")
        tests_passed += 1
    else:
        print(f"✗ FAILED: Expected {expected}, got {price_score}")
    
    # Test 3: Options Score Calculation
    print("\n[Test 3] Options Score Calculation")
    tests_total += 1
    test_row = pd.Series({
        'pcr_oi_change': 0.15,
        'put_oi_change_below_spot': 50000,
        'call_oi_change_above_spot': -20000,
        'atm_iv_percentile': 65
    })
    options_score = scorer.calculate_options_score(test_row)
    expected = 20.0  # 5+6+5+4 = 20
    if abs(options_score - expected) < 0.01:
        print(f"✓ PASSED: Options score = {options_score}")
        tests_passed += 1
    else:
        print(f"✗ FAILED: Expected {expected}, got {options_score}")
    
    # Test 4: Risk Penalty Calculation
    print("\n[Test 4] Risk Penalty Calculation")
    tests_total += 1
    test_row = pd.Series({
        'earnings_within_3_days': True,
        'stock_in_fno_ban': False,
        'atm_iv_percentile': 95,
        'put_oi_change_below_spot': -10000,
        'distance_to_call_resistance': 0.3,
        'atr': 2.0
    })
    risk_penalty = scorer.calculate_risk_penalty(test_row)
    expected = 15.0  # 10+5+5 = 20, capped at 15
    if abs(risk_penalty - expected) < 0.01:
        print(f"✓ PASSED: Risk penalty = {risk_penalty}")
        tests_passed += 1
    else:
        print(f"✗ FAILED: Expected {expected}, got {risk_penalty}")
    
    # Test 5: Final Score Clamping
    print("\n[Test 5] Final Score Clamping")
    tests_total += 1
    test_row = pd.Series({
        'volume_ratio': 4.0,
        'avg_volume_20d': 500000,
        'close': 110,
        'open': 105,
        'prev_high': 108,
        'prev_close': 107,
        'ema_10': 106,
        'rsi': 60,
        'prev_rsi': 55,
        'delivery_ratio': 1.5,
        'delivery_pct': 0.6,
        'futures_close': 111,
        'futures_prev_close': 109,
        'futures_oi_change': 100000,
        'futures_premium': 1.0,
        'pcr_oi_change': 0.2,
        'put_oi_change_below_spot': 80000,
        'call_oi_change_above_spot': -30000,
        'atm_iv_percentile': 50,
        'nifty_above_20_sma': True,
        'india_vix_change': -0.5,
        'fii_dii_bias_positive': True,
        'earnings_within_3_days': False,
        'stock_in_fno_ban': False
    })
    final_score = scorer.calculate_final_score(test_row)
    if 0 <= final_score <= 100:
        print(f"✓ PASSED: Final score clamped to [0,100]: {final_score}")
        tests_passed += 1
    else:
        print(f"✗ FAILED: Final score {final_score} out of range")
    
    # Test 6: Advice Generation - Strong Buy
    print("\n[Test 6] Advice Generation - Strong Buy")
    tests_total += 1
    test_row = pd.Series({
        'final_score': 85,
        'stock_in_fno_ban': False,
        'earnings_within_3_days': False,
        'atm_iv_percentile': 60,
        'put_oi_change_below_spot': 50000,
        'distance_to_call_resistance': 5.0,
        'atr': 2.0,
        'nifty_above_20_sma': True
    })
    advice, warnings = scorer.generate_advice(test_row)
    if advice == Advice.STRONG_BUY:
        print(f"✓ PASSED: Advice = {advice.value}")
        tests_passed += 1
    else:
        print(f"✗ FAILED: Expected STRONG_BUY, got {advice.value}")
    
    # Test 7: Advice Generation - Avoid due to F&O Ban
    print("\n[Test 7] Advice Generation - Avoid due to F&O Ban")
    tests_total += 1
    test_row = pd.Series({
        'final_score': 85,
        'stock_in_fno_ban': True,
        'earnings_within_3_days': False,
        'atm_iv_percentile': 60,
        'put_oi_change_below_spot': 50000,
        'distance_to_call_resistance': 5.0,
        'atr': 2.0,
        'nifty_above_20_sma': True
    })
    advice, warnings = scorer.generate_advice(test_row)
    if advice == Advice.AVOID and "F&O ban risk" in warnings:
        print(f"✓ PASSED: Advice = {advice.value}, Warning present")
        tests_passed += 1
    else:
        print(f"✗ FAILED: Expected AVOID with F&O ban warning")
    
    # Test 8: Trade Plan Generation
    print("\n[Test 8] Trade Plan Generation")
    tests_total += 1
    test_row = pd.Series({
        'close': 1000,
        'prev_high': 995,
        'atr': 20,
        'put_support_strike': 970,
        'call_resistance_strike': 1050,
        'low': 990
    })
    trade_plan = scorer.generate_trade_plan(test_row, Advice.BUY)
    if trade_plan and trade_plan.entry > 0 and trade_plan.stop_loss > 0:
        print(f"✓ PASSED: Trade plan generated")
        print(f"  Entry: {trade_plan.entry}, Stop: {trade_plan.stop_loss}")
        print(f"  Target 1: {trade_plan.target_1}, Target 2: {trade_plan.target_2}")
        print(f"  Risk-Reward: {trade_plan.risk_reward}")
        tests_passed += 1
    else:
        print(f"✗ FAILED: Trade plan not generated properly")
    
    # Test 9: Confidence Level
    print("\n[Test 9] Confidence Level")
    tests_total += 1
    test_row = pd.Series({'final_score': 85})
    confidence = scorer.determine_confidence(test_row, Advice.STRONG_BUY, [])
    if confidence == Confidence.HIGH:
        print(f"✓ PASSED: Confidence = {confidence.value}")
        tests_passed += 1
    else:
        print(f"✗ FAILED: Expected HIGH, got {confidence.value}")
    
    # Test 10: Reasons Generation
    print("\n[Test 10] Reasons Generation")
    tests_total += 1
    test_row = pd.Series({
        'volume_ratio': 2.8,
        'close': 105,
        'prev_high': 100,
        'ema_10': 102,
        'rsi': 55,
        'prev_rsi': 50,
        'futures_close': 106,
        'futures_prev_close': 104,
        'put_oi_change_below_spot': 30000,
        'call_oi_change_above_spot': -10000,
        'pcr_oi_change': 0.1,
        'nifty_above_20_sma': True
    })
    reasons = scorer.generate_reasons(test_row)
    if len(reasons) >= 5:
        print(f"✓ PASSED: Generated {len(reasons)} reasons")
        tests_passed += 1
    else:
        print(f"✗ FAILED: Expected at least 5 reasons, got {len(reasons)}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Tests Passed: {tests_passed}/{tests_total}")
    if tests_passed == tests_total:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print(f"⚠️  {tests_total - tests_passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = test_scoring_engine()
    if success:
        print("\n✅ Scoring engine is ready for production use!")
    else:
        print("\n❌ Please fix the failing tests before proceeding.")
