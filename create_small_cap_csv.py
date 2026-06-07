import pandas as pd
import requests
import io

# 1. 確保這個函式存在
def get_all_tw_tickers():
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    df = pd.read_html(io.StringIO(response.text))[0]
    df.columns = df.iloc[0]
    df = df.drop(0)
    df['代號'] = df['有價證券代號及名稱'].str.extract(r'(\d+)')
    stock_df = df[df['代號'].str.len() == 4]
    return (stock_df['代號'] + ".TW").tolist()

# 2. 接著定義篩選函式
def filter_all_stocks():
    all_tickers = get_all_tw_tickers() # 這裡現在就能正確呼叫上面的函式了
    print(f"共找到 {len(all_tickers)} 檔標的，已建立清單...")
    
    df_result = pd.DataFrame({'Ticker': all_tickers})
    df_result.to_csv('small_cap_list.csv', index=False, encoding='utf-8-sig')
    print("清單建立完成！")

# 3. 最後才是主程式執行區
if __name__ == "__main__":
    filter_all_stocks()