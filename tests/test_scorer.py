"""Unit tests for TestableScorer in breakoutstocks.scanners.fo_scorer."""

import pandas as pd
import pytest
from breakoutstocks.config import Config
from breakoutstocks.models.types import Advice, Confidence, StockAnalysis, TradePlan
from breakoutstocks.scanners.fo_scorer import TestableScorer


def test_cash_score():
    scorer = TestableScorer()
    test_row = pd.Series({
        'volume_ratio': 3.5,
        'avg_volume_20d': 300000,
        'close': 100,
        'open': 98
    })
    cash_score = scorer.calculate_cash_score(test_row)
    assert abs(cash_score - 20.0) < 0.01


def test_price_score():
    scorer = TestableScorer()
    test_row = pd.Series({
        'close': 105,
        'prev_high': 100,
        'prev_close': 102,
        'ema_10': 103,
        'rsi': 55,
        'prev_rsi': 50
    })
    price_score = scorer.calculate_price_score(test_row)
    assert abs(price_score - 20.0) < 0.01


def test_options_score():
    scorer = TestableScorer()
    test_row = pd.Series({
        'pcr_oi_change': 0.15,
        'put_oi_change_below_spot': 50000,
        'call_oi_change_above_spot': -20000,
        'atm_iv_percentile': 65
    })
    options_score = scorer.calculate_options_score(test_row)
    assert abs(options_score - 20.0) < 0.01


def test_risk_penalty():
    scorer = TestableScorer()
    test_row = pd.Series({
        'earnings_within_3_days': True,
        'stock_in_fno_ban': False,
        'atm_iv_percentile': 95,
        'put_oi_change_below_spot': -10000,
        'distance_to_call_resistance': 0.3,
        'atr': 2.0
    })
    risk_penalty = scorer.calculate_risk_penalty(test_row)
    assert abs(risk_penalty - 15.0) < 0.01


def test_final_score_clamping():
    scorer = TestableScorer()
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
    assert 0.0 <= final_score <= 100.0


def test_advice_generation_strong_buy():
    scorer = TestableScorer()
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
    assert advice == Advice.STRONG_BUY


def test_advice_generation_avoid_fno_ban():
    scorer = TestableScorer()
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
    assert advice == Advice.AVOID
    assert "F&O ban risk" in warnings


def test_trade_plan_generation():
    scorer = TestableScorer()
    test_row = pd.Series({
        'close': 1000,
        'prev_high': 995,
        'atr': 20,
        'put_support_strike': 970,
        'call_resistance_strike': 1050,
        'low': 990
    })
    trade_plan = scorer.generate_trade_plan(test_row, Advice.BUY)
    assert trade_plan is not None
    assert trade_plan.entry > 0
    assert trade_plan.stop_loss > 0
    assert trade_plan.target_1 > 0
    assert trade_plan.target_2 > 0
    assert trade_plan.risk_reward > 0


def test_confidence_level():
    scorer = TestableScorer()
    test_row = pd.Series({'final_score': 85})
    confidence = scorer.determine_confidence(test_row, Advice.STRONG_BUY, [])
    assert confidence == Confidence.HIGH


def test_reasons_generation():
    scorer = TestableScorer()
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
    assert len(reasons) >= 5


def test_analyze_stock_pipeline():
    scorer = TestableScorer()
    test_row = pd.Series({
        'symbol': 'RELIANCE',
        'volume_ratio': 3.5,
        'avg_volume_20d': 500000,
        'close': 2500,
        'open': 2450,
        'prev_high': 2480,
        'prev_close': 2460,
        'ema_10': 2470,
        'rsi': 65,
        'prev_rsi': 60,
        'delivery_ratio': 1.5,
        'delivery_pct': 0.6,
        'futures_close': 2510,
        'futures_prev_close': 2470,
        'futures_oi_change': 10000,
        'futures_premium': 10.0,
        'pcr_oi_change': 0.2,
        'put_oi_change_below_spot': 50000,
        'call_oi_change_above_spot': -10000,
        'atm_iv_percentile': 50,
        'nifty_above_20_sma': True,
        'india_vix_change': -0.2,
        'fii_dii_bias_positive': True,
        'earnings_within_3_days': False,
        'stock_in_fno_ban': False,
        'atr': 40,
        'put_support_strike': 2400,
        'call_resistance_strike': 2700,
        'low': 2460
    })
    analysis = scorer.analyze_stock(test_row)
    assert isinstance(analysis, StockAnalysis)
    assert analysis.symbol == 'RELIANCE'
    assert analysis.advice == Advice.STRONG_BUY
    assert analysis.confidence == Confidence.HIGH
    assert analysis.final_score >= 80.0
    assert analysis.trade_plan is not None
    assert len(analysis.reasons) >= 5


def test_custom_config_injection():
    custom_cfg = Config(CASH_SCORE_MAX=50.0, CASH_VOL_RATIO_LOW_PTS=25.0)
    scorer = TestableScorer(config=custom_cfg)
    test_row = pd.Series({
        'volume_ratio': 2.5,
        'avg_volume_20d': 100000,
        'close': 100,
        'open': 100
    })
    score = scorer.calculate_cash_score(test_row)
    assert score == 25.0
