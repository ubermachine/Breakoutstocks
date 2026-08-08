# Breakoutstocks Unified Scanner Restructure

## Overview

A full restructure of the Breakoutstocks project from a collection of standalone, duplicated scripts into a proper Python package with:
- Shared indicator/data/scoring modules (eliminating massive code duplication)
- Unified Streamlit dashboard combining F&O Scanner, Breakout/Reversal, and Multibagger finder
- Real data integration via market-data-lake (OHLCV) + live NSE scraping (F&O/options/FII-DII)
- All critical bugs fixed
- Unit tests for core logic
- Clean package structure with dependency management

## Current State Problems

### Critical Bugs
| Bug | File | Impact |
|---|---|---|
| Wrong Nifty ticker `^NSPI` (should be `^NSEI`) | `nse_fo_app.py` L166 | Market regime always fails silently |
| Empty company name mapping `names = {}` | `bse_breakout_reversal_scanner.py` | All stocks show as "Unknown" in CSVs |
| Uses raw `Close` not `Adj Close` | `find_multibaggers.py` | Stock splits cause wildly wrong return calculations |
| NSE FII/DII API always 403s (no session cookies) | `bse_breakout_reversal_scanner.py` | Falls back to random data every run |
| Duplicate/invalid ticker symbols | `nse_fo_scanner.py`, `nse_fo_app.py` | Scans fail silently for those tickers |
| `yfinance` news API structure change | `bse_breakout_reversal_scanner.py` | Sentiment analysis returns empty strings |
| RSI uses simple rolling mean | `bse_breakout_reversal_scanner.py` | Diverges from standard Wilder's smoothing |
| Simulated F&O data (random numbers) | `nse_fo_scanner.py`, `nse_fo_app.py` | Options/futures scores are meaningless |

### Code Duplication
| Duplicated Element | Files Where It Appears |
|---|---|
| `calculate_indicators()` | All 4 scanner files (each has its own version) |
| Hardcoded F&O stock list (~150+ symbols) | `nse_fo_scanner.py`, `nse_fo_consolidated_scanner.py`, `nse_fo_app.py` |
| Signal detection logic | `nse_fo_scanner.py`, `nse_fo_consolidated_scanner.py`, `bse_breakout_reversal_scanner.py` |
| Stock data fetching via yfinance | All 5 files |
| ThreadPoolExecutor scanning pattern | All 4 scanner files |
| Market regime fetching | `nse_fo_scanner.py`, `nse_fo_app.py` |

### Redundant Files
- `nse_fo_scanner.py` (original) superseded by `nse_fo_consolidated_scanner.py` (refined)
- `nse_fo_scanner_app.py` (Flask CSV viewer) superseded by `nse_fo_app.py` (Streamlit)
- `nse_fo_scanner_app.py` is also auto-generated as a string template inside `nse_fo_scanner.py`

## Approach

**Clean Rewrite with Proven Logic** — Create a proper Python package from scratch, port the proven `TestableScorer` from `nse_fo_consolidated_scanner.py` (which has TDD tests), extract shared modules, build one unified Streamlit app, integrate real NSE APIs, and add BSE + multibagger tabs.

Old/redundant files will be removed: `nse_fo_scanner.py`, `nse_fo_scanner_app.py`.

---

## Package Structure

