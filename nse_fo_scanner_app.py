
import streamlit as st
import pandas as pd
import glob
import os

st.set_page_config(page_title="NSE F&O Scanner", layout="wide")

st.title("🚀 NSE F&O Breakout & Reversal Scanner")
st.markdown("""
This scanner identifies NSE F&O stocks with potential 2-5 day swing trading opportunities using:
- **Cash Market**: Volume burst, price action, RSI, candlestick patterns
- **Futures**: OI changes, premium/discount
- **Options**: PCR, OI changes near spot, IV, support/resistance
- **Market Regime**: Nifty trend, India VIX, FII/DII flow
""")

# Load latest results
result_files = glob.glob("nse_fo_scan_results/nse_fo_scan_all_*.csv")

if not result_files:
    st.warning("No scan results found. Run the scanner first: `python nse_fo_scanner.py`")
    st.stop()

latest_file = sorted(result_files)[-1]
df = pd.read_csv(latest_file)

# Sidebar filters
st.sidebar.header("Filters")
min_score = st.sidebar.slider("Min Final Score", 0, 100, 50)
min_volume_ratio = st.sidebar.slider("Min Volume Ratio", 1.0, 5.0, 2.0)
signal_type = st.sidebar.selectbox("Signal Type", ["All", "BREAKOUT", "REVERSAL"])
min_option_score = st.sidebar.slider("Min Option Score", 0, 35, 15)

# Apply filters
filtered_df = df[
    (df['Final_Score'] >= min_score) &
    (df['Volume_Ratio'] >= min_volume_ratio) &
    (df['Option_Score'] >= min_option_score)
]

if signal_type != "All":
    filtered_df = filtered_df[filtered_df['Signal_Type'] == signal_type]

# Display results
st.subheader(f"Scan Results ({len(filtered_df)} stocks)")

# Key columns to display
display_cols = [
    'Symbol', 'Cash_Close', 'Change_Pct', 'Volume_Ratio', 'RSI',
    'Signal_Type', 'Cash_Score', 'Futures_Score', 'Option_Score',
    'Final_Score', 'PCR_OI', 'Put_Support_Strike', 'Call_Resistance_Strike',
    'ATM_IV', 'Latest_Date'
]

available_cols = [col for col in display_cols if col in filtered_df.columns]
st.dataframe(
    filtered_df[available_cols].sort_values('Final_Score', ascending=False),
    use_container_width=True,
    hide_index=True
)

# Detailed view
st.subheader("Detailed Analysis")
selected_symbol = st.selectbox("Select Stock", df['Symbol'].unique())

if selected_symbol:
    stock_data = df[df['Symbol'] == selected_symbol].iloc[0]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Cash Score", stock_data.get('Cash_Score', 'N/A'))
        st.metric("Volume Ratio", stock_data.get('Volume_Ratio', 'N/A'))
        st.metric("RSI", stock_data.get('RSI', 'N/A'))
    
    with col2:
        st.metric("Futures Score", stock_data.get('Futures_Score', 'N/A'))
        st.metric("PCR", stock_data.get('PCR_OI', 'N/A'))
        st.metric("ATM IV", stock_data.get('ATM_IV', 'N/A'))
    
    with col3:
        st.metric("Option Score", stock_data.get('Option_Score', 'N/A'))
        st.metric("Final Score", stock_data.get('Final_Score', 'N/A'))
        st.metric("Signal", stock_data.get('Signal_Type', 'N/A'))
    
    st.write("**Key Levels:**")
    st.write(f"- Put Support Strike: {stock_data.get('Put_Support_Strike', 'N/A')}")
    st.write(f"- Call Resistance Strike: {stock_data.get('Call_Resistance_Strike', 'N/A')}")
    st.write(f"- Distance to Support: {stock_data.get('Distance_To_Support', 'N/A')}")
    st.write(f"- Distance to Resistance: {stock_data.get('Distance_To_Resistance', 'N/A')}")

# Market regime
st.subheader("Market Regime")
regime_cols = [col for col in df.columns if 'Regime' in col or 'Nifty' in col or 'VIX' in col]
if any(col in df.columns for col in regime_cols):
    regime_data = df[regime_cols].iloc[0]
    st.json(regime_data.to_dict())
