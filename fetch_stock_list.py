import pandas as pd
import requests

def fetch_stock_list():
    print("正在從證交所下載最新股票清單...")
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    
    # 模擬瀏覽器請求
    headers = {'user-agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    
    # 使用 pandas 解析網頁表格
    dfs = pd.read_html(res.text)
    df = dfs[0]
    
    # 設定第一列為標頭
    df.columns = df.iloc[0]
    df = df.iloc[1:]
    
    # 欄位重新命名以方便處理
    df = df.rename(columns={
        "有價證券代號及名稱": "Symbol_Name",
        "市場": "Market"
    })
    
    # 拆分代號與名稱
    df[['Code', 'Name']] = df['Symbol_Name'].str.split(' ', n=1, expand=True)
    
    # --- 【清洗邏輯】 ---
    
    # 1. 篩選市場：只要上市 (TSE) 或上櫃 (OTC)
    # 註：證交所頁面顯示為 '上市' 和 '上櫃'
    df = df[df['Market'].isin(['上市', '上櫃'])].copy()
    
    # 2. 篩選四位數且為純數字代號 (排除權證、ETF 等複雜代號)
    # str.isdigit() 可以排除那些代號超過4碼或帶有符號的標的
    df = df[df['Code'].str.len() == 4]
    df = df[df['Code'].str.isdigit()]
    
    # 3. 剔除 ETF、特別股、存託憑證等非一般股票
    # 透過名稱過濾掉常見非股票標的
    exclude_keywords = ['ETF', '認購', '認售', '特別股', '存託']
    for keyword in exclude_keywords:
        df = df[~df['Name'].str.contains(keyword, na=False)]
    
    # 4. 準備輸出：標記 TW/TWO
    def format_ticker(row):
        return f"{row['Code']}.TW" if row['Market'] == '上市' else f"{row['Code']}.TWO"
        
    df['Ticker'] = df.apply(format_ticker, axis=1)
    
    # 存檔
    output = df[['Ticker', 'Code', 'Name', 'Market']]
    output.to_csv('small_cap_list.csv', index=False, encoding='utf-8-sig')
    print(f"清單更新完成！共抓取 {len(output)} 檔股票。")

if __name__ == "__main__":
    fetch_stock_list()