```
breakoutstocks/
├── pyproject.toml
├── requirements.txt
├── README.md
├── app.py                              # Unified Streamlit entry point
├── breakoutstocks/                     # Python package
│   ├── __init__.py
│   ├── config.py                       # Constants, thresholds, scoring weights
│   ├── data/
│   │   ├── __init__.py
│   │   ├── lake_client.py              # Reads OHLCV + metadata from market-data-lake
│   │   ├── nse_live.py                 # Live NSE scraping (F&O, option chain, FII/DII)
│   │   └── client.py                   # MarketDataClient — unified interface combining both
│   ├── indicators/
│   │   ├── __init__.py
│   │   └── technical.py                # All indicator calculations (single source of truth)
│   ├── scanners/
│   │   ├── __init__.py
│   │   ├── base.py                     # Base scanner with ThreadPoolExecutor pattern
│   │   ├── breakout_reversal.py        # Breakout & reversal detection logic
│   │   ├── fo_scorer.py                # TestableScorer (ported from consolidated)
│   │   └── multibagger.py              # Fundamental multibagger screening
│   ├── models/
│   │   ├── __init__.py
│   │   └── types.py                    # Dataclasses: StockAnalysis, TradePlan, Advice, etc.
│   └── utils/
│       ├── __init__.py
│       └── logging.py                  # Logging configuration
├── tests/
│   ├── __init__.py
│   ├── test_indicators.py
│   ├── test_scorer.py                  # Ported from existing TDD tests
│   ├── test_breakout_reversal.py
│   └── test_multibagger.py
└── output/                             # CSV output directory (gitignored)
```

---

## Data Architecture

### Data Sources

```
┌─────────────────────────────────────────────────────────────┐
│                breakoutstocks/data/                          │
├────────────────────────────┬────────────────────────────────┤
│     lake_client.py         │      nse_live.py               │
│  (reads from data lake)    │  (live NSE scraping)           │
│                            │                                │
│  • DailyBars.parquet       │  • F&O futures OI/premium      │
│  • StockMetadatas.parquet  │  • Option chain snapshots      │
│  • SectorDailyBars.parquet │  • FII/DII daily activity      │
│  • WeeklyBars.parquet      │  • F&O ban list                │
│                            │                                │
│  Source: GitHub raw URL    │  Source: nseindia.com APIs      │
│  or local clone            │  with proper session mgmt      │
└─────────────┬──────────────┴───────────────┬────────────────┘
              │                              │
              └──────────┬───────────────────┘
                         ▼
               ┌──────────────────┐
               │ MarketDataClient │  ← unified interface
               │ (combines both)  │
               └──────────────────┘
```

### `lake_client.py` — Data Lake Reader

```python
class DataLakeClient:
    """Reads historical OHLCV + metadata from ubermachine/market-data-lake."""
    
    GITHUB_BASE = "https://raw.githubusercontent.com/ubermachine/market-data-lake/main/data"
    
    def __init__(self, local_path: str = None):
        self.local_path = local_path  # Use local clone if available, else GitHub URL
    
    def get_daily_bars(self, symbol: str, days: int = 180) -> pd.DataFrame:
        """Get daily OHLCV for a symbol from DailyBars.parquet."""
    
    def get_weekly_bars(self, symbol: str) -> pd.DataFrame:
        """Get weekly OHLCV for a symbol from WeeklyBars.parquet."""
    
    def get_stock_metadata(self) -> pd.DataFrame:
        """Get ticker → name, sector mapping from StockMetadatas.parquet."""
    
    def get_sector_index(self, index: str, days: int = 30) -> pd.DataFrame:
        """Get sector/index data from SectorDailyBars.parquet."""
    
    def get_all_tickers(self) -> List[str]:
        """Get list of all 825+ NSE stock symbols in the lake."""
```

### `nse_live.py` — Real NSE F&O Data

```python
class NSELiveClient:
    """Fetches live derivatives data from NSE with proper session handling."""
    
    def __init__(self):
        self.session = self._create_nse_session()
    
    def _create_nse_session(self) -> requests.Session:
        """Initialize session by visiting nseindia.com to get cookies first.
        Solves the 403 Forbidden problem that plagues current code."""
    
    def get_option_chain(self, symbol: str) -> pd.DataFrame:
        """Fetch real option chain from NSE.
        Endpoint: https://www.nseindia.com/api/option-chain-equities?symbol={symbol}
        Returns: strikes, CE/PE OI, CE/PE change in OI, CE/PE IV, CE/PE LTP"""
    
    def get_fii_dii(self) -> dict:
        """Fetch today's FII/DII activity.
        Endpoint: https://www.nseindia.com/api/fiidiiTradeReact"""
    
    def get_fo_ban_list(self) -> List[str]:
        """Fetch current F&O ban list.
        Endpoint: https://nsearchives.nseindia.com/content/fo/fo_secban.csv"""
    
    def get_fo_participant_data(self) -> pd.DataFrame:
        """Fetch F&O participant-wise OI data (FII/DII/Pro/Client)."""
```

