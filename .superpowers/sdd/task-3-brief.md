# Task 3: NSE Live Client

## Files
- Create: `breakoutstocks/data/nse_live.py`
- Create: `tests/test_nse_live.py`

## Interfaces
- Consumes: `Config` from `breakoutstocks.config`
- Produces: `NSELiveClient` with methods:
  - `__init__()` (initializes requests.Session with headers and gets cookies by visiting nseindia.com)
  - `get_option_chain(symbol: str) -> Optional[pd.DataFrame]` (returns DataFrame with strikePrice, CE_OI, CE_changeinOI, CE_IV, CE_LTP, PE_OI, PE_changeinOI, PE_IV, PE_LTP, or None)
  - `get_fii_dii() -> Optional[Dict]` (returns Dict with fii_buy, fii_sell, fii_net, dii_buy, dii_sell, dii_net, fii_trend, dii_trend, or None)
  - `get_fo_ban_list() -> List[str]` (returns list of banned symbol strings)

## Global Constraints
- Python 3.10+ required
- All configuration constants in ONE file: `breakoutstocks/config.py`
- Option chain endpoint: `https://www.nseindia.com/api/option-chain-equities?symbol={symbol}`
- FII/DII endpoint: `https://www.nseindia.com/api/fiidiiTradeReact`
- F&O Ban list endpoint: `https://nsearchives.nseindia.com/content/fo/fo_secban.csv`
- Must handle 403 Forbidden by automatically re-acquiring cookies/session
- All tests must use deterministic mocks (e.g. `unittest.mock.patch` on `requests.Session` methods) to guarantee fast and isolated execution

## Steps (TDD)
1. Write `tests/test_nse_live.py` with mock response data:
   - Test session initialization with custom headers
   - Test `get_option_chain` parsing valid option chain JSON into structured DataFrame
   - Test `get_option_chain` returning None on network failure or invalid payload
   - Test `get_fii_dii` parsing FII/DII response and determining correct trend
   - Test `get_fo_ban_list` parsing CSV list of banned stocks
   - Test 403 retry session refresh logic
2. Run pytest to verify tests fail before implementation
3. Implement `breakoutstocks/data/nse_live.py`
4. Run pytest to verify tests pass
5. Commit with `git add -A` and `git commit -m "feat: add NSELiveClient for option chain, FII/DII, and F&O ban list"`
