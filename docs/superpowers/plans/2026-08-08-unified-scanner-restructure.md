# Breakoutstocks Unified Scanner — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the Breakoutstocks project from duplicated standalone scripts into a clean Python package with shared modules, real NSE data integration, and a unified 4-tab Streamlit dashboard.

**Architecture:** Clean rewrite using the proven `TestableScorer` from `nse_fo_consolidated_scanner.py` as the foundation. Shared modules for indicators, data fetching (market-data-lake + live NSE), and models. Single Streamlit entry point with F&O Scanner, Breakout/Reversal, Multibagger, and Market Overview tabs.

**Tech Stack:** Python 3.10+, Streamlit, Pandas, NumPy, PyArrow, Plotly, yfinance (fallback), requests, pytest

## Global Constraints

- Python 3.10+ required
- All indicator calculations in ONE file: `breakoutstocks/indicators/technical.py`
- All configuration constants in ONE file: `breakoutstocks/config.py` — no magic numbers in logic
- RSI must use Wilder's exponential smoothing (EWM with `alpha=1/14`), not simple rolling mean
- Never generate random/simulated data — log a warning if real data unavailable
- All tests use deterministic sample DataFrames — no network calls
- Commit after each task completes
- Data lake URL: `https://raw.githubusercontent.com/ubermachine/market-data-lake/main/data`
- Data lake Parquet files: `DailyBars.parquet`, `WeeklyBars.parquet`, `SectorDailyBars.parquet`, `StockMetadatas.parquet`
- Data lake columns: `Ticker` (e.g. `"TCS.NS"`), `Date`, `Open`, `High`, `Low`, `Close`, `Volume`
- NSE option chain endpoint: `https://www.nseindia.com/api/option-chain-equities?symbol={symbol}`
- NSE FII/DII endpoint: `https://www.nseindia.com/api/fiidiiTradeReact`

## File Map

| File | Responsibility |
|---|---|
| `breakoutstocks/__init__.py` | Package marker |
| `breakoutstocks/config.py` | All constants, thresholds, scoring weights |
| `breakoutstocks/models/__init__.py` | Package marker |
| `breakoutstocks/models/types.py` | Enums, dataclasses: `Advice`, `Confidence`, `TradePlan`, `StockAnalysis`, `ScanResult`, `MarketRegime` |
| `breakoutstocks/data/__init__.py` | Package marker |
| `breakoutstocks/data/lake_client.py` | Reads OHLCV + metadata from market-data-lake Parquet files |
| `breakoutstocks/data/nse_live.py` | Live NSE scraping: option chain, FII/DII, F&O ban list |
| `breakoutstocks/data/client.py` | `MarketDataClient` — unified facade combining lake + NSE live |
| `breakoutstocks/indicators/__init__.py` | Package marker |
| `breakoutstocks/indicators/technical.py` | All indicator calculations (single source of truth) |
| `breakoutstocks/scanners/__init__.py` | Package marker |
| `breakoutstocks/scanners/base.py` | `BaseScanner` ABC with ThreadPoolExecutor |
| `breakoutstocks/scanners/fo_scorer.py` | `TestableScorer` — ported F&O 100-point scoring engine |
| `breakoutstocks/scanners/breakout_reversal.py` | Breakout & reversal signal detection |
| `breakoutstocks/scanners/multibagger.py` | Fundamental multibagger screening |
| `breakoutstocks/utils/__init__.py` | Package marker |
| `breakoutstocks/utils/logging.py` | Logging configuration |
| `app.py` | Unified Streamlit dashboard (4 tabs) |
| `tests/__init__.py` | Package marker |
| `tests/test_indicators.py` | Indicator calculation tests |
| `tests/test_scorer.py` | F&O scoring engine tests (ported from existing 10 TDD tests) |
| `tests/test_breakout_reversal.py` | Breakout/reversal signal detection tests |
| `tests/test_multibagger.py` | Multibagger screening tests |
| `requirements.txt` | Dependencies |
| `output/` | CSV output directory (gitignored) |

---

### Task 1: Project Scaffolding, Config, and Models

