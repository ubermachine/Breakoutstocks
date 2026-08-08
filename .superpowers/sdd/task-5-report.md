# Task 5 Report: Technical Indicators Module

**Date:** 2026-08-09
**Status:** DONE
**Module:** `breakoutstocks/indicators/technical.py`
**Test Suite:** `tests/test_indicators.py`

---

## Executive Summary

Task 5 has been successfully implemented following strict Test-Driven Development (TDD). The `breakoutstocks/indicators/technical.py` module now serves as the project's single source of truth for computing technical indicators on OHLCV market data.

Key achievements:
- Implemented `calculate_all_indicators(df: pd.DataFrame) -> Optional[pd.DataFrame]` returning enriched DataFrame with all required indicator columns.
- Replaced simple rolling mean RSI with Wilder's exponential smoothing (`alpha = 1/14`), bounded `[0, 100]` with robust zero-division handling.
- Implemented moving averages (SMA_20, SMA_50, SMA_200, EMA_10, EMA_12, EMA_26), MACD (Line, Signal, Hist), Bollinger Bands (Upper, Middle, Lower), 14-period Wilder's ATR, Volume metrics (Volume_SMA_20, Volume_Ratio, OBV, VWAP), Momentum (ROC_10, ROC_20, Stoch_K, Stoch_D), and Trend metrics (ADX, Plus_DI, Minus_DI).
- Provided convenience aliases required by downstream scorers (`prev_close`, `prev_high`, `prev_rsi`, `ema_10`, `rsi`, `atr`, `volume_ratio`, `avg_volume_20d`).
- Comprehensive unit tests added to `tests/test_indicators.py` verifying bounds, calculations, ordering, and edge cases.

---

## TDD Workflow & Output

### 1. RED Phase (Initial Test Run)
Tests were written first in `tests/test_indicators.py`. Running `python -m pytest tests/test_indicators.py` failed as expected because the module did not exist yet:

```text
=================================== ERRORS ====================================
__________________ ERROR collecting tests/test_indicators.py __________________
ImportError while importing test module 'D:\antigravity_sandbox\Breakoutstocks\tests\test_indicators.py'.
...
ModuleNotFoundError: No module named 'breakoutstocks.indicators.technical'
=========================== short test summary info ===========================
ERROR tests/test_indicators.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

### 2. Implementation
Created `breakoutstocks/indicators/technical.py` with vectorised pandas/numpy calculations, incorporating Wilder's smoothing for RSI, ATR, and ADX/DI indicators. Updated `breakoutstocks/indicators/__init__.py` to export `calculate_all_indicators`.

### 3. GREEN Phase (Verification)
Executed `python -m pytest` across the entire project repository:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\antigravity_sandbox\Breakoutstocks
plugins: anyio-4.14.1, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False

collected 53 items

tests\test_client.py .................                                   [ 32%]
tests\test_indicators.py .........                                       [ 49%]
tests\test_lake_client.py ................                               [ 79%]
tests\test_nse_live.py ...........                                       [100%]

============================= 53 passed in 5.72s ==============================
```

---

## Implemented Indicators Summary

| Category | Indicators / Columns | Formula / Logic |
|---|---|---|
| Input Validation | `df is None or len(df) < 50` | Returns `None` |
| Moving Averages | `SMA_20`, `SMA_50`, `SMA_200`, `EMA_10`, `EMA_12`, `EMA_26` | Standard rolling mean / ewm span |
| MACD | `MACD`, `MACD_Signal`, `MACD_Hist` | `EMA_12 - EMA_26`, `EMA_9(MACD)`, `MACD - Signal` |
| RSI | `RSI` | Wilder's smoothing `ewm(alpha=1/14, adjust=False)` |
| Volatility | `BB_Upper`, `BB_Middle`, `BB_Lower`, `ATR` | 20-period 2σ BB; 14-period Wilder's ATR |
| Volume | `Volume_SMA_20`, `Volume_Ratio`, `OBV`, `VWAP` | Rolling vol mean, ratio, cumulative OBV & VWAP |
| Momentum | `ROC_10`, `ROC_20`, `Stoch_K`, `Stoch_D` | % change, 14-period Stochastic %K and 3-period SMA %D |
| Trend | `ADX`, `Plus_DI`, `Minus_DI` | 14-period smoothed Directional Indicators and ADX |
| Aliases | `prev_close`, `prev_high`, `prev_rsi`, `ema_10`, `rsi`, `atr`, `volume_ratio`, `avg_volume_20d` | Direct column aliases and shift(1) references |

---

## Git Commit Information

- **Commit Hash:** `e2969facc724f76a358774d4818cb836c33b9c31`
- **Commit Message:** `feat: add technical indicators module with Wilder's smoothed RSI`
