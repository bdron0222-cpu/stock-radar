import pandas as pd
import yfinance as yf
import logging
import concurrent.futures
from threading import Lock
from utils import calculate_indicators, get_signal, check_resistance, get_capital_billion

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

results_lock = Lock()
results = []

def process_ticker(ticker):
    try:
        # 1. 取得股本資訊
        cap = get_capital_billion(ticker)
        if cap is None or cap > 150: return

        # 2. 下載日線資料
        data_day = yf.download(ticker, period="1y", interval="1d", progress=False)
        if isinstance(data_day.columns, pd.MultiIndex):
            data_day.columns = data_day.columns.get_level_values(0)
        if len(data_day) < 120: return

        # 【優化過濾】：確保成交量不會因為空值導致篩選錯誤
        current_volume = data_day['Volume'].iloc[-1]
        
        # 處理可能的 NaN 或 0
        if pd.isna(current_volume): current_volume = 0
        
        # 這是關鍵除錯點，如果不符合量能，我們印出來看
        if current_volume < 500_000: 
            # 如果你想看有哪些股因為量太小被排除，可以取消下一行的註解
            # print(f"排除: {ticker} (成交量僅 {int(current_volume/1000)} 張)")
            return

        # 3. 趨勢與壓力判斷
        price = float(data_day['Close'].iloc[-1])
        ma20 = data_day['Close'].rolling(window=20).mean().iloc[-1]
        ma60 = data_day['Close'].rolling(window=60).mean().iloc[-1]
        if not (ma20 > ma60): return

        resistance_status, resistance_dist = check_resistance(price, data_day)

        # 4. 下載並分析短線訊號
        data_60m = yf.download(ticker, period="2mo", interval="60m", progress=False)
        if isinstance(data_60m.columns, pd.MultiIndex):
            data_60m.columns = data_60m.columns.get_level_values(0)
        sig = get_signal(data_60m)

        # 5. 結果寫入
        if sig and sig['KD'] and sig['MACD']:
            with results_lock:
                results.append({
                    "Ticker": ticker, 
                    "股本(億)": round(cap, 2), 
                    "成交量(張)": int(current_volume / 1000),
                    "KD": "✅", 
                    "MACD": "✅",
                    "壓力狀態": resistance_status,
                    "距壓力%": resistance_dist
                })
            print(f"--> 找到標的: {ticker} | 成交量: {int(current_volume/1000)}張 | 狀態: {resistance_status}")
            
    except Exception:
        pass

def run_scanner():
    try:
        tickers = pd.read_csv('small_cap_list.csv')['Ticker'].tolist()
    except FileNotFoundError:
        print("錯誤：找不到 small_cap_list.csv")
        return

    print(f"啟動並行掃描引擎，共 {len(tickers)} 檔...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        executor.map(process_ticker, tickers)
            
    if results:
        pd.DataFrame(results).to_csv('results.csv', index=False, encoding='utf-8-sig')
        print(f"掃描完成！共找到 {len(results)} 檔，結果存入 results.csv")
    else:
        print("掃描完成，未找到符合標的。")

if __name__ == "__main__":
    run_scanner()