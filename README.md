# Breakoutstocks: Modular Quantitative Stock Scanner & Dashboard

A comprehensive, modular quantitative trading decision-support system and interactive dashboard for Indian equities (NSE & BSE).

`Breakoutstocks` brings together market-data-lake historical Parquet datasets, live NSE market feeds, technical indicator computations, fundamental growth screening, and multi-factor F&O option chain scoring into a unified 4-tab Streamlit web application.

---

## 📐 Architecture & Package Layout

The codebase is organized into a modular Python package structure under `breakoutstocks/`:

```
Breakoutstocks/
├── app.py                      # Unified 4-Tab Streamlit Dashboard
├── requirements.txt            # Dependency specifications
├── README.md                   # Project documentation
├── breakoutstocks/             # Core Python Package
│   ├── __init__.py
│   ├── config.py               # Centralized configuration & thresholds
│   ├── data/                   # Data Fetching & Aggregation Layer
│   │   ├── client.py           # Unified MarketDataClient (Lake + Fallback)
│   │   ├── lake_client.py      # High-performance Parquet MarketDataLake client
│   │   └── nse_live.py         # Live NSE scraper (Option chains, FII/DII, F&O ban)
│   ├── indicators/             # Quantitative Technical Indicators
│   │   └── technical.py        # Technical indicator library (RSI, MACD, ATR, BB, etc.)
│   ├── models/                 # Strong Domain Models & Data Structures
│   │   └── types.py            # Dataclasses & Enums (StockAnalysis, TradePlan, etc.)
│   ├── scanners/               # Screening & Scoring Engines
│   │   ├── base.py             # BaseScanner interface & scan results wrapper
│   │   ├── breakout_reversal.py# Technical breakout & mean-reversal scanner
│   │   ├── fo_scorer.py        # 100-point multi-factor F&O scoring engine
│   │   └── multibagger.py      # Fundamental growth & multibagger screening engine
│   └── utils/                  # Utility & Cross-Cutting Helpers
│       └── logging.py          # Structured logging configuration
└── tests/                      # Automated Unit & Integration Test Suite
    ├── test_breakout_reversal.py
    ├── test_client.py
    ├── test_indicators.py
    ├── test_lake_client.py
    ├── test_multibagger.py
    ├── test_nse_live.py
    └── test_scorer.py
```

---

## 🖥️ Unified 4-Tab Streamlit Dashboard (`app.py`)

Launch the web app using `streamlit run app.py` to access four integrated analysis tabs:

### 1. 🎯 F&O Consolidated Scanner
Quantitative multi-factor scoring model for NSE Futures & Options stocks:
- **100-Point Scoring Engine**: Combines Cash Market signals (20 pts), Price Action (20 pts), Delivery volume (10 pts), Futures Open Interest & Premium (15 pts), Options Chain Put/Call writing & PCR (20 pts), and Market Regime (10 pts), with risk penalties up to -15 pts.
- **Actionable Advice**: Categorizes signals into `Strong Buy`, `Buy`, `Watch`, `Wait`, and `Avoid`.
- **Trade Plans**: Recommends exact entry levels, stop loss, Target 1 & Target 2, Risk-Reward ratios, position sizing, invalidation criteria, bullish reasons, and warning flags.

### 2. ⚡ Breakout & Reversal Scanner
Screens NSE and BSE tickers across technical patterns:
- **Breakout Patterns**: 20-day high breakouts, SMA50/SMA200 crossovers, Bollinger Band squeezes/expansions.
- **Reversal Setups**: RSI oversold mean-reversals, MACD bullish crossovers, hammer candlesticks, and price/RSI bullish divergence.
- **Interactive Filtering**: Filter by signal type, volume burst ratio, and price gain thresholds.

### 3. 🚀 Multibagger Hunter
Fundamental and technical screening engine designed to discover high-growth potential small and mid-cap stocks:
- **Fundamental Filters**: Revenue CAGR (>15%), Profit CAGR (>20%), ROE (>15%), ROCE (>15%), Low Debt-to-Equity (<0.5), expanding operating margins.
- **Market Cap Headroom**: Evaluates growth potential against overall addressable market size.
- **Combined Scoring**: Combines fundamental health score with technical trend alignment.

### 4. 📊 Market Overview Dashboard
Macroeconomic and broad market context view:
- **Indices & VIX**: Tracks Nifty 50, Nifty Bank, and India VIX regime.
- **Sectoral Heatmap**: Visualizes real-time and historical performance across sector indices.
- **Institutional Flows**: Live FII/DII cash market and derivative net buy/sell activities.
- **Market Breadth**: Advance/Decline ratios and sector momentum overview.

---

## 📊 Data Sources

1. **Market Data Lake (`DataLakeClient`)**:
   - Reads historical daily and weekly OHLCV data directly from compressed Parquet files stored locally or fetched from GitHub release mirrors.
   - Automatically falls back to `yfinance` online fetcher when local data is missing or incomplete.
2. **Live NSE Scraper (`NSELiveClient`)**:
   - Real-time fetching of NSE option chains (Open Interest, PCR, IV percentile).
   - Real-time FII/DII institutional activity summaries.
   - Current F&O security ban list for risk management vetoes.

---

## 🚀 Quickstart & Setup

### Prerequisites
- Python 3.10 or higher

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-repo/Breakoutstocks.git
   cd Breakoutstocks
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

Launch the Streamlit dashboard locally:
```bash
streamlit run app.py
```
The app will open automatically in your browser at `http://localhost:8501`.

---

## 🧪 Running the Test Suite

The project includes an extensive test suite verifying data clients, indicator computations, scan logic, fundamental scoring, and F&O advice generation.

To run the complete test suite:
```bash
pytest tests/ -v
```

Or run via `python -m pytest`:
```bash
python -m pytest tests/ -v
```

---

## ⚠️ Disclaimer

This application is built for **educational and decision-support purposes only** and does not constitute financial advice. Always execute proper risk management, verify live broker order books, and consult a qualified financial advisor before trading.

---

## 📝 License

MIT License - Open-source for personal and commercial development.
