#!/usr/bin/env python3
"""
NSE F&O Breakout & Reversal Scanner with Options Chain Analysis
================================================================
Scans NSE F&O stocks for 2-5 day swing trading opportunities using:
- Cash market volume burst detection
- Futures OI confirmation
- Options chain analysis (PCR, OI changes, IV, support/resistance)
- FII/DII participation data
- Market regime filtering

Generates detailed CSV reports and can be used with Streamlit UI.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import warnings
from typing import Dict, List, Optional, Tuple
import os

warnings.filterwarnings('ignore')

# Try to import yfinance for price data
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("Warning: yfinance not installed. Install with: pip install yfinance")

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Configuration parameters for the scanner"""
    
    # Universe
    USE_NSE_FO_ONLY = True
    
    # Cash market filters
    MIN_AVG_VOLUME_20D = 200000
    MIN_VOLUME_RATIO = 2.0
    MIN_RSI = 45.0
    LOOKBACK_DAYS = 60
    
    # Futures filters
    FUTURES_OI_CHANGE_MIN = -1000000  # Allow some OI decrease but not too much
    
    # Options filters
    MIN_PCR = 0.7
    MAX_IV_PERCENTILE = 85.0
    MIN_DISTANCE_TO_RESISTANCE_ATR = 1.0
    NEAR_SPOT_PERCENTAGE = 0.05  # 5% around spot for near-spot calculations
    
    # Scoring weights
    CASH_SCORE_WEIGHT = 40
    FUTURES_SCORE_WEIGHT = 15
    OPTIONS_SCORE_WEIGHT = 35
    REGIME_SCORE_WEIGHT = 10
    
    # Output
    OUTPUT_DIR = "nse_fo_scan_results"
    TOP_N_STOCKS = 20


# ============================================================================
# NSE F&O STOCK UNIVERSE
# ============================================================================