### `client.py` — Unified MarketDataClient

```python
class MarketDataClient:
    """Unified interface combining data lake and live NSE data."""
    
    def __init__(self, config: Config):
        self.lake = DataLakeClient(local_path=config.LAKE_PATH)
        self.nse = NSELiveClient()
        self.config = config
    
    # Equity data — from data lake (fast, reliable)
    def get_stock_ohlcv(self, symbol: str, days: int = 180) -> pd.DataFrame
    def get_stock_name(self, symbol: str) -> str
    def get_all_nse_tickers(self) -> List[str]
    
    # F&O data — from live NSE (real data)
    def get_futures_data(self, symbol: str) -> dict
    def get_option_chain(self, symbol: str) -> pd.DataFrame
    
    # Market regime — combined sources
    def get_market_regime(self) -> MarketRegime
    def get_fii_dii(self) -> dict
    def get_nifty_data(self, days: int = 30) -> pd.DataFrame
    def get_vix_data(self, days: int = 30) -> pd.DataFrame
```

### Fallback Strategy
1. **Primary**: Data lake for OHLCV, NSE live for F&O
2. **Fallback**: yfinance for cash OHLCV if lake is unavailable
3. **Never**: Generate random/simulated data — log a clear warning instead

### Configuration

```python
# breakoutstocks/config.py
LAKE_PATH = os.environ.get("MARKET_DATA_LAKE_PATH", None)  # local clone path
LAKE_GITHUB_URL = "https://raw.githubusercontent.com/ubermachine/market-data-lake/main/data"
YFINANCE_FALLBACK = True  # Use yfinance when lake data is unavailable
```

---

## Indicators Module

### `breakoutstocks/indicators/technical.py`

Single source of truth for all indicator calculations. Takes a raw OHLCV DataFrame, returns the same DataFrame with indicator columns appended.

| Category | Indicators |
|---|---|
| Moving Averages | SMA(20, 50, 200), EMA(10, 12, 26) |
| Momentum | RSI(14) **using Wilder's smoothing**, MACD, MACD Signal, MACD Histogram, ROC(10, 20), Stochastic(14,3) |
| Volatility | Bollinger Bands(20, 2σ), ATR(14) |
| Volume | Volume SMA(20), Volume Ratio, OBV, VWAP |
| Trend | ADX(14), Supertrend, Parabolic SAR |
| Advanced | Ichimoku Cloud (Tenkan 9, Kijun 26, Senkou B 52) |

**Key fix**: RSI uses Wilder's exponential smoothing (RMA) instead of simple rolling mean.

```python
def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators on OHLCV data.
    
    Args:
        df: DataFrame with columns [Open, High, Low, Close, Volume]
    
    Returns:
        Same DataFrame with indicator columns appended.
    """
```

---

## Scanners & Scoring Engine

### `breakoutstocks/scanners/base.py` — Base Scanner

```python
class BaseScanner(ABC):
    """Base scanner with shared parallel execution pattern."""
    
    def __init__(self, data_client: MarketDataClient, config: Config):
        self.data = data_client
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def scan(self, symbols: List[str], max_workers: int = 10,
             progress_callback: Callable = None) -> pd.DataFrame:
        """Parallel scan using ThreadPoolExecutor.
        Shared: progress tracking, error handling/logging, result collection."""
    
    @abstractmethod
    def analyze_stock(self, symbol: str) -> Optional[dict]:
        """Each scanner implements its own analysis logic."""
    
    def save_results(self, df: pd.DataFrame, prefix: str) -> str:
        """Save results to timestamped CSV in output/ directory."""
```

