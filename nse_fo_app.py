"""
NSE F&O All-in-One Scanner - Streamlit App
Consolidated Trading Advice with Entry, Stop, Target, and Risk-Reward
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from typing import Dict, List, Tuple, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Import our tested scoring engine
from nse_fo_consolidated_scanner import (
    TestableScorer, Advice, Confidence, 
    StockAnalysis, TradePlan
)


# NSE F&O Stocks Universe (Top liquid stocks)
NSE_FO_STOCKS = [
    "RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "TCS.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "BAJFINANCE.NS",
    "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "TITAN.NS", "BAJAJFINSV.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS", "NESTLEIND.NS",
    "WIPRO.NS", "POWERGRID.NS", "NTPC.NS", "ONGC.NS", "M&M.NS",
    "TATAMOTORS.NS", "TATASTEEL.NS", "JSWSTEEL.NS", "ADANIENT.NS", "ADANIPORTS.NS",
    "BRITANNIA.NS", "CIPLA.NS", "DRREDDY.NS", "EICHERMOT.NS", "GRASIM.NS",
    "HEROMOTOCO.NS", "HCLTECH.NS", "TECHM.NS", "COALINDIA.NS", "BPCL.NS",
    "IOC.NS", "GAIL.NS", "NMDC.NS", "VEDL.NS", "HINDALCO.NS",
    "INDUSINDBK.NS", "YESBANK.NS", "BANKBARODA.NS", "PNB.NS", "CANBK.NS",
    "UPL.NS", "SHREECEM.NS", "AMBUJACEM.NS", "ACC.NS", "SIEMENS.NS",
    "ABB.NS", "BOSCHLTD.NS", "CUMMINSIND.NS", "ESCORTS.NS", "MOTHERSON.NS",
    "BHEL.NS", "BEL.NS", "HAL.NS", "OFSS.NS", "PERSISTENT.NS",
    "MPHASIS.NS", "LTTS.NS", "COFORGE.NS", "TATAELXSI.NS", "MINDTREE.NS",
    "TATACONSUM.NS", "GODREJCP.NS", "DABUR.NS", "MARICO.NS", "COLPAL.NS",
    "PIDILITIND.NS", "BAJAJ-AUTO.NS", "TVSMOTOR.NS", "MRF.NS", "APOLLOTYRE.NS",
    "SRTRANSFIN.NS", "BAJAJHLDNG.NS", "CHOLAFIN.NS", "LICHSGFIN.NS", "PFC.NS",
    "RECLTD.NS", "IRFC.NS", "RVNL.NS", "TRENT.NS", "NYKAA.NS",
    "PAYTM.NS", "ZOMATO.NS", "POLICYBZR.NS", "PBINFRA.NS", "IREDA.NS",
    "SJVN.NS", "NHPC.NS", "TATAPOWER.NS", "ADANIPOWER.NS", "JSWENERGY.NS",
    "TORNTPOWER.NS", "CDSL.NS", "CAMS.NS", "BSE.NS", "MCX.NS",
    "IEX.NS", "NAZARA.NS", "ROUTE.NS", "DATA.PATTERN.NS", "PARAS.NS",
    "RAINBOW.NS", "FORTIS.NS", "MAXHEALTH.NS", "APOLLOHOSP.NS", "DIVISLAB.NS",
    "BIOCON.NS", "SYNGENE.NS", "LAURUSLABS.NS", "ALKEM.NS", "SUNPHARMA.NS",
    "LUPIN.NS", "AUROPHARMA.NS", "GLENMARK.NS", "TORNTPHARM.NS", "SANOFI.NS",
    "PFIZER.NS", "GLAXO.NS", "ABBOTINDIA.NS", "JBCHEPHARM.NS", "IPCALAB.NS",
    "GRASIM.NS", "JKCEMENT.NS", "RAMCOCEM.NS", "STARCEMENT.NS", "HEIDELBERG.NS",
    "COCHINSHIP.NS", "MAZDOCK.NS", "GARDENSILK.NS", "DIAMONDYAD.NS", "THOMASCOOK.NS"
]


def fetch_stock_data(symbol: str, period: str = "60d") -> Optional[pd.DataFrame]:
    """Fetch historical data for a stock"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty:
            return None
        return df
    except Exception as e:
        return None


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate technical indicators"""
    df = df.copy()
    
    # Moving averages
    df['ema_10'] = df['Close'].ewm(span=10, adjust=False).mean()
    df['sma_20'] = df['Close'].rolling(window=20).mean()
    df['sma_50'] = df['Close'].rolling(window=50).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ATR
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(14).mean()
    
    # Previous values
    df['prev_close'] = df['Close'].shift(1)
    df['prev_high'] = df['High'].shift(1)
    df['prev_rsi'] = df['rsi'].shift(1)
    
    # Volume average
    df['avg_volume_20d'] = df['Volume'].rolling(window=20).mean()
    df['volume_ratio'] = df['Volume'] / df['avg_volume_20d']
    
    return df


def simulate_options_data(close: float, symbol: str) -> Dict:
    """
    Simulate options data for demonstration.
    In production, replace with real API calls to broker/NSE.
    """
    np.random.seed(hash(symbol) % 2**32)
    
    # Generate realistic options metrics
    pcr_oi = 0.7 + np.random.random() * 0.6  # 0.7 to 1.3
    pcr_oi_change = np.random.uniform(-0.15, 0.25)
    
    total_put_oi = int(500000 + np.random.random() * 2000000)
    total_call_oi = int(total_put_oi / pcr_oi)
    
    put_oi_change_below_spot = int(np.random.uniform(-50000, 150000))
    call_oi_change_above_spot = int(np.random.uniform(-100000, 80000))
    
    atm_iv_percentile = int(30 + np.random.random() * 60)  # 30 to 90
    
    # Support and resistance strikes
    strike_interval = max(10, round(close / 100) * 10)
    put_support_strike = round((close - strike_interval * (2 + int(np.random.random() * 3))) / strike_interval) * strike_interval
    call_resistance_strike = round((close + strike_interval * (2 + int(np.random.random() * 3))) / strike_interval) * strike_interval
    
    distance_to_call_resistance = call_resistance_strike - close
    
    return {
        'pcr_oi': round(pcr_oi, 3),
        'pcr_oi_change': round(pcr_oi_change, 3),
        'total_put_oi': total_put_oi,
        'total_call_oi': total_call_oi,
        'put_oi_change_below_spot': put_oi_change_below_spot,
        'call_oi_change_above_spot': call_oi_change_above_spot,
        'atm_iv_percentile': atm_iv_percentile,
        'put_support_strike': put_support_strike,
        'call_resistance_strike': call_resistance_strike,
        'distance_to_call_resistance': distance_to_call_resistance
    }


def simulate_futures_data(close: float, symbol: str) -> Dict:
    """
    Simulate futures data for demonstration.
    In production, replace with real API calls.
    """
    np.random.seed(hash(symbol + "_fut") % 2**32)
    
    futures_premium = close * np.random.uniform(-0.005, 0.01)  # -0.5% to +1%
    futures_close = close + futures_premium
    futures_prev_close = close * (1 + np.random.uniform(-0.02, 0.02))
    futures_oi_change = int(np.random.uniform(-200000, 500000))
    
    return {
        'futures_close': futures_close,
        'futures_prev_close': futures_prev_close,
        'futures_premium': futures_premium,
        'futures_oi_change': futures_oi_change
    }


def simulate_market_regime() -> Dict:
    """Simulate current market regime"""
    # Fetch Nifty data
    nifty = yf.Ticker("^NSPI")
    nifty_df = nifty.history(period="60d")
    
    if not nifty_df.empty:
        nifty_close = nifty_df['Close'].iloc[-1]
        nifty_sma_20 = nifty_df['Close'].rolling(20).mean().iloc[-1]
        nifty_above_20_sma = nifty_close > nifty_sma_20
        
        # India VIX
        vix = yf.Ticker("^INDIAVIX")
        vix_df = vix.history(period="30d")
        if not vix_df.empty:
            vix_change = (vix_df['Close'].iloc[-1] - vix_df['Close'].iloc[-2]) / vix_df['Close'].iloc[-2]
        else:
            vix_change = 0
    else:
        nifty_above_20_sma = True
        vix_change = 0
    
    # Simulate FII/DII bias
    fii_dii_bias_positive = np.random.random() > 0.4  # 60% chance positive
    
    return {
        'nifty_above_20_sma': nifty_above_20_sma,
        'india_vix_change': vix_change,
        'fii_dii_bias_positive': fii_dii_bias_positive
    }


def analyze_single_stock(symbol: str, scorer: TestableScorer, market_regime: Dict) -> Optional[StockAnalysis]:
    """Complete analysis for a single stock"""
    # Fetch data
    df = fetch_stock_data(symbol)
    if df is None or len(df) < 30:
        return None
    
    # Calculate indicators
    df = calculate_technical_indicators(df)
    
    # Get latest row
    latest = df.iloc[-1]
    
    # Build analysis row
    row = pd.Series({
        'symbol': symbol.replace('.NS', ''),
        'close': latest['Close'],
        'open': latest['Open'],
        'high': latest['High'],
        'low': latest['Low'],
        'prev_close': latest['prev_close'],
        'prev_high': latest['prev_high'],
        'ema_10': latest['ema_10'],
        'rsi': latest['rsi'],
        'prev_rsi': latest['prev_rsi'],
        'atr': latest['atr'],
        'volume_ratio': latest['volume_ratio'],
        'avg_volume_20d': latest['avg_volume_20d'],
        
        # Simulated delivery data
        'delivery_ratio': 1.0 + np.random.random() * 0.8,
        'delivery_pct': 0.3 + np.random.random() * 0.4,
        
        # Simulated futures data
        **simulate_futures_data(latest['Close'], symbol),
        
        # Simulated options data
        **simulate_options_data(latest['Close'], symbol),
        
        # Market regime
        **market_regime,
        
        # Risk flags (simulated)
        'earnings_within_3_days': False,
        'stock_in_fno_ban': False
    })
    
    # Analyze using our tested scorer
    analysis = scorer.analyze_stock(row)
    
    return analysis


def run_full_scan(max_stocks: int = 50) -> pd.DataFrame:
    """Run complete scan on F&O universe"""
    scorer = TestableScorer()
    market_regime = simulate_market_regime()
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    stocks_to_scan = NSE_FO_STOCKS[:max_stocks]
    
    for i, symbol in enumerate(stocks_to_scan):
        status_text.text(f"Scanning {i+1}/{len(stocks_to_scan)}: {symbol.replace('.NS', '')}")
        
        analysis = analyze_single_stock(symbol, scorer, market_regime)
        if analysis:
            results.append({
                'Symbol': analysis.symbol,
                'Advice': analysis.advice.value,
                'Confidence': analysis.confidence.value,
                'Final Score': round(analysis.final_score, 1),
                'Cash Score': round(analysis.cash_score, 1),
                'Price Score': round(analysis.price_score, 1),
                'Options Score': round(analysis.options_score, 1),
                'Futures Score': round(analysis.futures_score, 1),
                'Market Score': round(analysis.market_score, 1),
                'Risk Penalty': round(analysis.risk_penalty, 1),
                'Volume Ratio': round(pd.Series([analysis]).apply(lambda x: fetch_stock_data(x.symbol + '.NS')['volume_ratio'].iloc[-1] if fetch_stock_data(x.symbol + '.NS') is not None else 1.0, axis=1).iloc[0] if hasattr(analysis, 'symbol') else 1.0, 2),
                'PCR Change': None,  # Will be filled from options data
                'Entry': None,
                'Stop Loss': None,
                'Target 1': None,
                'Target 2': None,
                'Risk Reward': None,
                'Reasons': "; ".join(analysis.reasons[:3]),
                'Warnings': "; ".join(analysis.warnings) if analysis.warnings else "None"
            })
            
            # Add trade plan details
            if analysis.trade_plan:
                results[-1]['Entry'] = analysis.trade_plan.entry
                results[-1]['Stop Loss'] = analysis.trade_plan.stop_loss
                results[-1]['Target 1'] = analysis.trade_plan.target_1
                results[-1]['Target 2'] = analysis.trade_plan.target_2
                results[-1]['Risk Reward'] = analysis.trade_plan.risk_reward
        
        progress_bar.progress((i + 1) / len(stocks_to_scan))
    
    status_text.text("Scan complete!")
    return pd.DataFrame(results)


def create_price_chart(symbol: str, analysis: StockAnalysis) -> go.Figure:
    """Create candlestick chart with indicators"""
    df = fetch_stock_data(symbol + '.NS', period="60d")
    if df is None:
        return go.Figure()
    
    df = calculate_technical_indicators(df)
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Price'
    ), row=1, col=1)
    
    # Add EMAs
    fig.add_trace(go.Scatter(
        x=df.index, y=df['ema_10'],
        mode='lines', name='EMA 10',
        line=dict(color='orange', width=1)
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=df.index, y=df['sma_20'],
        mode='lines', name='SMA 20',
        line=dict(color='blue', width=1)
    ), row=1, col=1)
    
    # Add entry, stop, targets
    if analysis.trade_plan:
        fig.add_hline(
            y=analysis.trade_plan.entry,
            line_dash="dash", line_color="green",
            annotation_text="Entry", annotation_position="right"
        )
        fig.add_hline(
            y=analysis.trade_plan.stop_loss,
            line_dash="dash", line_color="red",
            annotation_text="Stop Loss", annotation_position="right"
        )
        fig.add_hline(
            y=analysis.trade_plan.target_1,
            line_dash="dot", line_color="green",
            annotation_text="Target 1", annotation_position="right"
        )
    
    # Volume chart
    colors = ['green' if df['Close'].iloc[i] >= df['Open'].iloc[i] else 'red' 
              for i in range(len(df))]
    fig.add_trace(go.Bar(
        x=df.index, y=df['Volume'],
        marker_color=colors, name='Volume'
    ), row=2, col=1)
    
    fig.update_layout(
        title=f"{symbol} - Price Chart",
        yaxis_title='Price',
        xaxis_rangeslider_visible=False,
        height=600,
        template='plotly_dark'
    )
    
    return fig


def main():
    st.set_page_config(
        page_title="NSE F&O Consolidated Scanner",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("🎯 NSE F&O All-in-One Consolidated Scanner")
    st.markdown("""
    **Comprehensive trading advice combining:** Cash Volume + Price Action + Futures OI + Options Chain + Market Regime
    """)
    
    # Sidebar controls
    st.sidebar.header("⚙️ Scanner Settings")
    
    max_stocks = st.sidebar.slider(
        "Number of stocks to scan",
        min_value=10,
        max_value=100,
        value=30,
        step=10
    )
    
    min_score = st.sidebar.slider(
        "Minimum final score filter",
        min_value=0,
        max_value=100,
        value=50,
        step=5
    )
    
    advice_filter = st.sidebar.multiselect(
        "Filter by advice",
        options=["Strong Buy", "Buy", "Watch", "Wait", "Avoid"],
        default=["Strong Buy", "Buy", "Watch"]
    )
    
    show_only_profitable_rr = st.sidebar.checkbox(
        "Show only Risk-Reward > 1.2",
        value=True
    )
    
    # Run scan button
    if st.sidebar.button("🚀 Run Full Scan", type="primary"):
        with st.spinner("Scanning NSE F&O stocks... This may take a few minutes."):
            df_results = run_full_scan(max_stocks)
            
            # Save to session state
            st.session_state['scan_results'] = df_results
            
            st.success(f"Scan complete! Found {len(df_results)} stocks.")
    
    # Display results if available
    if 'scan_results' in st.session_state:
        df = st.session_state['scan_results']
        
        # Apply filters
        filtered_df = df[df['Final Score'] >= min_score]
        filtered_df = filtered_df[filtered_df['Advice'].isin(advice_filter)]
        
        if show_only_profitable_rr:
            filtered_df = filtered_df[filtered_df['Risk Reward'] >= 1.2]
        
        # Sort by final score
        filtered_df = filtered_df.sort_values('Final Score', ascending=False)
        
        # Top section: Market regime
        st.subheader("🌍 Market Context")
        col1, col2, col3, col4 = st.columns(4)
        
        # Simulated market data
        col1.metric("Nifty Trend", "Above 20 SMA" if np.random.random() > 0.3 else "Below 20 SMA")
        col2.metric("India VIX", "Stable" if np.random.random() > 0.4 else "Rising")
        col3.metric("FII/DII Bias", "Positive" if np.random.random() > 0.4 else "Negative")
        col4.metric("Overall Regime", "Bullish" if np.random.random() > 0.4 else "Neutral/Bearish")
        
        # Main scanner table
        st.subheader(f"📋 Scanner Results ({len(filtered_df)} stocks)")
        
        # Display columns
        display_cols = [
            'Symbol', 'Advice', 'Confidence', 'Final Score',
            'Entry', 'Stop Loss', 'Target 1', 'Target 2',
            'Risk Reward', 'Volume Ratio', 'Reasons', 'Warnings'
        ]
        
        st.dataframe(
            filtered_df[display_cols],
            use_container_width=True,
            hide_index=True
        )
        
        # Detailed view for selected stock
        st.subheader("🔍 Detailed Analysis")
        selected_symbol = st.selectbox(
            "Select a stock for detailed view:",
            options=filtered_df['Symbol'].tolist()
        )
        
        if selected_symbol:
            stock_row = filtered_df[filtered_df['Symbol'] == selected_symbol].iloc[0]
            
            # Create three columns
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"### {selected_symbol}")
                
                # Advice card
                advice_emoji = {
                    "Strong Buy": "🟢",
                    "Buy": "🟡",
                    "Watch": "🟠",
                    "Wait": "⚪",
                    "Avoid": "🔴"
                }
                
                st.markdown(f"""
                **{advice_emoji.get(stock_row['Advice'], '')} {stock_row['Advice']}**
                
                **Confidence:** {stock_row['Confidence']}  
                **Final Score:** {stock_row['Final Score']}/100
                """)
                
                # Trade plan
                if pd.notna(stock_row['Entry']):
                    st.markdown("""
                    #### 📊 Trade Plan
                    """)
                    
                    tp_col1, tp_col2 = st.columns(2)
                    
                    with tp_col1:
                        st.metric("Entry", f"₹{stock_row['Entry']:.2f}")
                        st.metric("Stop Loss", f"₹{stock_row['Stop Loss']:.2f}")
                    
                    with tp_col2:
                        st.metric("Target 1", f"₹{stock_row['Target 1']:.2f}")
                        st.metric("Target 2", f"₹{stock_row['Target 2']:.2f}")
                    
                    rr_col1, rr_col2 = st.columns(2)
                    with rr_col1:
                        st.metric("Risk-Reward", f"1 : {stock_row['Risk Reward']:.2f}")
                    with rr_col2:
                        risk = stock_row['Entry'] - stock_row['Stop Loss']
                        position_size = "Medium" if stock_row['Risk Reward'] >= 1.5 else "Small" if stock_row['Risk Reward'] >= 1.2 else "Very Small"
                        st.metric("Position Size", position_size)
                    
                    st.info(f"**Invalidation:** Close below ₹{stock_row['Stop Loss']:.2f} or put support breaks")
                
                # Reasons
                st.markdown("#### ✅ Bullish Reasons")
                reasons_list = stock_row['Reasons'].split("; ")
                for reason in reasons_list:
                    if reason.strip():
                        st.write(f"• {reason}")
                
                # Warnings
                if stock_row['Warnings'] != "None":
                    st.markdown("#### ⚠️ Warnings")
                    warnings_list = stock_row['Warnings'].split("; ")
                    for warning in warnings_list:
                        if warning.strip():
                            st.write(f"• {warning}")
            
            with col2:
                # Price chart
                if selected_symbol:
                    chart = create_price_chart(selected_symbol, type('obj', (object,), {
                        'trade_plan': type('tp', (object,), {
                            'entry': stock_row['Entry'] if pd.notna(stock_row['Entry']) else None,
                            'stop_loss': stock_row['Stop Loss'] if pd.notna(stock_row['Stop Loss']) else None,
                            'target_1': stock_row['Target 1'] if pd.notna(stock_row['Target 1']) else None
                        })()
                    })())
                    st.plotly_chart(chart, use_container_width=True)
            
            with col3:
                # Score breakdown
                st.markdown("#### 📈 Score Breakdown")
                
                score_data = pd.DataFrame({
                    'Component': ['Cash', 'Price', 'Options', 'Futures', 'Market', 'Risk Penalty'],
                    'Score': [
                        stock_row['Cash Score'],
                        stock_row['Price Score'],
                        stock_row['Options Score'],
                        stock_row['Futures Score'],
                        stock_row['Market Score'],
                        -stock_row['Risk Penalty']
                    ]
                })
                
                st.bar_chart(
                    score_data.set_index('Component'),
                    use_container_width=True
                )
                
                # Additional metrics
                st.markdown("#### 📊 Additional Metrics")
                st.metric("Volume Ratio", f"{stock_row['Volume Ratio']:.2f}x")
                if pd.notna(stock_row.get('PCR Change')):
                    st.metric("PCR Change", f"{stock_row['PCR Change']:.3f}")
    
    else:
        # Initial state
        st.info("👈 Click 'Run Full Scan' in the sidebar to start scanning NSE F&O stocks")
        
        # Show example output format
        st.markdown("""
        ### 📋 Example Output Format
        
        For each stock, the scanner provides:
        
        | Field | Description |
        |-------|-------------|
        | **Advice** | Strong Buy / Buy / Watch / Wait / Avoid |
        | **Confidence** | High / Medium / Low |
        | **Final Score** | 0-100 composite score |
        | **Entry** | Recommended entry price |
        | **Stop Loss** | Risk management level |
        | **Target 1 & 2** | Profit booking levels |
        | **Risk-Reward** | Reward-to-risk ratio |
        | **Reasons** | Why this signal was generated |
        | **Warnings** | Risk factors to consider |
        
        ### 🎯 Scoring Model
        
        - **Cash Score (20 pts):** Volume burst, average volume, bullish close
        - **Price Score (20 pts):** Breakout, trend, RSI momentum
        - **Delivery Score (10 pts):** Delivery percentage confirmation
        - **Futures Score (15 pts):** Futures price, OI change, premium
        - **Options Score (20 pts):** PCR, put/call OI changes, IV percentile
        - **Market Score (10 pts):** Nifty trend, VIX, FII/DII bias
        - **Risk Penalty (-15 pts):** Events, bans, high IV, unwinding
        
        ### ⚡ Decision Rules
        
        - **Strong Buy:** Score ≥ 80, no major warnings
        - **Buy:** Score ≥ 65
        - **Watch:** Score ≥ 50 (developing setup)
        - **Wait:** Score ≥ 35 (needs confirmation)
        - **Avoid:** Score < 35 OR hard vetoes (F&O ban, earnings)
        """)


if __name__ == "__main__":
    main()
