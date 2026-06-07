import pandas as pd
import yfinance as yf
import time
import logging
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

# --- 複製原本的核心函數 ---
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

def check_monthly_ma5(ticker_yf):
    try:
        df_monthly = yf.download(ticker_yf, period="12mo", interval="1mo", progress=False)
        if isinstance(df_monthly.columns, pd.MultiIndex): df_monthly.columns = df_monthly.columns.get_level_values(0)
        if len(df_monthly) < 5: return False
        ma5 = df_monthly['Close'].rolling(window=5).mean().iloc[-1]
        current_price = df_monthly['Close'].iloc[-1]
        return bool(current_price > ma5)
    except: return False

def get_capital_billion(ticker_yf):
    try:
        stock = yf.Ticker(ticker_yf)
        shares = stock.info.get('sharesOutstanding')
        return (shares * 10) / 100_000_000 if shares else None
    except: return None

# --- 主掃描邏輯 ---
def run_scanner():
    print("開始掃描，請稍候...")
    tickers = pd.read_csv('small_cap_list.csv')['Ticker'].tolist()
    results = []
    
    for ticker in tickers:
        cap = get_capital_billion(ticker)
        # 這裡設定您的篩選標準
        if cap is None or cap > 150: continue 
        
        data = yf.download(ticker, period="2mo", interval="60m", progress=False)
        if len(data) < 30: continue
        
        sig = get_signal(data)
        if sig and sig['KD'] and sig['MACD']:
            # 這裡您可以選擇是否檢查月線 MA5
            # if check_monthly_ma5(ticker):
            results.append({"Ticker": ticker, "股本(億)": round(cap, 2), "KD": sig['KD'], "MACD": sig['MACD']})
            print(f"找到標的: {ticker}")
            
    pd.DataFrame(results).to_csv('results.csv', index=False, encoding='utf-8-sig')
    print("掃描完成，已產出 results.csv")

if __name__ == "__main__":
    run_scanner()