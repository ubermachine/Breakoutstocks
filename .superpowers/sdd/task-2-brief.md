# Task 2: Data Lake Client

## Files
- Create: `breakoutstocks/data/lake_client.py`
- Create: `tests/test_lake_client.py`

## Interfaces
- Consumes: `Config` from `breakoutstocks.config`
- Produces: `DataLakeClient` with methods:
  - `__init__(local_path: Optional[str] = None)`
  - `get_daily_bars(symbol: str, days: int = 180) -> Optional[pd.DataFrame]`
  - `get_weekly_bars(symbol: str) -> Optional[pd.DataFrame]`
  - `get_stock_metadata() -> Optional[pd.DataFrame]`
  - `get_sector_index(index: str, days: int = 30) -> Optional[pd.DataFrame]`
  - `get_all_tickers() -> List[str]`
  - `get_stock_name(symbol: str) -> str`

## Global Constraints
- Python 3.10+ required
- Data lake URL: `https://raw.githubusercontent.com/ubermachine/market-data-lake/main/data`
- Parquet files: `DailyBars.parquet`, `WeeklyBars.parquet`, `SectorDailyBars.parquet`, `StockMetadatas.parquet`
- DailyBars columns: `Ticker` (e.g. `"TCS.NS"`), `Date`, `Open`, `High`, `Low`, `Close`, `Volume`
- StockMetadatas columns: `Ticker`, `Name`, `Sector`
- All tests must use deterministic mocks or graceful handling if network unavailable

## Steps (TDD)
1. Write `tests/test_lake_client.py` testing:
   - Init with local_path vs GitHub URL
   - `get_daily_bars` returns DataFrame with Open, High, Low, Close, Volume
   - `get_all_tickers` returns list of ticker strings
   - `get_stock_metadata` returns DataFrame
   - `get_stock_name` returns company name
2. Run pytest to verify tests fail before implementation
3. Implement `breakoutstocks/data/lake_client.py`
4. Run pytest to verify tests pass
5. Commit with `git add -A` and `git commit -m "feat: add DataLakeClient for market-data-lake integration"`