### `breakoutstocks/scanners/fo_scorer.py` — F&O Scoring Engine

Ported from `nse_fo_consolidated_scanner.py`'s `TestableScorer` (most mature code, already has 10 TDD tests).

**100-Point Scoring System:**

| Component | Points | Data Source |
|---|---|---|
| Cash Score | 0–20 | Data lake (DailyBars) |
| Price Score | 0–20 | Data lake (DailyBars) |
| Delivery Score | 0–10 | NSE bhavcopy (delivery qty/%) |
| Futures Score | 0–15 | NSE live (real futures OI, premium) |
| Options Score | 0–20 | NSE live (real option chain PCR, IV) |
| Market Score | 0–10 | Data lake (Nifty/VIX) + NSE live (FII/DII) |
| Risk Penalty | 0 to -15 | NSE live (F&O ban list, earnings proximity) |

**Decision Rules:**
- Strong Buy: ≥80
- Buy: 65–79
- Watch: 50–64
- Wait: 35–49
- Avoid: <35

**Hard Vetoes** (force Avoid): F&O ban, earnings < 2 days, severe illiquidity, extreme put unwinding.

**Trade Plan Output**: Entry, Stop Loss, Target 1, Target 2, R:R ratio, position size, invalidation criteria.

### `breakoutstocks/scanners/breakout_reversal.py` — Breakout & Reversal Scanner

**Breakout Signals:**
1. `BREAKOUT_20DAY_HIGH` — Close > 20-day max High AND Volume Ratio > 1.5
2. `BREAKOUT_SMA50` — Close crosses above SMA 50 AND Volume Ratio > 1.3
3. `BOLLINGER_BREAKOUT` — Close > Bollinger Upper AND Volume Ratio > 1.5
4. `GOLDEN_CROSS` — SMA 50 crosses above SMA 200

**Reversal Signals:**
1. `RSI_OVERSOLD_REVERSAL` (RSI < 30) / `RSI_OVERBOUGHT_REVERSAL` (RSI > 70)
2. `MACD_BULLISH_CROSSOVER` / `MACD_BEARISH_CROSSOVER`
3. `HAMMER_PATTERN` (bullish) / `SHOOTING_STAR_PATTERN` (bearish)
4. `BULLISH_DIVERGENCE` / `BEARISH_DIVERGENCE` (Price-RSI divergence)

**Confidence Scoring**: Each signal has a weight (VERY_STRONG=4, STRONG=3, MODERATE=2, WEAK=1). Cumulative strength_score determines confidence.

**Supports both BSE and NSE universes** — user selects in the dashboard.

### `breakoutstocks/scanners/multibagger.py` — Fundamental Scanner

**Screening Criteria** (configurable in `config.py`):
- PE ratio < 30
- Revenue growth > 15%
- Profit margin > 10%
- Debt-to-equity < 1.0
- ROE > 15%
- Market cap in mid/small cap range

**Key Fixes:**
- Uses **Adjusted Close** (accounting for splits/bonuses via corporate actions)
- Weighted composite scoring instead of equal weights
- Configurable time horizons (1yr, 3yr, 5yr)
- Rate-limit handling for Yahoo Finance fundamentals API

---

## Unified Streamlit Dashboard

### Layout

```
┌───────────────────────────────────────────────────────────────┐
│  🚀 Breakoutstocks Scanner                          [Scan ▶] │
├────────────┬──────────────┬──────────────┬────────────────────┤
│ 📊 F&O     │ 💥 Breakout/ │ 💎 Multi-    │ 🌡 Market         │
│ Scanner    │ Reversal     │ bagger       │ Overview           │
├────────────┴──────────────┴──────────────┴────────────────────┤
```

