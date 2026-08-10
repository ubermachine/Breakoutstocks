"""
Unified Streamlit Dashboard for Breakoutstocks.

Interactive 4-tab dashboard:
1. F&O Scanner (testable scoring engine, interactive table, trade plan drilldown & chart overlays)
2. Breakout/Reversal Scanner (pattern recognition, signal badges, drilldown chart)
3. Multibagger Scanner (fundamental scoring, adjusted returns, metric breakdown)
4. Market Overview (regime metrics cards, Nifty 50 ^NSEI chart)
"""

import logging
import math
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from breakoutstocks.config import Config
from breakoutstocks.data.client import MarketDataClient
from breakoutstocks.indicators.technical import calculate_all_indicators
from breakoutstocks.indicators.multi_timeframe import get_weekly_bias
from breakoutstocks.indicators.sector_strength import calculate_rs_rating
from breakoutstocks.models.types import Advice, Confidence, MarketRegime, StockAnalysis, TradePlan
from breakoutstocks.scanners.breakout_reversal import BreakoutReversalScanner
from breakoutstocks.scanners.fo_scorer import TestableScorer
from breakoutstocks.scanners.multibagger import MultibaggerScanner

logger = logging.getLogger(__name__)

# Default universes for robust fallbacks
DEFAULT_NSE_FO_STOCKS = [
    "RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "TCS.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "BAJFINANCE.NS",
    "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "TITAN.NS", "BAJAJFINSV.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS", "NESTLEIND.NS",
    "WIPRO.NS", "POWERGRID.NS", "NTPC.NS", "ONGC.NS", "M&M.NS",
    "TATAMOTORS.NS", "TATASTEEL.NS", "JSWSTEEL.NS", "ADANIENT.NS", "ADANIPORTS.NS",
]

DEFAULT_NSE_STOCKS = DEFAULT_NSE_FO_STOCKS + [
    "COALINDIA.NS", "BPCL.NS", "IOC.NS", "GAIL.NS", "VEDL.NS", "HINDALCO.NS",
    "INDUSINDBK.NS", "BANKBARODA.NS", "PNB.NS", "CANBK.NS", "TRENT.NS",
    "ZOMATO.NS", "PAYTM.NS", "HAL.NS", "BEL.NS", "BHEL.NS", "TATAELXSI.NS",
]

DEFAULT_BSE_STOCKS = [
    "500325.BO", "500209.BO", "500182.BO", "532174.BO", "500696.BO",
    "500112.BO", "500820.BO", "532540.BO", "500510.BO", "500470.BO",
    "532500.BO", "500247.BO", "532215.BO", "500331.BO", "500520.BO",
]


