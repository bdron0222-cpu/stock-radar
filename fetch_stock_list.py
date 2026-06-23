import pandas as pd
import requests
import io

def fetch_stock_list():
    print("正在從證交所下載最新股票清單...")
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    
    headers = {'user-agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    
    dfs = pd.read_html(io.StringIO(res.text))
    df = dfs[0]
    
    # 1. 設定標題
    df.columns = df.iloc[0]
    df = df.iloc[1:]
    
    # 2. 精準重新命名：索引 0 是 Symbol_Name，索引 3 是 Market
    new_columns = {}
    new_columns[df.columns[0]] = 'Symbol_Name'
    new_columns[df.columns[3]] = 'Market'
    df = df.rename(columns=new_columns)
    
    # 3. 安全地拆分代號與名稱 (使用 n=1, expand=True)
    # 先產生分割後的 DataFrame，再合併回去
    split_df = df['Symbol_Name'].str.split(n=1, expand=True)
    df['Code'] = split_df[0]
    df['Name'] = split_df[1]
    
    # --- 清洗邏輯 ---
    
    # 篩選市場 (確保只有 '上市' 或 '上櫃')
    df = df[df['Market'].isin(['上市', '上櫃'])].copy()
    
    # 篩選四位數且為純數字代號
    df = df[df['Code'].str.len() == 4]
    df = df[df['Code'].str.isdigit()]
    
    # 剔除 ETF、特別股等
    exclude_keywords = ['ETF', '認購', '認售', '特別股', '存託']
    for keyword in exclude_keywords:
        df = df[~df['Name'].str.contains(keyword, na=False)]
    
    # 準備輸出
    def format_ticker(row):
        return f"{row['Code']}.TW" if row['Market'] == '上市' else f"{row['Code']}.TWO"
        
    df['Ticker'] = df.apply(format_ticker, axis=1)
    
    output = df[['Ticker', 'Code', 'Name', 'Market']]
    output.to_csv('small_cap_list.csv', index=False, encoding='utf-8-sig')
    print(f"清單更新完成！共抓取 {len(output)} 檔股票。")

if __name__ == "__main__":
    fetch_stock_list()