### Tab 1: F&O Scanner
- **Sidebar**: Score threshold, advice filter, min R:R ratio, sector filter, max stocks to scan
- **Main**: Sortable results table → click stock → detail panel with:
  - Trade plan card (entry, SL, targets, R:R, position size)
  - Interactive Plotly candlestick chart with level overlays
  - Component score breakdown bar chart
  - Real option chain data visualization
  - Key reasons and warnings

### Tab 2: Breakout/Reversal
- **Sidebar**: BSE or NSE universe selector, breakout/reversal/both filter, confidence threshold
- **Main**: Results with signal type, confidence score, key signals
  - Expandable stock detail with chart and signal annotations

### Tab 3: Multibagger
- **Sidebar**: Fundamental criteria sliders (PE, growth, margin, D/E, ROE), time horizon
- **Main**: Ranked results with composite fundamental score
  - Stock detail showing financial metrics and price chart

### Tab 4: Market Overview
- Nifty 50 / Bank Nifty trend cards with mini-charts
- India VIX gauge
- FII/DII net buy/sell bar chart (real data from NSE)
- Sector rotation heatmap (from data lake SectorDailyBars)

### Shared Features
- Every scan auto-saves results to `output/` with timestamp
- Progress bar during scanning
- Color-coded advice tiers in result tables
- Responsive layout

---

## Data Models

### `breakoutstocks/models/types.py`

```python
class Advice(Enum):
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    WATCH = "Watch"
    WAIT = "Wait"
    AVOID = "Avoid"

class Confidence(Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

@dataclass
class TradePlan:
    entry: float
    entry_type: str           # "Breakout" / "Pullback"
    stop_loss: float
    target_1: float
    target_2: float
    risk_reward: float
    position_size: str        # e.g., "50% of normal"
    invalidation: str         # e.g., "Close below SL for 2 days"

@dataclass
class StockAnalysis:
    symbol: str
    name: str
    advice: Advice
    confidence: Confidence
    final_score: float
    trade_plan: Optional[TradePlan]
    reasons: List[str]
    warnings: List[str]
    component_scores: dict    # {cash, price, delivery, futures, options, market, risk_penalty}

@dataclass
class ScanResult:
    symbol: str
    name: str
    signal_type: str          # BREAKOUT / REVERSAL
    confidence: float
    current_price: float
    volume_ratio: float
    signals: List[dict]       # [{type, strength, description}]
    strength_score: float

@dataclass
class MultibaggerResult:
    symbol: str
    name: str
    pe_ratio: float
    revenue_growth: float
    profit_margin: float
    debt_to_equity: float
    roe: float
    market_cap: float
    return_pct: float         # Adjusted close return over selected horizon
    composite_score: float

@dataclass
class MarketRegime:
    nifty_trend: str          # "UP" / "DOWN" / "SIDEWAYS"
    nifty_change_pct: float
    vix_level: float
    vix_change_pct: float
    fii_net: float
    dii_net: float
    fii_trend: str            # "BUYING" / "SELLING"
    dii_trend: str
    regime_score: float       # 0-10
```

---

## Configuration

### `breakoutstocks/config.py`

All magic numbers extracted into one place:

