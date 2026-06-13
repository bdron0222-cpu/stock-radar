import pandas as pd
import requests
import io

def get_tw_tickers(mode):
    """
    mode=2: 上市
    mode=4: 上櫃
    """
    url = f"https://isin.twse.com.tw/isin/C_public.jsp?strMode={mode}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        df = pd.read_html(io.StringIO(response.text))[0]
        df.columns = df.iloc[0]
        df = df.drop(0)
        
        # 提取代號 (只取純數字部分)
        df['代號'] = df['有價證券代號及名稱'].str.extract(r'(\d+)')
        
        # 基礎過濾：4位數代號，且開頭不是 00 (過濾 ETF)
        is_4_digits = (df['代號'].str.len() == 4)
        is_not_etf = ~df['代號'].str.startswith('00')
        stock_df = df[is_4_digits & is_not_etf].copy()
        
        # 補上後綴
        suffix = ".TW" if mode == 2 else ".TWO"
        return (stock_df['代號'] + suffix).tolist()
    except Exception as e:
        print(f"獲取 mode={mode} 失敗: {e}")
        return []

def update_ticker_list():
    print("開始更新股票清單 (上市+上櫃)...")
    
    # 同時獲取上市與上櫃
    list_twse = get_tw_tickers(2)
    list_tpex = get_tw_tickers(4)
    
    all_tickers = sorted(list(set(list_twse + list_tpex)))
    
    if all_tickers:
        pd.DataFrame({'Ticker': all_tickers}).to_csv('small_cap_list.csv', index=False, encoding='utf-8-sig')
        print(f"清單建立完成！")
        print(f"上市: {len(list_twse)} 檔, 上櫃: {len(list_tpex)} 檔")
        print(f"總計: {len(all_tickers)} 檔")
    else:
        print("未抓取到任何資料，請檢查網路環境。")

if __name__ == "__main__":
    update_ticker_list()