# Task 8: Multibagger Scanner

## Files
- Create: `breakoutstocks/scanners/multibagger.py`
- Create: `tests/test_multibagger.py`

## Interfaces
- Consumes: `BaseScanner` (from `breakoutstocks.scanners.base`), `MarketDataClient` (from `breakoutstocks.data.client`), `Config` (from `breakoutstocks.config`), `MultibaggerResult` (from `breakoutstocks.models.types`)
- Produces:
  - `score_fundamentals(fundamentals: Dict, config: Config) -> float` (scoring 0.0 to 5.0 against PE < 30, revenue growth > 15%, profit margin > 10%, debt/equity < 1.0, ROE > 15%)
  - `MultibaggerScanner(BaseScanner)`:
    - `__init__(years: int = 5, **kwargs)`
    - `analyze_stock(symbol: str) -> Optional[Dict]` (fetches fundamentals and historical price via yfinance or data lake, computes adjusted return over selected year horizon, scores fundamentals, evaluates multibagger threshold >= 100% gain, returns result dict)

## Global Constraints
- Python 3.10+ required
- Fixes legacy corporate action / stock split bug by ensuring Adjusted Close is used for return calculations
- All thresholds from `Config` (`MAX_PE`, `MIN_REVENUE_GROWTH`, `MIN_PROFIT_MARGIN`, `MAX_DEBT_EQUITY`, `MIN_ROE`, `MULTIBAGGER_RETURN_THRESHOLD`)
- Gracefully handles missing fundamental metrics or API rate limits

## Steps (TDD)
1. Write `tests/test_multibagger.py` testing:
   - `score_fundamentals` scoring 5.0 for ideal metrics, 0.0 for bad metrics, and handling None/missing fields
   - `MultibaggerScanner.analyze_stock` calculating correct percentage returns and multibagger flags with mocked yfinance responses
   - `MultibaggerScanner.scan` running over multiple symbols
2. Run pytest to verify tests fail (RED phase)
3. Implement `breakoutstocks/scanners/multibagger.py`
4. Run pytest to verify all tests pass (GREEN phase)
5. Commit with `git add -A` and `git commit -m "feat: add MultibaggerScanner with fundamental scoring and adjusted returns"`
