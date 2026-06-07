import streamlit as st
import pandas as pd
import yfinance as yf

# --- 1. 設定頁面 ---
st.set_page_config(page_title="小型股選股雷達", layout="wide")

# --- 2. 函數定義區 ---
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

@st.cache_data
def load_ticker_list():
    df = pd.read_csv('small_cap_list.csv')
    df.columns = df.columns.str.strip() 
    df['Ticker'] = df['Ticker'].astype(str).str.replace('"', '').str.replace('=', '').str.strip()
    df['Code'] = df['Ticker'].str.split('.').str[0]
    is_4_digits = (df['Code'].str.len() == 4) & (df['Code'].str.isdigit())
    is_not_etf = ~df['Code'].str.startswith('00')
    df = df[is_4_digits & is_not_etf]
    return df['Ticker'].tolist()

# --- 3. 全域變數初始化 (關鍵：在 UI 之前執行) ---
all_tickers = load_ticker_list()

# --- 4. UI 顯示區 ---
st.title("小型股選股雷達 📊")
st.markdown("**掃描規則：** * 數據源：**60 分鐘 K 線** * **全場掃描**現已改為離線處理，點擊按鈕即可讀取最新的 `results.csv`。")
st.divider()

tab1, tab2 = st.tabs(["單檔查詢", "全場掃描結果"])

with tab1:
    st.header("單檔即時分析")
    col_a, col_b, col_c = st.columns(3)
    use_kd = col_a.checkbox("KD 勾頭", value=True)
    use_macd = col_b.checkbox("MACD 綠柱縮短", value=True)
    use_ma5 = col_c.checkbox("月K 5MA之上", value=True)
    
    selected = st.selectbox("請選擇股票:", all_tickers)
    
    if st.button("分析單檔"):
        with st.spinner('分析中...'):
            ticker_yf = selected
            data = yf.download(ticker_yf, period="2mo", interval="60m", progress=False)
            sig = get_signal(data)
            cap = get_capital_billion(ticker_yf)
            
            st.write(f"當前股本: {cap:.2f} 億" if cap else "無法取得股本")
            if sig:
                st.write("--- 分析結果 ---")
                c1, c2, c3 = st.columns(3)
                if use_kd: c1.metric("KD 勾頭", "✅" if sig['KD'] else "❌")
                if use_macd: c2.metric("MACD 綠柱縮短", "✅" if sig['MACD'] else "❌")
                if use_ma5: c3.metric("月K 5MA之上", "✅" if check_monthly_ma5(ticker_yf) else "❌")

with tab2:
    st.header("全場掃描結果")
    st.info("請確保 scanner.py 已執行過。")
    if st.button("讀取最新掃描結果"):
        try:
            df_res = pd.read_csv('results.csv')
            st.dataframe(df_res, use_container_width=True)
        except FileNotFoundError:
            st.error("找不到 results.csv，請先執行 scanner.py 進行掃描。")