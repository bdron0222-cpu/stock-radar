import pandas as pd
import yfinance as yf
import time
import logging

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

# --- 核心計算函數 ---
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

# --- 壓力標記函數 ---
def check_resistance(price, data_day):
    price = float(price)
    ma_periods = [20, 60, 120]
    mas = {p: float(data_day['Close'].rolling(window=p).mean().iloc[-1]) for p in ma_periods}
    
    mas_above = {p: val for p, val in mas.items() if val > price}
    
    if not mas_above:
        return "無明顯阻力", 0.0
    
    min_dist = min([(val - price) / price * 100 for val in mas_above.values()])
    
    if min_dist < 0.5:
        return "壓力臨近(危險)", round(min_dist, 2)
    elif min_dist < 1.5:
        return "有壓力空間尚可", round(min_dist, 2)
    else:
        return "有壓力但空間足夠", round(min_dist, 2)

def get_capital_billion(ticker_yf):
    try:
        stock = yf.Ticker(ticker_yf)
        shares = stock.info.get('sharesOutstanding')
        return (shares * 10) / 100_000_000 if shares else None
    except: return None

def run_scanner():
    try:
        tickers = pd.read_csv('small_cap_list.csv')['Ticker'].tolist()
    except:
        print("請先執行 get_tickers.py 產生清單")
        return

    results = []
    total = len(tickers)
    print(f"開始掃描 {total} 檔股票，請稍候...")

    for i, ticker in enumerate(tickers):
        # 【除錯訊息】：顯示目前進度
        print(f"[{i+1}/{total}] 正在掃描: {ticker} ...")
        
        cap = get_capital_billion(ticker)
        if cap is None or cap > 150: continue 

        data_day = yf.download(ticker, period="1y", interval="1d", progress=False)
        
        # 壓平欄位結構
        if isinstance(data_day.columns, pd.MultiIndex):
            data_day.columns = data_day.columns.get_level_values(0)
            
        if len(data_day) < 120: continue 
        
        price = float(data_day['Close'].iloc[-1])
        ma20 = data_day['Close'].rolling(window=20).mean().iloc[-1]
        ma60 = data_day['Close'].rolling(window=60).mean().iloc[-1]
        is_uptrend = (ma20 > ma60)
        
        resistance_status, resistance_dist = check_resistance(price, data_day)
        
        data_60m = yf.download(ticker, period="2mo", interval="60m", progress=False)
        if isinstance(data_60m.columns, pd.MultiIndex):
            data_60m.columns = data_60m.columns.get_level_values(0)
            
        sig = get_signal(data_60m)
        
        if sig and sig['KD'] and sig['MACD'] and is_uptrend:
            results.append({
                "Ticker": ticker, 
                "股本(億)": round(cap, 2), 
                "KD": "✅", 
                "MACD": "✅",
                "壓力狀態": resistance_status,
                "距壓力%": resistance_dist
            })
            print(f"--> 找到標的: {ticker} | 狀態: {resistance_status}")
        
        # 休息一下，避免被網站封鎖
        time.sleep(0.2)
            
    pd.DataFrame(results).to_csv('results.csv', index=False, encoding='utf-8-sig')
    print("掃描完成，結果已更新。")

if __name__ == "__main__":
    run_scanner()