def get_nse_fo_stocks() -> List[str]:
    """
    Returns list of NSE F&O enabled stocks.
    This is a static list - in production, fetch from NSE daily.
    """
    # Major liquid F&O stocks (as of 2024)
    fo_stocks = [
        'RELIANCE', 'HDFCBANK', 'INFY', 'TCS', 'ICICIBANK', 'SBIN', 'BHARTIARTL',
        'ITC', 'KOTAKBANK', 'LT', 'AXISBANK', 'ASIANPAINT', 'MARUTI', 'HCLTECH',
        'BAJFINANCE', 'TITAN', 'SUNPHARMA', 'ULTRACEMCO', 'NESTLEIND', 'BAJAJFINSV',
        'POWERGRID', 'NTPC', 'M&M', 'TATASTEEL', 'JSWSTEEL', 'ADANIENT', 'ADANIPORTS',
        'COALINDIA', 'ONGC', 'BPCL', 'IOC', 'HINDALCO', 'INDUSINDBK', 'GRASIM',
        'HEROMOTOCO', 'EICHERMOT', 'BRITANNIA', 'CIPLA', 'DRREDDY', 'DIVISLAB',
        'APOLLOHOSP', 'PIDILITIND', 'SHRIRAMFIN', 'BAJAJ-AUTO', 'TVSMOTOR',
        'TRENT', 'ZOMATO', 'PAYTM', 'POLICYBZR', 'NYKAA', 'TATAMOTORS',
        'TATAPOWER', 'ADANIGREEN', 'ADANITRANS', 'BEL', 'HAL', 'COCHINSHIP',
        'IREDA', 'RVNL', 'RAILTEL', 'HFCL', 'PFC', 'RECLTD', 'SJVN', 'NHPC',
        'TATAELXSI', 'OFSS', 'PERSISTENT', 'COFORGE', 'MPHASIS', 'LTTS',
        'TORNTPHARM', 'ALKEM', 'AUROPHARMA', 'LUPIN', 'GLENMARK', 'BIOCON',
        'NAM-INDIA', 'ICICIPRULI', 'SBILIFE', 'HDFCLIFE', 'MAXHEALTH',
        'DMART', 'BLUESTARCO', 'VOLTAS', 'AMBUJACEM', 'ACC', 'BERGEPAINT',
        'HAVELLS', 'CROMPTON', 'WHIRLPOOL', 'BOSCHLTD', 'SIEMENS', 'ABB',
        'CUMMINSIND', 'THERMAX', 'KEC', 'KALPATARU', 'PNCINFRA', 'NBCC',
        'IRB', 'IRCTC', 'CONCOR', 'GMRINFRA', 'GVKPIL', 'ADANIENSOL',
        'TATACONSUM', 'COLPAL', 'GODREJCP', 'MARICO', 'RADICO', 'UNITDSPR',
        'ABFRL', 'FASHION', 'RELAXO', 'BATAINDIA', 'METROPOLIS', 'LALPATHLAB',
        'FORTIS', 'MAXIND', 'NAVINFLUOR', 'SRF', 'PIIND', 'ATUL', 'NOVARTIS',
        'GLAND', 'LAURUSLABS', 'SYNGENE', 'DIVISLAB', 'SANOFI', 'PFIZER',
        'GLAXO', 'DIAMONDYD', 'THANGAMAYL', 'RAJESHEXPO', 'PCJEWELLER',
        'MANAPPURAM', 'CHOLAFIN', 'LICHSGFIN', 'PNBHOUSING', 'HDFCAMC',
        'NIPPOAMC', 'CAMS', 'BSE', 'MCX', 'CDSL', 'NSDL', 'CARBORUNIV',
        'ASTRAL', 'SUPREMEIND', 'FINPIPE', 'APLAPOLLO', 'SUDARSCHEM',
        'BALRAMCHIN', 'COROMANDEL', 'GNFC', 'CHAMBALFERT', 'RCF', 'FACT',
        'SPIC', 'KRISHANA', 'RASRESOR', 'SFL', 'GSPL', 'GUJGASLTD',
        'IGL', 'MGL', 'GAIL', 'PETRONET', 'OIL', 'HINDPETRO', 'MRPL',
        'STARCEMENT', 'JKCEMENT', 'HEIDELBERG', 'SAHAPOLY', 'TRIDENT',
        'VTL', 'WELCORP', 'JINDALSAW', 'SAWACA', 'SURYAROSNI', 'GRAPHITE',
        'HGINFRA', 'WEBSOL', 'WAAREE', 'PREMIERPOL', 'CLEANSUB', 'INDIGO',
        'SPICEJET', 'JETAIRWAYS', 'GMRINFRA', 'CESC', 'THERMAX', 'AARTIIND',
        'SRF', 'VINYLINDIA', 'GARFIBRES', 'GPPL', 'KPRMILL', 'VARDHACRLC',
        'TRIDENT', 'WELCORP', 'LUXIND', 'RAYMOND', 'GRASEVA', 'SURYALAXMI',
        'ORIENTELEC', 'HAVELLS', 'CROMPTON', 'KEI', 'POLYCAB', 'FINOLEXCABLE',
        'GTPL', 'HATHWAY', 'DEN', 'ZEEL', 'SUNTV', 'NETWORK18', 'TV18BRDCST',
        'PVRINOX', 'MULTISCREEN', 'BALAJITELE', 'SHYAMTEL', 'RTNPOWER',
        'RPOWER', 'ADANIPOWER', 'TATAPOWER', 'JSWENERGY', 'TORNTPOWER',
        'CESC', 'BSESUR', 'BSEDIL', 'POWERINDIA', 'TRANSFORMER', 'EMAMILTD',
        'DABUR', 'HINDUNILVR', 'ITC', 'GODREJCP', 'MARICO', 'BRITANNIA',
        'NESTLEIND', 'TATACONSUM', 'VARUNI', 'UNITDSPR', 'RADICO', 'UBL',
        'MCDOWELL-N', 'GIPCL', 'SJVN', 'NHPC', 'NTPC', 'POWERGRID', 'RECLTD',
        'PFC', 'IREDA', 'RVNL', 'IRFC', 'IRCON', 'NBCC', 'IRB', 'KNRCON',
        'PNCINFRA', 'HG Infra', 'Ashoka', 'Sadbhav', 'OrientGreen', 'SUZLON',
        'INOXWIND', 'SWELECT', 'INDOSOLAR', 'WEBELSOLAR', 'BORORENEW',
        'GREENPOWER', 'PARASPETRO', 'OILCOUNTUB', 'GPPL', 'GUFICBIO',
        'SEAMECLTD', 'DREDGECORP', 'COCHINSHIP', 'MAZDOCK', 'GSL', 'PSL',
        'SOUTHBIO', 'KERNEX', 'RAILTEL', 'RVNL', 'IRCON', 'IRFC', 'RITES',
        'CONCOR', 'CONTAINER', 'GATI', 'TCI', 'ALLCARGO', 'AEROFLEX',
        'BLUECHIP', 'CMASTERS', 'ESSARSHPNG', 'GESHIP', 'SCI', 'MERLIN',
        'SEAMECLTD', 'DREDGECORP', 'COCHINSHIP', 'MAZDOCK', 'GSL', 'PSL'
    ]
    return fo_stocks