```python
@dataclass
class Config:
    # Data sources
    LAKE_PATH: str = None
    LAKE_GITHUB_URL: str = "https://raw.githubusercontent.com/ubermachine/market-data-lake/main/data"
    YFINANCE_FALLBACK: bool = True
    
    # F&O Scoring weights (sum = 100 + penalty)
    CASH_SCORE_MAX: int = 20
    PRICE_SCORE_MAX: int = 20
    DELIVERY_SCORE_MAX: int = 10
    FUTURES_SCORE_MAX: int = 15
    OPTIONS_SCORE_MAX: int = 20
    MARKET_SCORE_MAX: int = 10
    RISK_PENALTY_MAX: int = 15
    
    # Advice thresholds
    STRONG_BUY_THRESHOLD: int = 80
    BUY_THRESHOLD: int = 65
    WATCH_THRESHOLD: int = 50
    WAIT_THRESHOLD: int = 35
    
    # Breakout thresholds
    VOLUME_RATIO_BREAKOUT: float = 1.5
    VOLUME_RATIO_SMA_CROSS: float = 1.3
    RSI_OVERSOLD: float = 30.0
    RSI_OVERBOUGHT: float = 70.0
    
    # Multibagger criteria
    MAX_PE: float = 30.0
    MIN_REVENUE_GROWTH: float = 0.15
    MIN_PROFIT_MARGIN: float = 0.10
    MAX_DEBT_EQUITY: float = 1.0
    MIN_ROE: float = 0.15
    
    # Scanner settings
    MAX_WORKERS: int = 10
    DEFAULT_LOOKBACK_DAYS: int = 180
```

---

## Files to Remove

| File | Reason |
|---|---|
| `nse_fo_scanner.py` | Superseded by `nse_fo_consolidated_scanner.py` → ported to `fo_scorer.py` |
| `nse_fo_scanner_app.py` | Superseded by unified `app.py`; was auto-generated from `nse_fo_scanner.py` |

## Files to Port & Remove

| Old File | Ported To | Key Fixes |
|---|---|---|
| `nse_fo_consolidated_scanner.py` | `breakoutstocks/scanners/fo_scorer.py` | Real F&O data, config-driven thresholds |
| `nse_fo_app.py` | `app.py` (unified dashboard) | Fixed `^NSPI`→`^NSEI`, added BSE+multibagger tabs |
| `bse_breakout_reversal_scanner.py` | `breakoutstocks/scanners/breakout_reversal.py` | Fixed RSI, company names, removed random FII/DII |
| `find_multibaggers.py` | `breakoutstocks/scanners/multibagger.py` | Adj Close, weighted scoring, rate limiting |

---

## Testing Strategy

### Unit Tests

```
tests/
├── test_indicators.py          # Test indicator calculations against known values
├── test_scorer.py              # Port existing 10 TDD tests + add edge cases
├── test_breakout_reversal.py   # Test signal detection with deterministic sample data
└── test_multibagger.py         # Test screening criteria and return calculations
```

All tests use deterministic sample DataFrames — no network calls.

### Run Tests

```bash
python -m pytest tests/ -v
```

### Manual Verification

1. Run `streamlit run app.py` and verify all 4 tabs render
2. Run a scan on NSE F&O universe — verify real data flows through
3. Run a BSE breakout/reversal scan — verify company names populated
4. Check CSV exports in `output/` directory

---

## Dependency Management

### `requirements.txt`

```
streamlit>=1.28.0
pandas>=2.0.0
numpy>=1.24.0
yfinance>=0.2.28
plotly>=5.15.0
pyarrow>=12.0.0
requests>=2.31.0
beautifulsoup4>=4.12.0
ta>=0.10.2
pytest>=7.4.0
```

---

## Implementation Order

1. **Foundation**: `config.py`, `models/types.py`, `utils/logging.py`
2. **Data Layer**: `data/lake_client.py`, `data/nse_live.py`, `data/client.py`
3. **Indicators**: `indicators/technical.py` + `tests/test_indicators.py`
4. **Scanners**: `scanners/base.py`, `scanners/fo_scorer.py` + `tests/test_scorer.py`
5. **More Scanners**: `scanners/breakout_reversal.py`, `scanners/multibagger.py` + tests
6. **Dashboard**: `app.py` (Tab 1: F&O → Tab 2: Breakout/Reversal → Tab 3: Multibagger → Tab 4: Market Overview)
7. **Cleanup**: Remove old files, update README, create `requirements.txt`
8. **Verification**: Run all tests, verify dashboard end-to-end
