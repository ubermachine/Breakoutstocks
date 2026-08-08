# Task 5: Technical Indicators Module

## Files
- Create: `breakoutstocks/indicators/technical.py`
- Create: `tests/test_indicators.py`

## Interfaces
- Consumes: Raw OHLCV DataFrame with columns `Open`, `High`, `Low`, `Close`, `Volume`
- Produces: `calculate_all_indicators(df: pd.DataFrame) -> Optional[pd.DataFrame]` returning enriched DataFrame with:
  - `SMA_20`, `SMA_50`, `SMA_200`
  - `EMA_10`, `EMA_12`, `EMA_26`
  - `MACD`, `MACD_Signal`, `MACD_Hist`
  - `RSI` using Wilder's exponential smoothing (`alpha = 1/14`), NOT simple rolling mean
  - `BB_Upper`, `BB_Middle`, `BB_Lower` (20-period, 2 std dev)
  - `ATR` (14-period Wilder's smoothing)
  - `Volume_SMA_20`, `Volume_Ratio`, `OBV`, `VWAP`
  - `ROC_10`, `ROC_20`
  - `Stoch_K`, `Stoch_D` (14-period Stochastic)
  - `ADX`, `Plus_DI`, `Minus_DI` (14-period)
  - Convenience aliases for scorer: `prev_close`, `prev_high`, `prev_rsi`, `ema_10`, `rsi`, `atr`, `volume_ratio`, `avg_volume_20d`

## Global Constraints
- Python 3.10+ required
- All indicator calculations must reside in `breakoutstocks/indicators/technical.py` (single source of truth)
- Returns None if input DataFrame is None or has len < 50
- RSI must use Wilder's exponential smoothing (EWM `alpha=1/14`), diverging from simple rolling mean
- No division by zero or NaN explosion; fill / handle zero division safely

## Steps (TDD)
1. Write tests in `tests/test_indicators.py`:
   - Returns None for len < 50
   - Returns DataFrame containing all required indicator column names
   - Asserts RSI values are strictly bounded `[0, 100]` and match Wilder's smoothing behavior
   - Asserts Bollinger Bands: `BB_Upper >= BB_Middle >= BB_Lower`
   - Asserts Volume_Ratio calculation: `Volume / Volume_SMA_20`
   - Asserts Stochastic oscillator bounds `[0, 100]`
   - Asserts ATR > 0
2. Run pytest to verify tests fail (RED phase)
3. Implement `breakoutstocks/indicators/technical.py`
4. Run pytest to verify tests pass (GREEN phase)
5. Commit with `git add -A` and `git commit -m "feat: add technical indicators module with Wilder's smoothed RSI"`