# ============================================================================
# CASH MARKET ANALYSIS
# ============================================================================

def fetch_cash_data(symbol: str, lookback_days: int = 60) -> Optional[pd.DataFrame]:
    """Fetch cash market data for a stock"""
    if not YFINANCE_AVAILABLE:
        return None
    
    try:
        # For NSE stocks, use .NS suffix
        ticker = f"{symbol}.NS"
        stock = yf.Ticker(ticker)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days + 10)
        
        df = stock.history(start=start_date, end=end_date)
        
        if df.empty or len(df) < 20:
            return None
        
        df = df.reset_index()
        df['Symbol'] = symbol
        return df
        
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None


def calculate_cash_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate cash market technical indicators"""
    if df is None or len(df) < 20:
        return None
    
    df = df.copy()
    
    # Moving averages
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['EMA_20'] = df['Close'].ewm(span=20).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Volume indicators
    df['Volume_SMA_20'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA_20']
    
    # Price position
    df['Prev_High'] = df['High'].shift(1)
    df['Prev_Low'] = df['Low'].shift(1)
    df['Prev_Close'] = df['Close'].shift(1)
    df['Prev_Open'] = df['Open'].shift(1)
    
    # Candlestick patterns
    df['Body'] = df['Close'] - df['Open']
    df['Range'] = df['High'] - df['Low']
    df['Body_Ratio'] = abs(df['Body']) / df['Range']
    
    # Bullish engulfing
    df['Bullish_Engulfing'] = (
        (df['Close'] > df['Open']) & 
        (df['Prev_Close'] < df['Prev_Open']) &
        (df['Open'] < df['Prev_Close']) &
        (df['Close'] > df['Prev_Open'])
    )
    
    # Hammer pattern
    lower_shadow = df['Low'] - df[['Open', 'Close']].min(axis=1)
    upper_shadow = df[['Open', 'Close']].max(axis=1) - df['High']
    body = abs(df['Close'] - df['Open'])
    
    df['Hammer'] = (
        (lower_shadow > 2 * body) &
        (upper_shadow < body * 0.5) &
        (df['Close'] > df['Open'])
    )
    
    # ATR
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Prev_Close'])
    low_close = abs(df['Low'] - df['Prev_Close'])
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14).mean()
    
    return df


def detect_cash_signals(df: pd.DataFrame, config: Config) -> Dict:
    """Detect breakout and reversal signals from cash data"""
    if df is None or len(df) < 25:
        return None
    
    latest = df.iloc[-1].copy()
    prev = df.iloc[-2].copy()
    
    symbol = latest['Symbol']
    
    # Check basic filters
    avg_volume = latest['Volume_SMA_20']
    if pd.isna(avg_volume) or avg_volume < config.MIN_AVG_VOLUME_20D:
        return None
    
    volume_ratio = latest['Volume_Ratio']
    if pd.isna(volume_ratio) or volume_ratio < config.MIN_VOLUME_RATIO:
        return None
    
    rsi = latest['RSI']
    if pd.isna(rsi) or rsi < config.MIN_RSI:
        return None
    
    # Calculate scores
    cash_score = 0
    
    # Volume score (max 15)
    if volume_ratio > 3:
        cash_score += 15
    elif volume_ratio > 2.5:
        cash_score += 10
    elif volume_ratio > 2:
        cash_score += 5
    
    # Price action score (max 15)
    if latest['Close'] > latest['Prev_High']:
        cash_score += 10
    if latest['Close'] > latest['SMA_20']:
        cash_score += 5
    
    # RSI momentum (max 5)
    if rsi > 50 and rsi > prev['RSI']:
        cash_score += 5
    
    # Pattern score (max 5)
    if latest['Bullish_Engulfing'] or latest['Hammer']:
        cash_score += 5
    
    # Signal type
    signal_type = "NONE"
    if latest['Close'] > latest['Prev_High'] and volume_ratio > 2:
        signal_type = "BREAKOUT"
    elif (latest['Hammer'] or latest['Bullish_Engulfing']) and rsi < 55:
        signal_type = "REVERSAL"
    
    return {
        'Symbol': symbol,
        'Cash_Close': round(latest['Close'], 2),
        'Change_Pct': round((latest['Close'] - latest['Prev_Close']) / latest['Prev_Close'] * 100, 2),
        'Volume': int(latest['Volume']),
        'Volume_Ratio': round(volume_ratio, 2),
        'RSI': round(rsi, 2),
        'SMA_20': round(latest['SMA_20'], 2) if not pd.isna(latest['SMA_20']) else None,
        'ATR': round(latest['ATR'], 2) if not pd.isna(latest['ATR']) else None,
        'Prev_High': round(latest['Prev_High'], 2),
        'Signal_Type': signal_type,
        'Cash_Score': cash_score,
        'Latest_Date': latest['Date'].strftime('%Y-%m-%d') if hasattr(latest['Date'], 'strftime') else str(latest['Date'])
    }


# ============================================================================
# FUTURES ANALYSIS
# ============================================================================

def fetch_futures_data(symbol: str) -> Optional[Dict]:
    """
    Fetch futures data for a stock.
    In production, this would connect to NSE/broker API.
    For now, returns simulated data based on cash data.
    """
    # Placeholder - in production, fetch from NSE derivative bhavcopy or broker API
    try:
        # Simulate futures data (replace with actual API call)
        ticker = f"{symbol}.NS"
        stock = yf.Ticker(ticker)
        cash_df = stock.history(period='2mo')
        
        if cash_df.empty:
            return None
        
        latest_cash = cash_df.iloc[-1]['Close']
        prev_cash = cash_df.iloc[-2]['Close']
        
        # Simulate futures premium/discount
        premium_pct = np.random.uniform(-0.005, 0.015)  # -0.5% to +1.5%
        futures_price = latest_cash * (1 + premium_pct)
        
        # Simulate OI (in production, get actual OI)
        base_oi = np.random.randint(1000000, 50000000)
        oi_change = np.random.randint(-base_oi//10, base_oi//5)
        
        return {
            'Symbol': symbol,
            'Futures_Close': round(futures_price, 2),
            'Futures_Change_Pct': round((futures_price - prev_cash * (1 + premium_pct * 0.8)) / (prev_cash * (1 + premium_pct * 0.8)) * 100, 2),
            'Futures_OI': int(base_oi),
            'Futures_OI_Change': int(oi_change),
            'Futures_Premium_Pct': round(premium_pct * 100, 3),
            'Futures_Volume': int(cash_df.iloc[-1]['Volume'] * np.random.uniform(0.8, 1.2))
        }
    except:
        return None


def calculate_futures_score(futures_data: Dict, config: Config) -> int:
    """Calculate futures score based on OI and price action"""
    if not futures_data:
        return 0
    
    score = 0
    
    # Futures price up (max 5)
    if futures_data['Futures_Change_Pct'] > 0:
        score += 5
    
    # OI supportive (max 5)
    if futures_data['Futures_OI_Change'] > 0:
        score += 5
    elif futures_data['Futures_OI_Change'] > config.FUTURES_OI_CHANGE_MIN:
        score += 2
    
    # Premium improving (max 5)
    if futures_data['Futures_Premium_Pct'] > 0:
        score += 5
    
    return score


# ============================================================================
# OPTIONS CHAIN ANALYSIS
# ============================================================================

def fetch_option_chain(symbol: str) -> Optional[pd.DataFrame]:
    """
    Fetch option chain for a stock.
    In production, connect to NSE option chain API or broker API.
    For now, returns simulated data.
    """
    try:
        # Get spot price
        ticker = f"{symbol}.NS"
        stock = yf.Ticker(ticker)
        cash_df = stock.history(period='1d')
        
        if cash_df.empty:
            return None
        
        spot = cash_df.iloc[-1]['Close']
        
        # Generate simulated option chain
        # In production, replace with actual NSE/broker API call
        strikes = []
        step = max(5, round(spot * 0.02))  # 2% strike intervals
        min_strike = round(spot * 0.85 / step) * step
        max_strike = round(spot * 1.15 / step) * step
        
        data = []
        for strike in range(int(min_strike), int(max_strike) + 1, int(step)):
            distance = (strike - spot) / spot
            
            # Simulate call OI (higher near ATM, decreases OTM)
            call_oi_base = max(10000, int(500000 * np.exp(-abs(distance) * 3)))
            call_oi = call_oi_base * np.random.uniform(0.7, 1.3)
            call_oi_change = call_oi * np.random.uniform(-0.15, 0.15)
            
            # Simulate put OI
            put_oi_base = max(10000, int(500000 * np.exp(-abs(distance) * 3)))
            put_oi = put_oi_base * np.random.uniform(0.7, 1.3)
            put_oi_change = put_oi * np.random.uniform(-0.15, 0.15)
            
            # Simulate IV (smile pattern)
            atm_iv = np.random.uniform(15, 35)
            iv_adjustment = abs(distance) * 10
            call_iv = atm_iv + iv_adjustment + np.random.uniform(-2, 2)
            put_iv = atm_iv + iv_adjustment + np.random.uniform(-2, 2)
            
            # Simulate volume
            call_volume = call_oi * np.random.uniform(0.1, 0.5)
            put_volume = put_oi * np.random.uniform(0.1, 0.5)
            
            # Simulate LTP using Black-Scholes approximation
            if strike < spot:
                call_ltp = (spot - strike) * 0.9 + np.random.uniform(1, 5)
                put_ltp = np.random.uniform(1, 3)
            else:
                call_ltp = np.random.uniform(1, 5)
                put_ltp = (strike - spot) * 0.9 + np.random.uniform(1, 5)
            
            data.append({
                'Strike': strike,
                'Call_OI': int(call_oi),
                'Call_OI_Change': int(call_oi_change),
                'Call_Volume': int(call_volume),
                'Call_IV': round(call_iv, 2),
                'Call_LTP': round(max(0.05, call_ltp), 2),
                'Put_OI': int(put_oi),
                'Put_OI_Change': int(put_oi_change),
                'Put_Volume': int(put_volume),
                'Put_IV': round(put_iv, 2),
                'Put_LTP': round(max(0.05, put_ltp), 2)
            })
        
        df = pd.DataFrame(data)
        df['Symbol'] = symbol
        df['Spot_Price'] = round(spot, 2)
        
        return df
        
    except Exception as e:
        print(f"Error fetching option chain for {symbol}: {e}")
        return None


def compute_option_features(chain: pd.DataFrame, spot: float, atr: float = None) -> Dict:
    """Compute option chain features and scores"""
    if chain is None or len(chain) == 0:
        return None
    
    chain = chain.copy()
    chain = chain.sort_values('Strike').reset_index(drop=True)
    
    # Find ATM strike
    chain['Distance_To_Spot'] = abs(chain['Strike'] - spot)
    atm_row = chain.loc[chain['Distance_To_Spot'].idxmin()]
    atm_strike = atm_row['Strike']
    
    # Total OI
    total_call_oi = chain['Call_OI'].sum()
    total_put_oi = chain['Put_OI'].sum()
    
    # PCR
    pcr_oi = total_put_oi / total_call_oi if total_call_oi > 0 else np.nan
    
    # Near-spot strikes (within 5% of spot)
    lower_bound = spot * (1 - 0.05)
    upper_bound = spot * (1 + 0.05)
    
    near_chain = chain[(chain['Strike'] >= lower_bound) & (chain['Strike'] <= upper_bound)]
    
    # OI changes near spot
    puts_below = near_chain[near_chain['Strike'] <= spot]
    calls_above = near_chain[near_chain['Strike'] >= spot]
    
    put_oi_change_below = puts_below['Put_OI_Change'].sum() if len(puts_below) > 0 else 0
    call_oi_change_above = calls_above['Call_OI_Change'].sum() if len(calls_above) > 0 else 0
    
    # Support and resistance strikes
    puts_below_spot = chain[chain['Strike'] <= spot]
    calls_above_spot = chain[chain['Strike'] >= spot]
    
    if len(puts_below_spot) > 0:
        put_support_idx = puts_below_spot['Put_OI'].idxmax()
        put_support_strike = puts_below_spot.loc[put_support_idx, 'Strike']
        put_support_oi = puts_below_spot.loc[put_support_idx, 'Put_OI']
    else:
        put_support_strike = np.nan
        put_support_oi = 0
    
    if len(calls_above_spot) > 0:
        call_resistance_idx = calls_above_spot['Call_OI'].idxmax()
        call_resistance_strike = calls_above_spot.loc[call_resistance_idx, 'Strike']
        call_resistance_oi = calls_above_spot.loc[call_resistance_idx, 'Call_OI']
    else:
        call_resistance_strike = np.nan
        call_resistance_oi = 0
    
    # ATM IV
    atm_call_iv = atm_row['Call_IV']
    atm_put_iv = atm_row['Put_IV']
    atm_iv = (atm_call_iv + atm_put_iv) / 2 if pd.notna(atm_call_iv) and pd.notna(atm_put_iv) else np.nan
    
    # Max Pain calculation
    def calculate_max_pain(chain_df):
        strikes = chain_df['Strike'].unique()
        pains = []
        
        for settlement in strikes:
            call_pain = ((chain_df['Strike'].clip(upper=settlement) - settlement).abs() * chain_df['Call_OI']).sum()
            put_pain = ((settlement - chain_df['Strike'].clip(lower=settlement)).abs() * chain_df['Put_OI']).sum()
            pains.append(call_pain + put_pain)
        
        min_idx = np.argmin(pains)
        return strikes[min_idx]
    
    max_pain_strike = calculate_max_pain(chain)
    
    # Distances
    distance_to_support = spot - put_support_strike if pd.notna(put_support_strike) else np.nan
    distance_to_resistance = call_resistance_strike - spot if pd.notna(call_resistance_strike) else np.nan
    
    # Option score calculation
    option_score = 0
    
    # PCR rising (assume previous PCR was slightly lower for simulation)
    if pcr_oi > 0.9:
        option_score += 8
    
    # Put writing below spot
    if put_oi_change_below > 0:
        option_score += 10
    
    # Call unwinding above spot
    if call_oi_change_above < 0:
        option_score += 8
    
    # IV not extreme (simulated percentile)
    if atm_iv and atm_iv < 30:
        option_score += 5
    
    # Support nearby
    if pd.notna(distance_to_support) and distance_to_support < (atr * 2 if atr else spot * 0.05):
        option_score += 4
    
    # Upside room
    if pd.notna(distance_to_resistance) and distance_to_resistance > (atr if atr else spot * 0.02):
        option_score += 4
    
    return {
        'Spot_Price': round(spot, 2),
        'ATM_Strike': atm_strike,
        'Total_Call_OI': int(total_call_oi),
        'Total_Put_OI': int(total_put_oi),
        'PCR_OI': round(pcr_oi, 3) if pd.notna(pcr_oi) else None,
        'Put_OI_Change_Below': int(put_oi_change_below),
        'Call_OI_Change_Above': int(call_oi_change_above),
        'Put_Support_Strike': put_support_strike,
        'Call_Resistance_Strike': call_resistance_strike,
        'Put_Support_OI': int(put_support_oi),
        'Call_Resistance_OI': int(call_resistance_oi),
        'ATM_IV': round(atm_iv, 2) if pd.notna(atm_iv) else None,
        'Max_Pain_Strike': max_pain_strike,
        'Distance_To_Support': round(distance_to_support, 2) if pd.notna(distance_to_support) else None,
        'Distance_To_Resistance': round(distance_to_resistance, 2) if pd.notna(distance_to_resistance) else None,
        'Option_Score': option_score
    }


# ============================================================================
# MARKET REGIME ANALYSIS
# ============================================================================

def get_market_regime() -> Dict:
    """Get overall market regime indicators"""
    try:
        # Fetch Nifty 50 data
        nifty = yf.Ticker("^NSEI")
        nifty_df = nifty.history(period='3mo')
        
        if nifty_df.empty:
            return {'Regime': 'UNKNOWN', 'Regime_Score': 5}
        
        nifty_close = nifty_df.iloc[-1]['Close']
        nifty_sma20 = nifty_df['Close'].rolling(20).mean().iloc[-1]
        
        # India VIX
        vix = yf.Ticker("^INDIAVIX")
        vix_df = vix.history(period='1mo')
        vix_value = vix_df.iloc[-1]['Close'] if not vix_df.empty else 15
        
        # Regime determination
        regime_score = 5  # Neutral
        
        if nifty_close > nifty_sma20:
            regime = 'BULLISH'
            regime_score += 3
        else:
            regime = 'BEARISH'
            regime_score -= 3
        
        if vix_value < 18:
            regime_score += 2
        elif vix_value > 25:
            regime_score -= 2
        
        # Simulate FII/DII data (in production, fetch from NSE)
        fii_net = np.random.uniform(-5000, 5000)  # Crores
        dii_net = -fii_net * 0.7  # Typically opposite
        
        if fii_net > 0:
            regime_score += 2
        else:
            regime_score -= 1
        
        return {
            'Nifty_Close': round(nifty_close, 2),
            'Nifty_SMA20': round(nifty_sma20, 2),
            'India_VIX': round(vix_value, 2),
            'Regime': regime,
            'FII_Net_Cash': int(fii_net),
            'DII_Net_Cash': int(dii_net),
            'Regime_Score': max(0, min(10, regime_score))
        }
        
    except Exception as e:
        print(f"Error getting market regime: {e}")
        return {'Regime': 'UNKNOWN', 'Regime_Score': 5}


# ============================================================================
# MAIN SCANNER
# ============================================================================

class NSEFOScanner:
    """Main scanner class for NSE F&O stocks"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.results = []
        self.market_regime = None
    
    def scan(self, max_stocks: int = None, verbose: bool = True) -> pd.DataFrame:
        """Run the complete scan"""
        
        # Get F&O universe
        fo_stocks = get_nse_fo_stocks()
        if max_stocks:
            fo_stocks = fo_stocks[:max_stocks]
        
        if verbose:
            print(f"Scanning {len(fo_stocks)} NSE F&O stocks...")
        
        # Get market regime
        self.market_regime = get_market_regime()
        if verbose:
            print(f"Market Regime: {self.market_regime['Regime']} (Score: {self.market_regime['Regime_Score']}/10)")
        
        # Scan each stock
        for i, symbol in enumerate(fo_stocks):
            if verbose and (i + 1) % 10 == 0:
                print(f"Processing {i+1}/{len(fo_stocks)}: {symbol}")
            
            try:
                # Fetch cash data
                cash_df = fetch_cash_data(symbol, self.config.LOOKBACK_DAYS)
                if cash_df is None:
                    continue
                
                # Calculate indicators
                cash_df = calculate_cash_indicators(cash_df)
                
                # Detect cash signals
                cash_signal = detect_cash_signals(cash_df, self.config)
                if cash_signal is None:
                    continue
                
                # Fetch futures data
                futures_data = fetch_futures_data(symbol)
                futures_score = calculate_futures_score(futures_data, self.config) if futures_data else 0
                
                # Fetch option chain
                option_chain = fetch_option_chain(symbol)
                atr = cash_signal.get('ATR')
                spot = cash_signal['Cash_Close']
                
                option_features = compute_option_features(option_chain, spot, atr) if option_chain is not None else None
                option_score = option_features['Option_Score'] if option_features else 0
                
                # Calculate final score
                final_score = (
                    cash_signal['Cash_Score'] * self.config.CASH_SCORE_WEIGHT / 40 +
                    futures_score * self.config.FUTURES_SCORE_WEIGHT / 15 +
                    option_score * self.config.OPTIONS_SCORE_WEIGHT / 35 +
                    self.market_regime['Regime_Score'] * self.config.REGIME_SCORE_WEIGHT / 10
                )
                
                # Combine all data
                result = {**cash_signal}
                if futures_data:
                    result.update(futures_data)
                result['Futures_Score'] = futures_score
                if option_features:
                    result.update(option_features)
                result['Option_Score'] = option_score
                result['Regime_Score'] = self.market_regime['Regime_Score']
                result['Final_Score'] = round(final_score, 2)
                
                self.results.append(result)
                
            except Exception as e:
                if verbose:
                    print(f"Error processing {symbol}: {e}")
                continue
        
        # Create DataFrame
        if not self.results:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.results)
        df = df.sort_values('Final_Score', ascending=False)
        
        return df
    
    def save_results(self, df: pd.DataFrame, output_dir: str = None):
        """Save scan results to CSV files"""
        if df.empty:
            print("No results to save")
            return
        
        output_dir = output_dir or self.config.OUTPUT_DIR
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save all results
        all_file = f"{output_dir}/nse_fo_scan_all_{timestamp}.csv"
        df.to_csv(all_file, index=False)
        
        # Save top breakouts
        breakouts = df[df['Signal_Type'] == 'BREAKOUT'].sort_values('Final_Score', ascending=False)
        breakout_file = f"{output_dir}/nse_fo_breakouts_{timestamp}.csv"
        breakouts.head(self.config.TOP_N_STOCKS).to_csv(breakout_file, index=False)
        
        # Save top reversals
        reversals = df[df['Signal_Type'] == 'REVERSAL'].sort_values('Final_Score', ascending=False)
        reversal_file = f"{output_dir}/nse_fo_reversals_{timestamp}.csv"
        reversals.head(self.config.TOP_N_STOCKS).to_csv(reversal_file, index=False)
        
        # Save top overall
        top_file = f"{output_dir}/nse_fo_top_{timestamp}.csv"
        df.head(self.config.TOP_N_STOCKS).to_csv(top_file, index=False)
        
        print(f"\nResults saved:")
        print(f"  All signals: {all_file}")
        print(f"  Breakouts: {breakout_file} ({len(breakouts)} stocks)")
        print(f"  Reversals: {reversal_file} ({len(reversals)} stocks)")
        print(f"  Top {self.config.TOP_N_STOCKS}: {top_file}")


