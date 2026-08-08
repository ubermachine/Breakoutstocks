# Task 4: Unified MarketDataClient

## Files
- Create: `breakoutstocks/data/client.py`
- Create: `tests/test_client.py`

## Interfaces
- Consumes: `DataLakeClient` (from `breakoutstocks.data.lake_client`), `NSELiveClient` (from `breakoutstocks.data.nse_live`), `Config` (from `breakoutstocks.config`), `MarketRegime` (from `breakoutstocks.models.types`)
- Produces: `MarketDataClient` facade class with methods:
  - `__init__(config: Optional[Config] = None)`
  - `get_stock_ohlcv(symbol: str, days: int = 180) -> Optional[pd.DataFrame]` (tries lake first, then yfinance fallback)
  - `get_stock_name(symbol: str) -> str` (delegates to lake)
  - `get_all_nse_tickers() -> List[str]` (delegates to lake)
  - `get_option_chain(symbol: str) -> Optional[pd.DataFrame]` (delegates to nse_live)
  - `get_fii_dii() -> Optional[Dict]` (delegates to nse_live)
  - `get_fo_ban_list() -> List[str]` (delegates to nse_live)
  - `get_nifty_data(days: int = 30) -> Optional[pd.DataFrame]` (queries "^NSEI" from lake, fallback to yfinance)
  - `get_vix_data(days: int = 30) -> Optional[pd.DataFrame]` (queries "^INDIAVIX" from lake, fallback to yfinance)
  - `get_market_regime() -> MarketRegime` (aggregates nifty trend, 20 SMA check, VIX level & change, FII/DII net & trends into a populated `MarketRegime` dataclass with regime_score 0-10)

## Global Constraints
- Python 3.10+ required
- Nifty ticker is `^NSEI` (fixing legacy `^NSPI` bug)
- India VIX ticker is `^INDIAVIX`
- All tests must use deterministic mocks for data lake and NSE client components

## Steps (TDD)
1. Write unit tests in `tests/test_client.py` covering:
   - Initializing MarketDataClient with default or custom Config
   - `get_stock_ohlcv` with lake hit, lake miss -> yfinance fallback, and complete failure -> None
   - `get_nifty_data` and `get_vix_data` retrieval and fallbacks
   - `get_market_regime` calculations (nifty above 20 SMA check, VIX change, FII/DII positive bias, regime score calculation 0-10)
   - Delegation methods (`get_stock_name`, `get_all_nse_tickers`, `get_option_chain`, `get_fii_dii`, `get_fo_ban_list`)
2. Run pytest to verify test failure (RED phase)
3. Implement `breakoutstocks/data/client.py`
4. Run pytest to verify test passes (GREEN phase)
5. Commit with `git add -A` and `git commit -m "feat: add MarketDataClient unified facade combining lake and live NSE"`
