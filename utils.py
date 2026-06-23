# utils.py
import pandas as pd
import yfinance as yf

def calculate_indicators(df):
    n = 9
    low_n = df['Low'].rolling(window=n).min()
    high_n = df['High'].rolling(window=n).max()
    rsv = (df['Close'] - low_n) / (high_n - low_n) * 100
    df['K'] = rsv.ewm(com=2, adjust=False).mean()
    df['D'] = df['K'].ewm(com=2, adjust=False).mean()
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['DIF'] = ema12 - ema26
    df['MACD_Signal'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['Hist'] = df['DIF'] - df['MACD_Signal']
    return df

def get_signal(df):
    if df.empty or len(df) < 26: return None
    df = calculate_indicators(df)
    kd_hook = (df['K'].iloc[-1] < df['D'].iloc[-1]) and (df['K'].iloc[-1] > df['K'].iloc[-2])
    macd_shrinking = (df['Hist'].iloc[-1] < 0) and (df['Hist'].iloc[-1] > df['Hist'].iloc[-2])
    return {"KD": kd_hook, "MACD": macd_shrinking}

def check_resistance(price, data_day):
    price = float(price)
    ma_periods = [20, 60, 120]
    mas = {p: float(data_day['Close'].rolling(window=p).mean().iloc[-1]) for p in ma_periods}
    mas_above = {p: val for p, val in mas.items() if val > price}
    if not mas_above: return "無明顯阻力", 0.0
    min_dist = min([(val - price) / price * 100 for val in mas_above.values()])
    if min_dist < 0.5: return "壓力臨近(危險)", round(min_dist, 2)
    elif min_dist < 1.5: return "有壓力空間尚可", round(min_dist, 2)
    else: return "有壓力但空間足夠", round(min_dist, 2)

def get_capital_billion(ticker_yf):
    try:
        stock = yf.Ticker(ticker_yf)
        shares = stock.info.get('sharesOutstanding')
        return (shares * 10) / 100_000_000 if shares else None
    except: return None