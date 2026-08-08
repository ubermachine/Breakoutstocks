# Task 3 Report: NSE Live Client Implementation

## Status
DONE

## Summary
Successfully implemented `NSELiveClient` in `breakoutstocks/data/nse_live.py` along with unit tests in `tests/test_nse_live.py`. The client fetches live derivatives data from NSE India including:
- Option chains (`https://www.nseindia.com/api/option-chain-equities?symbol={symbol}`)
- FII/DII trade activity (`https://www.nseindia.com/api/fiidiiTradeReact`)
- F&O Ban list (`https://nsearchives.nseindia.com/content/fo/fo_secban.csv`)

It uses a customized `requests.Session` with standard browser headers, auto-populates cookies by visiting `https://www.nseindia.com`, and automatically handles `403 Forbidden` responses by re-acquiring fresh session cookies.

## TDD Cycle Summary

### 1. RED Phase
- Created unit test suite `tests/test_nse_live.py` with 11 tests covering:
  - Session initialization with browser User-Agent headers and initial cookie fetch.
  - Custom timeout configuration.
  - `get_option_chain` parsing valid option chain JSON into structured `pd.DataFrame`.
  - `get_option_chain` returning `None` on network or payload parsing errors.
  - `get_fii_dii` parsing FII & DII trade activity and calculating trends (`BUY`, `SELL`, `NEUTRAL`).
  - `get_fii_dii` returning `None` on network or payload errors.
  - `get_fo_ban_list` parsing CSV list of banned stocks into symbol list.
  - `get_fo_ban_list` returning empty list `[]` on HTTP error.
  - Automatic `403 Forbidden` retry logic triggering session cookie refresh.
  - Package level export test (`from breakoutstocks.data import NSELiveClient`).
- **Initial Test Run Output (RED)**:
  `ModuleNotFoundError: No module named 'breakoutstocks.data.nse_live'`

### 2. GREEN Phase
- Created `breakoutstocks/data/nse_live.py` implementing `NSELiveClient`.
- Updated `breakoutstocks/data/__init__.py` to export `NSELiveClient`.
- **Final Test Run Output (GREEN)**:
  `27 passed in 2.59s` (16 lake client tests + 11 nse live client tests).

## Commits Created
- `7e88c37`: `feat: add NSELiveClient for option chain, FII/DII, and F&O ban list`

## Verification Evidence
```
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\antigravity_sandbox\Breakoutstocks
plugins: anyio-4.14.1, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 27 items

tests\test_lake_client.py ................                               [ 59%]
tests\test_nse_live.py ...........                                       [100%]

============================= 27 passed in 2.59s ==============================
```

## Concerns / Notes
- None. All requirements and interface specifications met.
