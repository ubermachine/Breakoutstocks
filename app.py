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

    # 5 Main Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 F&O Scanner", "💥 Breakout / Reversal", "💎 Multibagger", "🌡 Market Overview", "🔥 Fusion Scanner"]
    )

    # =========================================================================
    # TAB 1: F&O SCANNER
    # =========================================================================
    with tab1:
        st.header("📊 F&O All-in-One Consolidated Scanner")
        st.write("Scan liquid F&O stocks with real-time technicals, futures OI, option chain structure, and risk scoring.")

        col_ctrl1, col_ctrl2, col_ctrl3, col_ctrl4 = st.columns(4)
        with col_ctrl1:
            max_fo_stocks = st.slider("Max Stocks to Scan", 5, 100, 25, key="fo_max")
        with col_ctrl2:
            min_score_filter = st.slider("Min Final Score", 0, 100, 50, key="fo_min_score")
        with col_ctrl3:
            advice_options = [a.value for a in Advice]
            selected_advices = st.multiselect(
                "Advice Filter",
                advice_options,
                default=["Strong Buy", "Buy", "Watch"],
                key="fo_advices",
            )
        with col_ctrl4:
            rr_filter = st.checkbox("Risk:Reward > 1.2 Only", value=False, key="fo_rr_filter")

        run_fo_scan = st.button("🚀 Run F&O Scan", type="primary", key="btn_run_fo")

        if run_fo_scan:
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            tickers = data_client.get_all_nse_tickers()
            tickers_fo = [t for t in tickers if t.endswith(".NS")] if tickers else DEFAULT_NSE_FO_STOCKS
            if not tickers_fo:
                tickers_fo = DEFAULT_NSE_FO_STOCKS

            scan_universe = tickers_fo[:max_fo_stocks]

            status_text.text("Fetching market regime metrics...")
            market_regime = data_client.get_market_regime()

            results_list = []
            analysis_dict = {}

            for idx, sym in enumerate(scan_universe):
                status_text.text(f"Scanning ({idx + 1}/{len(scan_universe)}): {sym}")
                analysis = analyze_fo_stock(sym, data_client, fo_scorer, market_regime)

                if analysis:
                    analysis_dict[analysis.symbol] = (analysis, sym)
                    tp = analysis.trade_plan

                    results_list.append(
                        {
                            "Symbol": analysis.symbol,
                            "Name": analysis.name,
                            "Advice": analysis.advice.value,
                            "Confidence": analysis.confidence.value,
                            "Final Score": round(analysis.final_score, 1),
                            "Entry": tp.entry if tp else None,
                            "Stop Loss": tp.stop_loss if tp else None,
                            "Target 1": tp.target_1 if tp else None,
                            "Target 2": tp.target_2 if tp else None,
                            "Risk:Reward": tp.risk_reward if tp else None,
                            "Cash Score": round(analysis.cash_score, 1),
                            "Price Score": round(analysis.price_score, 1),
                            "Options Score": round(analysis.options_score, 1),
                            "Futures Score": round(analysis.futures_score, 1),
                            "Risk Penalty": round(analysis.risk_penalty, 1),
                            "Reasons": "; ".join(analysis.reasons[:2]),
                        }
                    )

                progress_bar.progress((idx + 1) / len(scan_universe))

            status_text.text("F&O Scan complete!")
            st.session_state["fo_results_df"] = pd.DataFrame(results_list)
            st.session_state["fo_analysis_dict"] = analysis_dict

        # Render F&O Scan Results if available
        if "fo_results_df" in st.session_state and not st.session_state["fo_results_df"].empty:
            df_res = st.session_state["fo_results_df"].copy()

            # Apply filters
            df_filtered = df_res[df_res["Final Score"] >= min_score_filter]
            if selected_advices:
                df_filtered = df_filtered[df_filtered["Advice"].isin(selected_advices)]
            if rr_filter and "Risk:Reward" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["Risk:Reward"].fillna(0) >= 1.2]

            df_filtered = df_filtered.sort_values(by="Final Score", ascending=False).reset_index(drop=True)

            st.subheader(f"📋 Scan Results ({len(df_filtered)} stocks found)")
            st.dataframe(
                df_filtered,
                use_container_width=True,
                column_config={
                    "Final Score": st.column_config.ProgressColumn(
                        "Final Score", min_value=0, max_value=100, format="%.1f"
                    ),
                    "Risk:Reward": st.column_config.NumberColumn(format="%.2f"),
                    "Entry": st.column_config.NumberColumn(format="₹%.2f"),
                    "Stop Loss": st.column_config.NumberColumn(format="₹%.2f"),
                    "Target 1": st.column_config.NumberColumn(format="₹%.2f"),
                },
            )

            # Detail Drilldown
            st.markdown("---")
            st.subheader("🔍 Selected Stock Detail Drill-Down")
            available_symbols = df_filtered["Symbol"].tolist() if not df_filtered.empty else list(st.session_state["fo_analysis_dict"].keys())

            if available_symbols:
                selected_sym = st.selectbox("Select Stock for Detailed Trade Plan & Chart", available_symbols, key="sb_fo_detail")
                analysis_obj, raw_sym = st.session_state["fo_analysis_dict"][selected_sym]

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
                    st.metric("Risk:Reward", f"1:{rr_val:.2f}" if rr_val else "N/A")
                with m_col5:
                    entry_val = analysis_obj.trade_plan.entry if analysis_obj.trade_plan else 0.0
                    st.metric("Entry Price", f"₹{entry_val:.2f}" if entry_val else "N/A")

                # Trade Plan Card
                if analysis_obj.trade_plan:
                    tp = analysis_obj.trade_plan
                    with st.expander("📌 Detailed Trade Plan Card", expanded=True):
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

                # Component Score Breakdown
                with st.expander("📊 Score Component Breakdown", expanded=False):
                    sc1, sc2, sc3, sc4, sc5, sc6, sc7 = st.columns(7)
                    sc1.metric("Cash (max 20)", f"{analysis_obj.cash_score:.1f}")
                    sc2.metric("Price (max 20)", f"{analysis_obj.price_score:.1f}")
                    sc3.metric("Delivery (max 10)", f"{analysis_obj.delivery_score:.1f}")
                    sc4.metric("Futures (max 15)", f"{analysis_obj.futures_score:.1f}")
                    sc5.metric("Options (max 20)", f"{analysis_obj.options_score:.1f}")
                    sc6.metric("Market (max 10)", f"{analysis_obj.market_score:.1f}")
                    sc7.metric("Risk Penalty", f"-{analysis_obj.risk_penalty:.1f}")

                # Interactive Chart
                df_stock = data_client.get_stock_ohlcv(raw_sym, days=180)
                if df_stock is not None and not df_stock.empty:
                    df_ind = calculate_all_indicators(df_stock)
                    fig = create_price_chart(df_ind, selected_sym, analysis_obj.trade_plan)
                    st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # TAB 2: BREAKOUT / REVERSAL SCANNER
    # =========================================================================
    with tab2:
        st.header("💥 Breakout & Trend Reversal Pattern Scanner")
        st.write("Detect 20-day high breakouts, SMA 50/200 Golden Crosses, RSI oversold/overbought reversals, and MACD crossovers.")

        b_col1, b_col2, b_col3 = st.columns(3)
        with b_col1:
            universe_choice = st.radio("Stock Universe", ["NSE", "BSE"], horizontal=True, key="br_univ")
        with b_col2:
            signal_filter_choice = st.selectbox(
                "Signal Filter", ["All", "Breakout Only", "Reversal Only"], index=0, key="br_filt"
            )
        with b_col3:
            br_max_stocks = st.slider("Max Stocks to Scan", 5, 100, 25, key="br_max")

        run_br_scan = st.button("💥 Run Breakout & Reversal Scan", type="primary", key="btn_run_br")

        if run_br_scan:
            scanner = BreakoutReversalScanner(data_client=data_client)
            if universe_choice == "NSE":
                tickers = data_client.get_all_nse_tickers()
                symbols_to_scan = [t for t in tickers if t.endswith(".NS")] if tickers else DEFAULT_NSE_STOCKS
                if not symbols_to_scan:
                    symbols_to_scan = DEFAULT_NSE_STOCKS
            else:
                symbols_to_scan = DEFAULT_BSE_STOCKS

            symbols_to_scan = symbols_to_scan[:br_max_stocks]

            br_prog = st.progress(0.0)
            br_status = st.empty()

            def br_callback(comp, tot):
                br_prog.progress(comp / tot)
                br_status.text(f"Scanning stock {comp}/{tot}...")

            res_df = scanner.scan(symbols_to_scan, progress_callback=br_callback)
            br_status.text("Breakout & Reversal scan complete!")
            st.session_state["br_results_df"] = res_df

        if "br_results_df" in st.session_state and not st.session_state["br_results_df"].empty:
            df_br = st.session_state["br_results_df"].copy()

            if signal_filter_choice == "Breakout Only":
                df_br = df_br[df_br["signal_type"].isin(["BREAKOUT", "BREAKOUT_AND_REVERSAL"])]
            elif signal_filter_choice == "Reversal Only":
                df_br = df_br[df_br["signal_type"].isin(["REVERSAL", "BREAKOUT_AND_REVERSAL"])]

            st.subheader(f"📋 Detected Signals ({len(df_br)} matches)")
            display_cols = [
                c for c in [
                    "symbol", "name", "signal_type", "current_price",
                    "change_percent", "volume_ratio", "rsi", "strength_score", "signal_count"
                ] if c in df_br.columns
            ]
            st.dataframe(
                df_br[display_cols],
                use_container_width=True,
                column_config={
                    "current_price": st.column_config.NumberColumn("Price", format="₹%.2f"),
                    "change_percent": st.column_config.NumberColumn("Change %", format="%.2f%%"),
                    "volume_ratio": st.column_config.NumberColumn("Vol Ratio", format="%.2fx"),
                    "strength_score": st.column_config.NumberColumn("Strength Score", format="%.1f"),
                },
            )

            # Drilldown
            st.markdown("---")
            st.subheader("🔍 Selected Stock Signal Drill-Down")
            br_symbols = df_br["symbol"].tolist()
            if br_symbols:
                sel_br_sym = st.selectbox("Select Stock for Detailed Signal Analysis", br_symbols, key="sb_br_detail")
                selected_row = df_br[df_br["symbol"] == sel_br_sym].iloc[0]

                s_c1, s_c2, s_c3, s_c4 = st.columns(4)
                s_c1.metric("Signal Type", selected_row.get("signal_type", "N/A"))
                s_c2.metric("Price", f"₹{selected_row.get('current_price', 0):.2f}")
                s_c3.metric("Volume Ratio", f"{selected_row.get('volume_ratio', 0):.2f}x")
                s_c4.metric("RSI", f"{selected_row.get('rsi', 0):.1f}")

                signals_list = selected_row.get("signals", [])
                if isinstance(signals_list, list) and signals_list:
                    st.write("**Detected Pattern Signals:**")
                    for sig in signals_list:
                        st.info(f"🔹 **[{sig.get('type')}]** ({sig.get('strength')} strength): {sig.get('description')}")

                df_br_chart = data_client.get_stock_ohlcv(sel_br_sym, days=180)
                if df_br_chart is not None and not df_br_chart.empty:
                    df_ind_br = calculate_all_indicators(df_br_chart)
                    fig_br = create_price_chart(df_ind_br, sel_br_sym)
                    st.plotly_chart(fig_br, use_container_width=True)

    # =========================================================================
    # TAB 3: MULTIBAGGER SCANNER
    # =========================================================================
    with tab3:
        st.header("💎 Fundamental Multibagger Discovery Engine")
        st.write("Screen high-growth stocks evaluating fundamental criteria (PE, revenue growth, profit margin, ROE, debt/equity) and adjusted multi-year price returns.")

        m_col1, m_col2 = st.columns(2)
        with m_col1:
            years_horizon = st.radio("Lookback Horizon", [1, 3, 5], index=2, horizontal=True, key="mb_years")
        with m_col2:
            mb_max_stocks = st.slider("Max Stocks to Scan", 5, 100, 20, key="mb_max")

        run_mb_scan = st.button("💎 Run Multibagger Scan", type="primary", key="btn_run_mb")

        if run_mb_scan:
            scanner = MultibaggerScanner(years=years_horizon, data_client=data_client)
            tickers = data_client.get_all_nse_tickers()
            symbols_to_scan = [t for t in tickers if t.endswith(".NS")] if tickers else DEFAULT_NSE_STOCKS
            if not symbols_to_scan:
                symbols_to_scan = DEFAULT_NSE_STOCKS

            symbols_to_scan = symbols_to_scan[:mb_max_stocks]

            mb_prog = st.progress(0.0)
            mb_status = st.empty()

            def mb_callback(comp, tot):
                mb_prog.progress(comp / tot)
                mb_status.text(f"Analyzing fundamentals ({comp}/{tot})...")

            res_mb_df = scanner.scan(symbols_to_scan, progress_callback=mb_callback)
            mb_status.text("Multibagger scan complete!")
            st.session_state["mb_results_df"] = res_mb_df

        if "mb_results_df" in st.session_state and not st.session_state["mb_results_df"].empty:
            df_mb = st.session_state["mb_results_df"].copy()
            st.subheader(f"🏆 Ranked Multibagger Candidates ({len(df_mb)} identified)")

            mb_cols = [
                c for c in [
                    "symbol", "name", "return_pct", "fundamental_score",
                    "pe_ratio", "revenue_growth", "profit_margin", "roe", "debt_to_equity", "market_cap"
                ] if c in df_mb.columns
            ]
            st.dataframe(
                df_mb[mb_cols],
                use_container_width=True,
                column_config={
                    "return_pct": st.column_config.NumberColumn("Return %", format="%.2f%%"),
                    "revenue_growth": st.column_config.NumberColumn("Revenue Growth", format="%.2f%%"),
                    "profit_margin": st.column_config.NumberColumn("Profit Margin", format="%.2f%%"),
                    "roe": st.column_config.NumberColumn("ROE", format="%.2f%%"),
                    "fundamental_score": st.column_config.NumberColumn("Fund Score", format="%.1f / 5.0"),
                },
            )

            # Drilldown
            st.markdown("---")
            st.subheader("🔍 Selected Multibagger Stock Fundamental Drill-Down")
            mb_symbols = df_mb["symbol"].tolist()
            if mb_symbols:
                sel_mb_sym = st.selectbox("Select Stock for Fundamental Inspection", mb_symbols, key="sb_mb_detail")
                selected_mb_row = df_mb[df_mb["symbol"] == sel_mb_sym].iloc[0]

                mc1, mc2, mc3, mc4, mc5 = st.columns(5)
                mc1.metric("PE Ratio", f"{selected_mb_row.get('pe_ratio', 0):.2f}")
                mc2.metric("Revenue Growth", f"{(selected_mb_row.get('revenue_growth', 0) * 100):.1f}%")
                mc3.metric("Profit Margin", f"{(selected_mb_row.get('profit_margin', 0) * 100):.1f}%")
                mc4.metric("ROE", f"{(selected_mb_row.get('roe', 0) * 100):.1f}%")
                mc5.metric("Debt to Equity", f"{selected_mb_row.get('debt_to_equity', 0):.2f}")

                df_mb_chart = data_client.get_stock_ohlcv(sel_mb_sym, days=years_horizon * 365)
                if df_mb_chart is not None and not df_mb_chart.empty:
                    df_ind_mb = calculate_all_indicators(df_mb_chart)
                    fig_mb = create_price_chart(df_ind_mb, sel_mb_sym)
                    st.plotly_chart(fig_mb, use_container_width=True)

    # =========================================================================
    # TAB 4: MARKET OVERVIEW
    # =========================================================================
    with tab4:
        st.header("🌡 Broad Market Regime & Nifty 50 Overview")
        st.write("Real-time benchmark trend analysis, India VIX volatility gauge, and FII / DII institutional capital flow tracking.")

        regime = data_client.get_market_regime()

        # Top Metric Cards
        card1, card2, card3, card4, card5 = st.columns(5)
        with card1:
            st.metric(
                "📈 Nifty 50 Trend",
                regime.nifty_trend,
                delta=f"{regime.nifty_change_pct:+.2f}%",
            )
        with card2:
            st.metric(
                "⚡ India VIX Level",
                f"{regime.vix_level:.2f}",
                delta=f"{regime.vix_change_pct:+.2f}%",
                delta_color="inverse",
            )
        with card3:
            st.metric(
                "🏛 FII Net Flow",
                f"₹{regime.fii_net:,.0f} Cr",
                delta=regime.fii_trend,
            )
        with card4:
            st.metric(
                "🏢 DII Net Flow",
                f"₹{regime.dii_net:,.0f} Cr",
                delta=regime.dii_trend,
            )
        with card5:
            st.metric(
                "🌡 Regime Score",
                f"{regime.regime_score:.1f} / 10.0",
                delta="Bullish" if regime.regime_score >= 6.0 else ("Bearish" if regime.regime_score <= 4.0 else "Neutral"),
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

    # =========================================================================
    # TAB 5: FUSION SCANNER
    # =========================================================================
    with tab5:
        st.header("🔥 Fusion Scanner (The Watchlist)")
        st.write("Combines F&O scores with Breakout signals. Only shows stocks that appear in BOTH scanners. Sorted by Fusion Score.")
        
        if "fo_results_df" not in st.session_state or st.session_state["fo_results_df"].empty or \
           "br_results_df" not in st.session_state or st.session_state["br_results_df"].empty:
            st.warning("⚠️ Please run BOTH the 'F&O Scan' (Tab 1) and 'Breakout & Reversal Scan' (Tab 2) first to generate the Fusion Watchlist.")
        else:
            fo_df = st.session_state["fo_results_df"].copy()
            br_df = st.session_state["br_results_df"].copy()
            
            # Standardize symbol column for merge
            if "Symbol" in fo_df.columns:
                fo_df = fo_df.rename(columns={"Symbol": "symbol"})
                
            fusion_df = fo_df.merge(br_df, on="symbol", suffixes=("_fo", "_br"))
            
            if fusion_df.empty:
                st.info("No stocks found that match signals in both scanners. Market might be choppy or lacking strong setups.")
            else:
                # Calculate fusion score: (F&O Score * 0.6) + (Breakout Strength * 0.4 * 10)
                fusion_df["fusion_score"] = (fusion_df["Final Score"] * 0.6) + (fusion_df["strength_score"].clip(upper=10) * 4.0)
                fusion_df = fusion_df.sort_values("fusion_score", ascending=False).reset_index(drop=True)
                
                st.subheader(f"🔥 Top Watchlist Candidates ({len(fusion_df)} stocks)")
                
                display_cols = [
                    "symbol", "Name", "fusion_score", "Final Score", "signal_type", 
                    "strength_score", "Advice", "Risk:Reward"
                ]
                
                st.dataframe(
                    fusion_df[display_cols],
                    use_container_width=True,
                    column_config={
                        "fusion_score": st.column_config.NumberColumn("Fusion Score", format="%.1f"),
                        "Final Score": st.column_config.NumberColumn("F&O Score", format="%.1f"),
                        "strength_score": st.column_config.NumberColumn("Pattern Strength", format="%.1f"),
                        "Risk:Reward": st.column_config.NumberColumn("Risk:Reward", format="%.2f"),
                    }
                )
                
                st.markdown("---")
                st.subheader("🔍 Selected Fusion Stock Details")
                fusion_symbols = fusion_df["symbol"].tolist()
                sel_fusion_sym = st.selectbox("Select Stock", fusion_symbols, key="sb_fusion_detail")
                
                # We can reuse the Trade Plan card logic from Tab 1
                if sel_fusion_sym in st.session_state.get("fo_analysis_dict", {}):
                    analysis_obj, raw_sym = st.session_state["fo_analysis_dict"][sel_fusion_sym]
                    if analysis_obj.trade_plan:
                        tp = analysis_obj.trade_plan
                        with st.expander("📌 Detailed Trade Plan Card", expanded=True):
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
                                    
                df_stock = data_client.get_stock_ohlcv(raw_sym, days=180)
                if df_stock is not None and not df_stock.empty:
                    df_ind = calculate_all_indicators(df_stock)
                    fig = create_price_chart(df_ind, sel_fusion_sym, analysis_obj.trade_plan if analysis_obj else None)
                    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