**Files:**
- Create: `requirements.txt`
- Create: `breakoutstocks/__init__.py`
- Create: `breakoutstocks/config.py`
- Create: `breakoutstocks/models/__init__.py`
- Create: `breakoutstocks/models/types.py`
- Create: `breakoutstocks/utils/__init__.py`
- Create: `breakoutstocks/utils/logging.py`
- Create: `breakoutstocks/data/__init__.py`
- Create: `breakoutstocks/indicators/__init__.py`
- Create: `breakoutstocks/scanners/__init__.py`
- Create: `tests/__init__.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `Config` dataclass (used by all later tasks), `Advice` enum, `Confidence` enum, `TradePlan` dataclass, `StockAnalysis` dataclass, `ScanResult` dataclass, `MarketRegime` dataclass, `setup_logging()` function

- [ ] **Step 1: Create `requirements.txt`**
- [ ] **Step 2: Create package `__init__.py` files**
- [ ] **Step 3: Create `breakoutstocks/utils/logging.py`**
- [ ] **Step 4: Create `breakoutstocks/config.py`**
- [ ] **Step 5: Create `breakoutstocks/models/types.py`**
- [ ] **Step 6: Update `.gitignore`**
- [ ] **Step 7: Create `output/` directory with `.gitkeep`**
- [ ] **Step 8: Commit Task 1**

---

### Task 2: Data Lake Client

**Files:**
- Create: `breakoutstocks/data/lake_client.py`
- Create: `tests/test_lake_client.py`

**Interfaces:**
- Consumes: `Config` from `breakoutstocks.config`
- Produces: `DataLakeClient` with methods `get_daily_bars(symbol, days) -> pd.DataFrame`, `get_stock_metadata() -> pd.DataFrame`, `get_sector_index(index, days) -> pd.DataFrame`, `get_all_tickers() -> List[str]`

- [ ] **Step 1: Write failing test for `DataLakeClient`**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `breakoutstocks/data/lake_client.py`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit Task 2**

---

### Task 3: NSE Live Client

**Files:**
- Create: `breakoutstocks/data/nse_live.py`

**Interfaces:**
- Consumes: `Config` from `breakoutstocks.config`
- Produces: `NSELiveClient` with methods `get_option_chain(symbol) -> Optional[pd.DataFrame]`, `get_fii_dii() -> Optional[dict]`, `get_fo_ban_list() -> List[str]`

- [ ] **Step 1: Create `breakoutstocks/data/nse_live.py` with session cookies and fallback retry**
- [ ] **Step 2: Commit Task 3**

---

### Task 4: Unified MarketDataClient

**Files:**
- Create: `breakoutstocks/data/client.py`

**Interfaces:**
- Consumes: `DataLakeClient`, `NSELiveClient`, `Config`, `MarketRegime`
- Produces: `MarketDataClient` with facade methods

- [ ] **Step 1: Create `breakoutstocks/data/client.py`**
- [ ] **Step 2: Commit Task 4**

---

### Task 5: Technical Indicators Module

**Files:**
- Create: `breakoutstocks/indicators/technical.py`
- Create: `tests/test_indicators.py`

**Interfaces:**
- Consumes: Raw OHLCV DataFrames
- Produces: `calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame` with Wilder's smoothed RSI

- [ ] **Step 1: Write failing tests for indicators**
- [ ] **Step 2: Run tests to verify failure**
- [ ] **Step 3: Implement `breakoutstocks/indicators/technical.py`**
- [ ] **Step 4: Run tests to verify they pass**
- [ ] **Step 5: Commit Task 5**

---

### Task 6: F&O Scoring Engine (TestableScorer)

**Files:**
- Create: `breakoutstocks/scanners/fo_scorer.py`
- Create: `tests/test_scorer.py`

**Interfaces:**
- Consumes: `Config`, `Advice`, `Confidence`, `TradePlan`, `StockAnalysis` from models
- Produces: `TestableScorer` with method `analyze_stock(row: pd.Series) -> StockAnalysis`

- [ ] **Step 1: Write failing tests (porting 10 TDD tests)**
- [ ] **Step 2: Run tests to verify failure**
- [ ] **Step 3: Implement `breakoutstocks/scanners/fo_scorer.py`**
- [ ] **Step 4: Run tests to verify all 10 pass**
- [ ] **Step 5: Commit Task 6**

---

### Task 7: Base Scanner + Breakout/Reversal Scanner

**Files:**
- Create: `breakoutstocks/scanners/base.py`
- Create: `breakoutstocks/scanners/breakout_reversal.py`
- Create: `tests/test_breakout_reversal.py`

**Interfaces:**
- Consumes: `MarketDataClient`, `Config`, `calculate_all_indicators`, `ScanResult`
- Produces: `BaseScanner` ABC, `BreakoutReversalScanner`

- [ ] **Step 1: Write failing tests**
- [ ] **Step 2: Run tests to verify failure**
- [ ] **Step 3: Create `breakoutstocks/scanners/base.py`**
- [ ] **Step 4: Create `breakoutstocks/scanners/breakout_reversal.py`**
- [ ] **Step 5: Run tests to verify they pass**
- [ ] **Step 6: Commit Task 7**

---

### Task 8: Multibagger Scanner

**Files:**
- Create: `breakoutstocks/scanners/multibagger.py`
- Create: `tests/test_multibagger.py`

**Interfaces:**
- Consumes: `BaseScanner`, `MarketDataClient`, `Config`
- Produces: `MultibaggerScanner` with Adjusted Close return calculations

- [ ] **Step 1: Write failing tests**
- [ ] **Step 2: Run tests to verify failure**
- [ ] **Step 3: Implement `breakoutstocks/scanners/multibagger.py`**
- [ ] **Step 4: Run tests to verify they pass**
- [ ] **Step 5: Commit Task 8**

---

### Task 9: Unified Streamlit Dashboard

**Files:**
- Create: `app.py`

**Interfaces:**
- Consumes: `MarketDataClient`, `TestableScorer`, `BreakoutReversalScanner`, `MultibaggerScanner`, Plotly
- Produces: Runnable 4-tab Streamlit web application (`app.py`)

- [ ] **Step 1: Implement `app.py`**
- [ ] **Step 2: Verify app starts cleanly without import errors**
- [ ] **Step 3: Commit Task 9**

---

### Task 10: Cleanup and Final Verification

**Files:**
- Delete: `nse_fo_scanner.py`, `nse_fo_scanner_app.py`
- Modify: `README.md`

- [ ] **Step 1: Remove redundant deprecated files**
- [ ] **Step 2: Run full test suite (`pytest tests/ -v`)**
- [ ] **Step 3: Verify Streamlit app runs in headless mode**
- [ ] **Step 4: Update `README.md` with new package usage and setup guides**
- [ ] **Step 5: Final commit**
