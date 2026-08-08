# NSE F&O All-in-One Consolidated Scanner

## 🎯 Overview

A comprehensive trading decision-support system for NSE F&O stocks that provides **consolidated trading advice** with clear entry, stop loss, targets, and risk-reward analysis.

This scanner combines:
- **Cash Market Analysis** (Volume burst, price action, delivery)
- **Futures Data** (OI changes, premium/discount)
- **Options Chain Analysis** (PCR, put/call writing, IV percentile)
- **Market Regime** (Nifty trend, India VIX, FII/DII bias)

## ✨ Key Features

### 1. Test-Driven Development
- Comprehensive test suite with 10+ tests
- All scoring components validated
- Production-ready code quality

### 2. Consolidated Trading Advice
For each stock, the system answers:
- **What should I do?** → Strong Buy / Buy / Watch / Wait / Avoid
- **How confident?** → High / Medium / Low
- **Where to enter?** → Specific entry price
- **Where is stop loss?** → Risk management level
- **What are targets?** → Target 1 & Target 2
- **What's the risk-reward?** → R:R ratio
- **Why this signal?** → Clear reasons list
- **What are the risks?** → Warnings list

### 3. Scoring Model (100 points total)

| Component | Weight | Factors |
|-----------|--------|---------|
| Cash Score | 20 pts | Volume burst (>2x), avg volume, bullish close |
| Price Score | 20 pts | Breakout above high, trend, RSI momentum |
| Delivery Score | 10 pts | Delivery ratio, delivery percentage |
| Futures Score | 15 pts | Futures price, OI change, premium |
| Options Score | 20 pts | PCR rising, put writing, call unwinding, IV |
| Market Score | 10 pts | Nifty trend, VIX, FII/DII bias |
| Risk Penalty | -15 pts | Events, bans, high IV, unwinding |

### 4. Decision Rules

| Final Score | Advice | Meaning |
|-------------|--------|---------|
| ≥ 80 | **Strong Buy** | High-quality setup, minimal warnings |
| 65-79 | **Buy** | Good setup with acceptable risk |
| 50-64 | **Watch** | Developing setup, needs confirmation |
| 35-49 | **Wait** | Conditions close but trigger incomplete |
| < 35 | **Avoid** | Not good enough or conflicting signals |

**Hard Vetoes** (automatic Avoid):
- Stock in F&O ban
- Earnings within 2 days
- Severe liquidity issues
- Extreme put unwinding

## 📁 Files

### `nse_fo_consolidated_scanner.py`
Core scoring engine with:
- `TestableScorer` class with all scoring methods
- `Advice` enum (STRONG_BUY, BUY, WATCH, WAIT, AVOID)
- `Confidence` enum (HIGH, MEDIUM, LOW)
- `TradePlan` dataclass (entry, stop, targets, RR)
- `StockAnalysis` dataclass (complete analysis result)
- Comprehensive test suite (`test_scoring_engine()`)

### `nse_fo_app.py`
Streamlit web application with:
- Interactive scanner UI
- Real-time stock scanning
- Filterable results table
- Detailed stock analysis view
- Price charts with entry/stop/targets
- Score breakdown visualization
- Market context dashboard

## 🚀 Usage

### Run Tests First
```bash
python3 nse_fo_consolidated_scanner.py
```

Expected output:
```
Tests Passed: 10/10
🎉 ALL TESTS PASSED!
✅ Scoring engine is ready for production use!
```

### Launch Streamlit App
```bash
streamlit run nse_fo_app.py
```

The app will open in your browser at `http://localhost:8501`

### Using the App

1. **Configure Settings** (sidebar):
   - Number of stocks to scan (10-100)
   - Minimum final score filter (0-100)
   - Advice type filter (Strong Buy, Buy, Watch, etc.)
   - Risk-Reward filter (>1.2 recommended)

2. **Run Scan**:
   - Click "🚀 Run Full Scan"
   - Wait for progress bar to complete
   - Results appear in table

