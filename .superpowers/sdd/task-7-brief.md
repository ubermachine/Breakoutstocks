# Task 7: Base Scanner + Breakout/Reversal Scanner

## Files
- Create: `breakoutstocks/scanners/base.py`
- Create: `breakoutstocks/scanners/breakout_reversal.py`
- Create: `tests/test_breakout_reversal.py`

## Interfaces
- Consumes: `MarketDataClient` (from `breakoutstocks.data.client`), `Config` (from `breakoutstocks.config`), `calculate_all_indicators` (from `breakoutstocks.indicators.technical`), `ScanResult` (from `breakoutstocks.models.types`)
- Produces:
  - `BaseScanner(ABC)` with:
    - `__init__(data_client: Optional[MarketDataClient] = None, config: Optional[Config] = None)`
    - `scan(symbols: List[str], max_workers: int = 10, progress_callback: Optional[Callable] = None) -> pd.DataFrame` (using ThreadPoolExecutor)
    - `analyze_stock(symbol: str) -> Optional[Dict]` (abstract method)
    - `save_results(df: pd.DataFrame, prefix: str) -> str` (saves timestamped CSV into output/ directory)
  - `detect_breakout_signals(df: Optional[pd.DataFrame], symbol: str, config: Optional[Config] = None) -> List[Dict]`
    - Conditions: 20-day high breakout + volume surge (>1.5x), SMA 50 cross + volume (>1.3x), Bollinger breakout + volume, Golden Cross (50 SMA > 200 SMA)
  - `detect_reversal_signals(df: Optional[pd.DataFrame], symbol: str, config: Optional[Config] = None) -> List[Dict]`
    - Conditions: RSI oversold (<30) / overbought (>70) reversal, MACD bullish/bearish crossover, Hammer/Shooting Star candlestick patterns, Price-RSI bullish/bearish divergence
  - `BreakoutReversalScanner(BaseScanner)`:
    - `analyze_stock(symbol: str) -> Optional[Dict]` (fetches OHLCV, calculates indicators, detects breakout and reversal signals, computes weighted strength_score, extracts company name from client, returns result dict)

## Global Constraints
- Python 3.10+ required
- Supports both BSE (e.g. `500325.BO`) and NSE (e.g. `TCS.NS`) symbols
- Must use `calculate_all_indicators` from Task 5 (no duplicate indicator logic)
- Thresholds must come from `Config` (e.g. `VOLUME_RATIO_BREAKOUT`, `VOLUME_RATIO_SMA_CROSS`, `RSI_OVERSOLD`, `RSI_OVERBOUGHT`, `SIGNAL_STRENGTH_WEIGHTS`)

## Steps (TDD)
1. Write `tests/test_breakout_reversal.py` testing:
   - Detecting `BREAKOUT_20DAY_HIGH` on breakout pattern DataFrame
   - Detecting `BREAKOUT_SMA50` on crossover DataFrame
   - Detecting `BOLLINGER_BREAKOUT`
   - Detecting `GOLDEN_CROSS`
   - Detecting `RSI_OVERSOLD_REVERSAL` on oversold DataFrame
   - Detecting `MACD_BULLISH_CROSSOVER`
   - Detecting `HAMMER_PATTERN`
   - Detecting `BULLISH_DIVERGENCE`
   - Testing `BreakoutReversalScanner.analyze_stock` and `scan` with mock MarketDataClient
2. Run pytest to verify tests fail (RED phase)
3. Implement `breakoutstocks/scanners/base.py` and `breakoutstocks/scanners/breakout_reversal.py`
4. Run pytest to verify all tests pass (GREEN phase)
5. Commit with `git add -A` and `git commit -m "feat: add BaseScanner and BreakoutReversalScanner with signal detection"`
