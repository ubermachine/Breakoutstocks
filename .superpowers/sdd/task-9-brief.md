# Task 9: Unified Streamlit Dashboard

## Files
- Create: `app.py`

## Interfaces
- Consumes:
  - `MarketDataClient` (from `breakoutstocks.data.client`)
  - `TestableScorer` (from `breakoutstocks.scanners.fo_scorer`)
  - `BreakoutReversalScanner` (from `breakoutstocks.scanners.breakout_reversal`)
  - `MultibaggerScanner` (from `breakoutstocks.scanners.multibagger`)
  - `calculate_all_indicators` (from `breakoutstocks.indicators.technical`)
  - Models: `Advice`, `Confidence`, `TradePlan`, `StockAnalysis`, `ScanResult`, `MarketRegime` (from `breakoutstocks.models.types`)
  - `Config` (from `breakoutstocks.config`)
  - Plotly: `plotly.graph_objects`, `plotly.subplots.make_subplots`
  - Streamlit: `streamlit as st`
- Produces:
  - Runnable Streamlit web application: `app.py` with 4 interactive tabs:
    1. 📊 **F&O Scanner Tab**:
       - Controls: max stocks to scan, min score slider, advice multi-select, R:R > 1.2 filter
       - Scan trigger with progress bar
       - Results table with color-coded advice and sortable columns
       - Stock detail drill-down with interactive Plotly candlestick chart, trade plan levels (Entry, Stop Loss, Target 1), and score component breakdown
    2. 💥 **Breakout/Reversal Tab**:
       - Controls: Universe selector (NSE / BSE), Signal type filter (All / Breakout / Reversal), scan limit
       - Scan trigger with progress bar
       - Signal details table (price, change %, volume ratio, RSI, strength score, signal badges)
       - Stock detail drill-down with price chart
    3. 💎 **Multibagger Tab**:
       - Controls: Time horizon selector (1, 3, 5 years), stock limit
       - Scan trigger with progress bar
       - Ranked multibagger results table with PE ratio, revenue growth, profit margin, ROE, debt to equity, market cap, and adjusted returns %
    4. 🌡 **Market Overview Tab**:
       - Metric cards: Nifty trend & 24h change, India VIX level & change, FII flow & trend, DII flow & trend, Overall regime score (0-10)
       - Candlestick chart for Nifty 50 (`^NSEI`)

## Global Constraints
- Python 3.10+ required
- Must import and use the real modules from `breakoutstocks` package
- Nifty ticker must be `^NSEI` (fixing legacy `^NSPI` bug)
- Clean error handling if data sources are momentarily unavailable
- Headless execution compatible: `streamlit run app.py --server.headless true`

## Steps
1. Create `app.py` implementing all 4 tabs and helper functions (`create_price_chart`, `analyze_fo_stock`, `_extract_options_features`)
2. Verify app compiles and starts in headless mode: `python -m py_compile app.py`
3. Verify test suite still passes without conflicts
4. Commit with `git add -A` and `git commit -m "feat: add unified 4-tab Streamlit dashboard"`