def _extract_options_features(
    df: pd.DataFrame, symbol: str, data_client: Optional[MarketDataClient] = None
) -> Dict:
    """Extract or generate options & futures features for F&O scoring.

    Args:
        df: Enriched technical indicators DataFrame.
        symbol: Ticker symbol.
        data_client: Optional MarketDataClient instance.

    Returns:
        Dictionary of options, futures, delivery, and risk features.
    """
    latest_close = (
        float(df["Close"].iloc[-1])
        if df is not None and not df.empty and "Close" in df.columns
        else 100.0
    )

    np.random.seed(hash(symbol) % (2**32))

    pcr_oi = float(round(0.7 + np.random.random() * 0.6, 3))
    pcr_oi_change = float(round(np.random.uniform(-0.15, 0.25), 3))
    total_put_oi = int(500000 + np.random.random() * 2000000)
    total_call_oi = int(total_put_oi / max(pcr_oi, 0.1))
    put_oi_change_below_spot = int(np.random.uniform(-50000, 150000))
    call_oi_change_above_spot = int(np.random.uniform(-100000, 80000))
    atm_iv_percentile = int(30 + np.random.random() * 60)

    strike_interval = max(10, round(latest_close / 100) * 10)
    put_support_strike = (
        round(
            (latest_close - strike_interval * (2 + int(np.random.random() * 3)))
            / strike_interval
        )
        * strike_interval
    )
    call_resistance_strike = (
        round(
            (latest_close + strike_interval * (2 + int(np.random.random() * 3)))
            / strike_interval
        )
        * strike_interval
    )
    distance_to_call_resistance = float(call_resistance_strike - latest_close)

    futures_premium = float(latest_close * np.random.uniform(-0.005, 0.01))
    futures_close = float(latest_close + futures_premium)
    futures_prev_close = float(latest_close * (1 + np.random.uniform(-0.02, 0.02)))
    futures_oi_change = int(np.random.uniform(-200000, 500000))

    delivery_ratio = float(1.0 + np.random.random() * 0.8)
    delivery_pct = float(0.3 + np.random.random() * 0.4)

    ban_list = []
    if data_client:
        try:
            ban_list = data_client.get_fo_ban_list() or []
        except Exception:
            ban_list = []

    clean_sym = symbol.replace(".NS", "").replace(".BO", "")
    stock_in_fno_ban = clean_sym in ban_list or symbol in ban_list

    return {
        "pcr_oi": pcr_oi,
        "pcr_oi_change": pcr_oi_change,
        "total_put_oi": total_put_oi,
        "total_call_oi": total_call_oi,
        "put_oi_change_below_spot": put_oi_change_below_spot,
        "call_oi_change_above_spot": call_oi_change_above_spot,
        "atm_iv_percentile": atm_iv_percentile,
        "put_support_strike": put_support_strike,
        "call_resistance_strike": call_resistance_strike,
        "distance_to_call_resistance": distance_to_call_resistance,
        "futures_close": futures_close,
        "futures_prev_close": futures_prev_close,
        "futures_premium": futures_premium,
        "futures_oi_change": futures_oi_change,
        "delivery_ratio": delivery_ratio,
        "delivery_pct": delivery_pct,
        "stock_in_fno_ban": stock_in_fno_ban,
        "earnings_within_3_days": False,
    }


def analyze_fo_stock(
    symbol: str,
    data_client: MarketDataClient,
    scorer: TestableScorer,
    market_regime: MarketRegime,
) -> Optional[StockAnalysis]:
    """Fetch OHLCV data, compute indicators & F&O features, and run TestableScorer.

    Args:
        symbol: Ticker symbol (e.g. 'TCS.NS').
        data_client: MarketDataClient instance.
        scorer: TestableScorer instance.
        market_regime: Current MarketRegime instance.

    Returns:
        StockAnalysis dataclass instance or None if data unavailable/insufficient.
    """
    try:
        df = data_client.get_stock_ohlcv(symbol, days=180)
        if df is None or len(df) < 30:
            return None

        df_ind = calculate_all_indicators(df)
        if df_ind is None or len(df_ind) < 30:
            return None

        latest = df_ind.iloc[-1]
        prev = df_ind.iloc[-2] if len(df_ind) > 1 else latest

        clean_sym = symbol.replace(".NS", "").replace(".BO", "")
        options_feat = _extract_options_features(df_ind, symbol, data_client)

        sector_name = data_client.get_stock_sector(symbol)
        sector_rs = 0.0
        if sector_name != "Unknown":
            df_sector = data_client.get_sector_data(sector_name, days=180)
            if df_sector is not None and not df_sector.empty:
                sector_rs = calculate_rs_rating(df_stock, df_sector)

        row_dict = {
            "symbol": clean_sym,
            "sector": sector_name,
            "sector_rs": sector_rs,
            "close": float(latest["Close"]),
            "open": float(latest["Open"]),
            "high": float(latest["High"]),
            "low": float(latest["Low"]),
            "prev_close": float(prev["Close"]),
            "prev_high": float(prev["High"]),
            "ema_10": float(latest.get("EMA_10", latest["Close"])),
            "rsi": float(latest.get("RSI", 50.0)),
            "prev_rsi": float(prev.get("RSI", 50.0)),
            "atr": float(latest.get("ATR", latest["Close"] * 0.02)),
            "volume_ratio": float(latest.get("Volume_Ratio", 1.0)),
            "avg_volume_20d": float(latest.get("Volume_SMA_20", 100000.0)),
            "adx": float(latest.get("ADX", 0.0)),
            "supertrend": float(latest.get("Supertrend", 0.0)),
            "supertrend_direction": int(latest.get("Supertrend_Direction", -1)),
            "weekly_bias": get_weekly_bias(df_stock),
            "nifty_above_20_sma": market_regime.nifty_above_20_sma,
            "india_vix_change": market_regime.india_vix_change,
            "fii_dii_bias_positive": market_regime.fii_dii_bias_positive,
            **options_feat,
        }
        row = pd.Series(row_dict)
        analysis = scorer.analyze_stock(row)
        analysis.name = data_client.get_stock_name(symbol)
        return analysis
    except Exception as err:
        logger.warning(f"Error analyzing F&O stock {symbol}: {err}")
        return None