# ============================================================================
# STREAMLIT APP (Optional)
# ============================================================================

def create_streamlit_app():
    """Create Streamlit app code"""
    app_code = '''
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
'''
    
    with open('nse_fo_scanner_app.py', 'w') as f:
        f.write(app_code)
    
    print("Streamlit app created: nse_fo_scanner_app.py")
    print("Run with: streamlit run nse_fo_scanner_app.py")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='NSE F&O Breakout & Reversal Scanner')
    parser.add_argument('--max-stocks', type=int, default=None, help='Maximum number of stocks to scan')
    parser.add_argument('--verbose', action='store_true', default=True, help='Show progress')
    parser.add_argument('--no-save', action='store_true', help='Do not save results to CSV')
    parser.add_argument('--create-app', action='store_true', help='Create Streamlit app')
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
    
    # Run scanner
    scanner = NSEFOScanner()
    results_df = scanner.scan(max_stocks=args.max_stocks, verbose=args.verbose)
    
    if results_df.empty:
        print("\nNo signals found matching criteria")
    else:
        print(f"\n{'='*80}")
        print(f"SCAN COMPLETE")
        print(f"{'='*80}")
        print(f"Total stocks scanned: {len(get_nse_fo_stocks()) if not args.max_stocks else args.max_stocks}")
        print(f"Signals found: {len(results_df)}")
        print(f"Breakouts: {len(results_df[results_df['Signal_Type'] == 'BREAKOUT'])}")
        print(f"Reversals: {len(results_df[results_df['Signal_Type'] == 'REVERSAL'])}")
        print(f"\nTop 5 by Final Score:")
        print(results_df[['Symbol', 'Cash_Close', 'Change_Pct', 'Volume_Ratio', 'Signal_Type', 'Final_Score']].head())
        
        if not args.no_save:
            scanner.save_results(results_df)
    
    # Create Streamlit app if requested
    if args.create_app:
        create_streamlit_app()
