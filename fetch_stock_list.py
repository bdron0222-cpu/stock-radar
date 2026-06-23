import pandas as pd
import requests
import io

def fetch_stock_list():
    print("正在從證交所下載最新股票清單...")
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    
    headers = {'user-agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    
    # 使用 io.StringIO 解決警告
    dfs = pd.read_html(io.StringIO(res.text))
    df = dfs[0]
    
    # 這裡將第一列強制設定為標題，並將原始資料保留下來
    df.columns = df.iloc[0]
    df = df.iloc[1:]
    
    # 【除錯用】如果出錯，你可以看到現在的欄位名稱是什麼
    print("目前偵測到的欄位名稱:", df.columns.tolist())
    
    # 【關鍵修正】：不要依賴名稱，直接透過欄位順序來指定
    # 根據證交所表格結構：
    # 索引 1 通常是 "有價證券代號及名稱"
    # 索引 3 通常是 "市場" (上市/上櫃)
    # 我們重新命名它們以符合後續程式邏輯
    df.rename(columns={df.columns[1]: 'Symbol_Name', df.columns[3]: 'Market'}, inplace=True)
    
    # 拆分代號與名稱
    df[['Code', 'Name']] = df['Symbol_Name'].str.split(' ', n=1, expand=True)
    
    # --- 清洗邏輯 ---
    
    # 1. 篩選市場
    df = df[df['Market'].isin(['上市', '上櫃'])].copy()
    
    # 2. 篩選四位數且為純數字代號
    df = df[df['Code'].str.len() == 4]
    df = df[df['Code'].str.isdigit()]
    
    # 3. 剔除 ETF、特別股等
    exclude_keywords = ['ETF', '認購', '認售', '特別股', '存託']
    for keyword in exclude_keywords:
        df = df[~df['Name'].str.contains(keyword, na=False)]
    
    # 4. 準備輸出
    def format_ticker(row):
        return f"{row['Code']}.TW" if row['Market'] == '上市' else f"{row['Code']}.TWO"
        
    df['Ticker'] = df.apply(format_ticker, axis=1)
    
    output = df[['Ticker', 'Code', 'Name', 'Market']]
    output.to_csv('small_cap_list.csv', index=False, encoding='utf-8-sig')
    print(f"清單更新完成！共抓取 {len(output)} 檔股票。")

if __name__ == "__main__":
    fetch_stock_list()