3. **View Results**:
   - Sort by Final Score, Risk-Reward, etc.
   - Click on any stock for detailed view
   - See trade plan, reasons, warnings

4. **Detailed Analysis** shows:
   - Advice card with confidence level
   - Entry, Stop Loss, Target 1 & 2
   - Risk-Reward ratio
   - Position size recommendation
   - Invalidation conditions
   - Bullish reasons list
   - Warning flags
   - Price chart with indicators
   - Score breakdown chart

## 📊 Example Output

```
Stock: TATAMOTORS
Advice: BUY
Confidence: Medium
Final Score: 74/100

Trade Plan:
├─ Entry: ₹978.00
├─ Stop Loss: ₹952.00
├─ Target 1: ₹1005.00
├─ Target 2: ₹1025.00
├─ Risk-Reward: 1 : 1.7
└─ Position Size: Medium

Invalidation: Close below ₹952.00 or put support breaks

✅ Bullish Reasons:
• Volume burst: 2.9x average
• Closed above previous high
• Put OI increasing below spot
• Call OI not aggressive above spot
• PCR rising
• Futures price supportive

⚠️ Warnings:
• Call resistance is very close
• Earnings in 4 days
```

## 🔧 Production Deployment

### Replace Simulated Data

The current implementation uses **simulated options and futures data** for demonstration. For production:

1. **Connect Broker API** (Zerodha Kite, Upstox, Angel One, Dhan, Fyers):
```python
# Replace simulate_options_data() with:
from kiteconnect import KiteConnect
kite = KiteConnect(api_key="your_key")
option_chain = kite.option_chain("RELIANCE")
```

2. **Fetch Real F&O Ban List**:
```python
# Download from NSE website daily
fno_ban_stocks = fetch_nse_fno_ban_list()
```

3. **Real Earnings Calendar**:
```python
# Integrate with earnings API
earnings_dates = fetch_earnings_calendar()
```

4. **Real FII/DII Data**:
```python
# Download from NSE bhavcopy
fii_dii_data = fetch_nse_fii_dii_report()
```

## 🧪 Testing

The test suite validates:
1. ✅ Cash score calculation
2. ✅ Price score calculation
3. ✅ Options score calculation
4. ✅ Risk penalty calculation
5. ✅ Final score clamping [0-100]
6. ✅ Strong Buy advice generation
7. ✅ Avoid advice with F&O ban veto
8. ✅ Trade plan generation
9. ✅ Confidence level determination
10. ✅ Reasons generation

Run tests anytime:
```bash
python3 nse_fo_consolidated_scanner.py
```

## 📈 Next Steps

### Phase 1: MVP (Current)
✅ Core scoring engine  
✅ Test suite  
✅ Streamlit UI  
✅ Simulated data  

### Phase 2: Real Data Integration
- [ ] Broker API integration
- [ ] Real options chain fetching
- [ ] Real futures OI data
- [ ] F&O ban list auto-update

### Phase 3: Backtesting
- [ ] Historical signal testing
- [ ] Win rate analysis
- [ ] Profit factor calculation
- [ ] Drawdown statistics

### Phase 4: Advanced Features
- [ ] Sector strength analysis
- [ ] Correlation filtering
- [ ] Portfolio optimization
- [ ] Alert system (email/SMS)

## ⚠️ Disclaimer

This is a **decision-support tool**, not financial advice. Always:
- Do your own research
- Use proper position sizing
- Set stop losses
- Avoid event-risk trades
- Paper trade before live trading
- Monitor execution and slippage

## 📝 License

MIT License - Free for personal and commercial use.

## 🤝 Contributing

Contributions welcome! Please:
1. Add tests for new features
2. Follow existing code style
3. Document all functions
4. Update this README

---

**Built with ❤️ for Indian traders**  
*Data sources: Yahoo Finance (price), NSE (F&O data)*