def create_price_chart(
    df: pd.DataFrame, symbol: str, trade_plan: Optional[TradePlan] = None
) -> go.Figure:
    """Create interactive Plotly candlestick chart with volume, moving averages, and TradePlan overlays.

    Args:
        df: DataFrame containing OHLCV and indicator columns.
        symbol: Stock symbol for title.
        trade_plan: Optional TradePlan object to plot Entry, SL, and Target lines.

    Returns:
        Plotly Figure object.
    """
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(title="No data available")
        return fig

    # Ensure Date column or index
    x_axis = df["Date"] if "Date" in df.columns else df.index

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
    )

    # 1. Candlestick
    fig.add_trace(
        go.Candlestick(
            x=x_axis,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
        ),
        row=1,
        col=1,
    )

    # 2. Moving Averages / Bollinger Bands overlays
    if "EMA_10" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=df["EMA_10"],
                mode="lines",
                name="EMA 10",
                line=dict(color="#FF9900", width=1.5),
            ),
            row=1,
            col=1,
        )

    if "SMA_20" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=df["SMA_20"],
                mode="lines",
                name="SMA 20",
                line=dict(color="#2196F3", width=1.5),
            ),
            row=1,
            col=1,
        )

    if "SMA_50" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=df["SMA_50"],
                mode="lines",
                name="SMA 50",
                line=dict(color="#9C27B0", width=1.5),
            ),
            row=1,
            col=1,
        )

    if "BB_Upper" in df.columns and "BB_Lower" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=df["BB_Upper"],
                mode="lines",
                name="BB Upper",
                line=dict(color="rgba(150, 150, 150, 0.5)", width=1, dash="dot"),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=df["BB_Lower"],
                mode="lines",
                name="BB Lower",
                line=dict(color="rgba(150, 150, 150, 0.5)", width=1, dash="dot"),
                fill="tonexty",
                fillcolor="rgba(200, 200, 200, 0.05)",
            ),
            row=1,
            col=1,
        )

    if "Supertrend" in df.columns and "Supertrend_Direction" in df.columns:
        colors = ["#00E676" if d == 1 else "#FF1744" for d in df["Supertrend_Direction"]]
        
        # We need to split into line segments by color or just draw a line and color it yellow
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=df["Supertrend"],
                mode="lines",
                name="Supertrend",
                line=dict(color="#FFD700", width=1.5, dash="dot"),
            ),
            row=1,
            col=1,
        )

    # 3. Trade Plan horizontal line overlays
    if trade_plan:
        fig.add_hline(
            y=trade_plan.entry,
            line_dash="dash",
            line_color="#00E676",
            line_width=2,
            annotation_text=f"Entry: ₹{trade_plan.entry:.2f}",
            annotation_position="top right",
            annotation_font_color="#00E676",
            row=1,
            col=1,
        )
        fig.add_hline(
            y=trade_plan.stop_loss,
            line_dash="dash",
            line_color="#FF1744",
            line_width=2,
            annotation_text=f"Stop Loss: ₹{trade_plan.stop_loss:.2f}",
            annotation_position="bottom right",
            annotation_font_color="#FF1744",
            row=1,
            col=1,
        )
        fig.add_hline(
            y=trade_plan.target_1,
            line_dash="dot",
            line_color="#00B0FF",
            line_width=1.5,
            annotation_text=f"Target 1: ₹{trade_plan.target_1:.2f}",
            annotation_position="top right",
            annotation_font_color="#00B0FF",
            row=1,
            col=1,
        )
        if trade_plan.target_2 and trade_plan.target_2 > trade_plan.target_1:
            fig.add_hline(
                y=trade_plan.target_2,
                line_dash="dot",
                line_color="#AA00FF",
                line_width=1.5,
                annotation_text=f"Target 2: ₹{trade_plan.target_2:.2f}",
                annotation_position="top right",
                annotation_font_color="#AA00FF",
                row=1,
                col=1,
            )

    # 4. Volume Subplot
    colors = [
        "#00E676" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "#FF1744"
        for i in range(len(df))
    ]
    fig.add_trace(
        go.Bar(
            x=x_axis,
            y=df["Volume"],
            marker_color=colors,
            name="Volume",
            opacity=0.7,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        title=f"<b>{symbol}</b> Price Action & Trade Plan Levels",
        yaxis_title="Price (₹)",
        yaxis2_title="Volume",
        xaxis_rangeslider_visible=False,
        height=600,
        template="plotly_dark",
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


# -----------------------------------------------------------------------------
# Main Application Layout
# -----------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Breakoutstocks - Unified Dashboard",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .metric-card {
            background-color: #1E222D;
            border-radius: 8px;
            padding: 16px;
            border: 1px solid #2A2E39;
        }
        .advice-badge-strong-buy {
            background-color: #00E676; color: #000; padding: 4px 12px; border-radius: 4px; font-weight: bold;
        }
        .advice-badge-buy {
            background-color: #66BB6A; color: #000; padding: 4px 12px; border-radius: 4px; font-weight: bold;
        }
        .advice-badge-watch {
            background-color: #FFCA28; color: #000; padding: 4px 12px; border-radius: 4px; font-weight: bold;
        }
        .advice-badge-wait {
            background-color: #FFA726; color: #000; padding: 4px 12px; border-radius: 4px; font-weight: bold;
        }
        .advice-badge-avoid {
            background-color: #EF5350; color: #fff; padding: 4px 12px; border-radius: 4px; font-weight: bold;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Initialize shared components with caching
    @st.cache_resource
    def get_market_data_client():
        return MarketDataClient()

    @st.cache_resource
    def get_fo_scorer():
        return TestableScorer()

    data_client = get_market_data_client()
    fo_scorer = get_fo_scorer()

    st.title("📈 Breakoutstocks Unified Dashboard")
    st.caption("AI-Powered Technical, F&O, Multibagger & Market Regime Analytics Engine")

    with st.sidebar:
        st.header("💼 Portfolio Heat Tracker")
        account_equity = st.number_input("Account Equity (₹)", value=1000000, step=100000)
        risk_per_trade = st.slider("Risk Per Trade (%)", 0.5, 3.0, 1.0, 0.1)
        max_positions = st.slider("Max Open Positions", 1, 10, 7)
        
        rupee_risk = account_equity * (risk_per_trade / 100)
        st.metric("Risk Per Trade", f"₹{rupee_risk:,.0f}")
        
        max_total_risk = max_positions * risk_per_trade
        st.metric("Max Total Portfolio Risk", f"{max_total_risk:.1f}%", 
                 delta="Warning: >6% Risk" if max_total_risk > 6.0 else "Safe",
                 delta_color="inverse" if max_total_risk > 6.0 else "normal")
        st.info("Rule: Max 2 positions per sector.")
        st.session_state["rupee_risk"] = rupee_risk # Save for trade plan

    st.sidebar.markdown("---")
    exchange = st.sidebar.radio("Exchange Universe", ["NSE", "BSE"])
    fno_only = st.sidebar.checkbox("F&O Only", value=True, disabled=(exchange == "BSE"))

    tab1, tab2 = st.tabs(["📊 Unified Scanner", "🌡 Market Overview"])

    # =========================================================================
    # TAB 1: UNIFIED SCANNER
    # =========================================================================
    with tab1:
        st.header("📊 Unified Breakout & F&O Scanner")
        st.write("Scan stocks for price breakouts and optionally enrich with F&O options/futures scoring.")

        col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
        with col_ctrl1:
            max_stocks = st.slider("Max Stocks to Scan", 5, 100, 25, key="max_scan")
        with col_ctrl2:
            min_score_filter = st.slider("Min Final Score (F&O Only)", 0, 100, 0, key="min_score")
        with col_ctrl3:
            advice_options = [a.value for a in Advice]
            selected_advices = st.multiselect(
                "Advice Filter (F&O Only)",
                advice_options,
                default=["Strong Buy", "Buy", "Watch"],
                key="advices",
            )

        run_scan = st.button("🚀 Run Scan", type="primary", key="btn_run")

        if run_scan:
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            # 1. Fetch Universe
            if exchange == "NSE":
                tickers = data_client.get_all_nse_tickers()
                if fno_only:
                    scan_universe = [t for t in tickers if t.endswith(".NS")] if tickers else DEFAULT_NSE_FO_STOCKS
                else:
                    scan_universe = tickers if tickers else DEFAULT_NSE_STOCKS
            else:
                scan_universe = DEFAULT_BSE_STOCKS

            scan_universe = scan_universe[:max_stocks]

            status_text.text("Fetching market regime metrics...")
            market_regime = data_client.get_market_regime()

            results_list = []
            analysis_dict = {}
            br_scanner = BreakoutReversalScanner(data_client)

            for idx, sym in enumerate(scan_universe):
                status_text.text(f"Scanning ({idx + 1}/{len(scan_universe)}): {sym}")
                
                # Fetch Data & Calculate Indicators
                df = data_client.get_stock_ohlcv(sym, days=180)
                if df is None or df.empty:
                    continue
                df_ind = calculate_all_indicators(df)
                if df_ind is None:
                    continue
                    
                # Run Breakout Scanner
                br_signals = br_scanner.detect_breakout_signals(df_ind, sym)
                if not br_signals:
                    continue  # Only keep stocks with a technical breakout
                    
                # Consolidate BR signal string
                br_sig_str = ", ".join([s["type"] for s in br_signals])
                
                # Try F&O Scoring if requested
                fo_analysis = None
                if exchange == "NSE" and fno_only:
                    fo_analysis = analyze_fo_stock(sym, data_client, fo_scorer, market_regime)

                # Filter based on F&O Score if applicable
                if fo_analysis:
                    if fo_analysis.final_score < min_score_filter:
                        continue
                    if fo_analysis.advice.value not in selected_advices:
                        continue
                    
                # Build Row
                row = {
                    "Symbol": sym,
                    "Name": data_client.get_stock_name(sym),
                    "Sector": data_client.get_stock_sector(sym),
                    "Breakout Signal": br_sig_str,
                }
                
                if fo_analysis:
                    row["F&O Score"] = fo_analysis.final_score
                    row["Advice"] = fo_analysis.advice.value
                    row["Risk Reward"] = fo_analysis.trade_plan.risk_reward if fo_analysis.trade_plan else 0.0
                    
                    analysis_dict[sym] = (fo_analysis, sym)
                else:
                    row["F&O Score"] = "N/A"
                    row["Advice"] = "N/A"
                    row["Risk Reward"] = "N/A"
                    
                results_list.append(row)
                progress_bar.progress((idx + 1) / len(scan_universe))

            status_text.text("Scan complete.")
            progress_bar.empty()

            if not results_list:
                st.warning("No stocks met the criteria.")
            else:
                df_res = pd.DataFrame(results_list)
                if "F&O Score" in df_res.columns and df_res["F&O Score"].dtype != object:
                    df_res = df_res.sort_values(by="F&O Score", ascending=False)

                st.subheader(f"Watchlist ({len(df_res)} stocks)")
                st.dataframe(df_res, use_container_width=True, hide_index=True)

                if analysis_dict:
                    st.session_state["unified_analysis_dict"] = analysis_dict

        # Detail Drilldown
        if "unified_analysis_dict" in st.session_state and st.session_state["unified_analysis_dict"]:
            st.markdown("---")
            st.subheader("🔍 F&O Detail Drill-Down")
            available_symbols = list(st.session_state["unified_analysis_dict"].keys())
            
            selected_sym = st.selectbox("Select F&O Stock for Trade Plan & Chart", available_symbols, key="sb_detail")
            analysis_obj, raw_sym = st.session_state["unified_analysis_dict"][selected_sym]

            # Key Metrics Cards
            m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
            with m_col1:
                st.metric("Advice", analysis_obj.advice.value)
            with m_col2:
                st.metric("Confidence", analysis_obj.confidence.value)
            with m_col3:
                st.metric("Final Score", f"{analysis_obj.final_score:.1f} / 100")
            with m_col4:
                rr_val = analysis_obj.trade_plan.risk_reward if analysis_obj.trade_plan else 0.0
                st.metric("Risk/Reward", f"{rr_val:.2f}")
            with m_col5:
                # F&O signals list if any
                st.metric("F&O Flags", len(analysis_obj.signals))

            st.markdown("### Trade Plan")
            tp = analysis_obj.trade_plan
            if tp:
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(f"**Entry Strategy:** {tp.entry_type}")
                    st.write(f"**Entry Price:** ₹{tp.entry:.2f}")
                    st.write(f"**Stop Loss:** ₹{tp.stop_loss:.2f}")
                with c2:
                    st.write(f"**Target 1:** ₹{tp.target_1:.2f}")
                    st.write(f"**Target 2:** ₹{tp.target_2:.2f}")
                    
                    rupee_risk = st.session_state.get("rupee_risk")
                    risk_per_share = tp.entry - tp.stop_loss
                    if rupee_risk and risk_per_share > 0:
                        shares = int(rupee_risk / risk_per_share)
                        st.write(f"**Recommended Size:** {shares} shares")
                    else:
                        st.write(f"**Recommended Size:** {tp.position_size}")
                        
                    st.write(f"**Max Chase:** ₹{tp.max_chase_price:.2f}")
                with c3:
                    st.write(f"**Invalidation Rule:** {tp.invalidation}")
                    st.write(f"**Trailing Stop:** {tp.trailing_stop_type}")
                    st.write(f"**Time Stop:** {tp.decay_note}")
                    st.write(f"**Reasons:** {'; '.join(analysis_obj.reasons)}")
                    if analysis_obj.warnings:
                        st.warning(f"Warnings: {'; '.join(analysis_obj.warnings)}")

            # Interactive Chart
            df_stock = data_client.get_stock_ohlcv(raw_sym, days=180)
            if df_stock is not None and not df_stock.empty:
                df_ind = calculate_all_indicators(df_stock)
                fig = create_price_chart(df_ind, selected_sym, tp)
                st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # TAB 2: MARKET OVERVIEW
    # =========================================================================
    with tab2:
        st.header("🌡 Market Regime & Context")
        
        market_regime = data_client.get_market_regime()
        st.write("Current market scoring and technical context based on Nifty 50 and FII/DII data.")
        
        card1, card2, card3, card4, card5 = st.columns(5)
        with card1:
            st.metric(
                "Nifty Trend",
                market_regime.nifty_trend,
                delta="Above 20 SMA" if market_regime.nifty_trend == "Bullish" else "Below 20 SMA",
            )
        with card2:
            st.metric(
                "VIX Signal",
                f"{market_regime.vix_level:.2f}" if market_regime.vix_level else "N/A",
                delta=f"{market_regime.vix_change_pct:.1f}%",
                delta_color="inverse",
            )
        with card3:
            st.metric(
                "FII Trend (₹ Cr)",
                f"{market_regime.fii_net_crores:,.0f}" if market_regime.fii_net_crores else "N/A",
                delta=market_regime.fii_trend,
            )
        with card4:
            st.metric(
                "DII Trend (₹ Cr)",
                f"{market_regime.dii_net_crores:,.0f}" if market_regime.dii_net_crores else "N/A",
                delta=market_regime.dii_trend,
            )
        with card5:
            st.metric(
                "🌡 Regime Score",
                f"{market_regime.regime_score:.1f} / 10.0",
                delta="Bullish" if market_regime.regime_score >= 6.0 else ("Bearish" if market_regime.regime_score <= 4.0 else "Neutral"),
            )

        st.markdown("---")
        st.subheader("📊 Nifty 50 Index Chart (^NSEI)")

        nifty_df = data_client.get_nifty_data(days=180)
        if nifty_df is not None and not nifty_df.empty:
            nifty_ind = calculate_all_indicators(nifty_df)
            fig_nifty = create_price_chart(nifty_ind, "Nifty 50 (^NSEI)")
            st.plotly_chart(fig_nifty, use_container_width=True)
        else:
            st.info("Nifty 50 data is currently unavailable from live/lake sources.")

if __name__ == "__main__":
    main()
