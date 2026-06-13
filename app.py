import streamlit as st
import pandas as pd
import yfinance as yf

# --- 設定頁面 ---
st.set_page_config(page_title="小型股選股雷達", layout="wide")

# --- 核心邏輯函數 (內建於 app.py 以確保單檔分析獨立運作) ---
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

def get_capital_billion(ticker_yf):
    try:
        stock = yf.Ticker(ticker_yf)
        shares = stock.info.get('sharesOutstanding')
        return (shares * 10) / 100_000_000 if shares else None
    except: return None

# --- UI 介面 ---
st.title("小型股選股雷達 📊")
tab1, tab2 = st.tabs(["單檔即時診斷", "全場掃描結果"])

with tab1:
    st.subheader("單檔即時診斷")
    ticker_input = st.text_input("請輸入股票代號 (例如: 2330):")
    
    if st.button("進行診斷"):
        if ticker_input:
            with st.spinner('計算條件中...'):
                ticker = ticker_input.strip()
                if "." not in ticker: possible = [f"{ticker}.TW", f"{ticker}.TWO"]
                else: possible = [ticker]
                
                df_day, df_60m, valid_ticker = None, None, None
                for t in possible:
                    temp_day = yf.download(t, period="1y", interval="1d", progress=False)
                    if not temp_day.empty:
                        if isinstance(temp_day.columns, pd.MultiIndex): temp_day.columns = temp_day.columns.get_level_values(0)
                        df_day = temp_day
                        valid_ticker = t
                        break
                
                if df_day is not None:
                    # 1. 股本檢查
                    cap = get_capital_billion(valid_ticker)
                    
                    # 2. 趨勢檢查 (MA20 > MA60)
                    ma20 = df_day['Close'].rolling(window=20).mean().iloc[-1]
                    ma60 = df_day['Close'].rolling(window=60).mean().iloc[-1]
                    trend_ok = ma20 > ma60
                    
                    # 3. KD/MACD 檢查
                    df_60m = yf.download(valid_ticker, period="2mo", interval="60m", progress=False)
                    if isinstance(df_60m.columns, pd.MultiIndex): df_60m.columns = df_60m.columns.get_level_values(0)
                    df_60m = calculate_indicators(df_60m)
                    kd_ok = (df_60m['K'].iloc[-1] < df_60m['D'].iloc[-1]) and (df_60m['K'].iloc[-1] > df_60m['K'].iloc[-2])
                    macd_ok = (df_60m['Hist'].iloc[-1] < 0) and (df_60m['Hist'].iloc[-1] > df_60m['Hist'].iloc[-2])
                    
                    # --- 診斷結果呈現 ---
                    st.write(f"### 診斷標的: {valid_ticker}")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("市值 < 150億", "✅ 符合" if cap and cap < 150 else "❌ 超標")
                    col2.metric("趨勢向上 (MA20>MA60)", "✅ 符合" if trend_ok else "❌ 未符合")
                    col3.metric("短線買點 (KD+MACD)", "✅ 符合" if (kd_ok and macd_ok) else "❌ 未符合")
                    
                    st.line_chart(df_day['Close'])
                else:
                    st.error("找不到代號，請檢查。")

with tab2:
    st.subheader("全場掃描結果")
    if st.button("重新讀取掃描結果"):
        df = pd.read_csv('results.csv') if pd.io.common.file_exists('results.csv') else None
        if df is not None: st.dataframe(df, use_container_width=True)
        else: st.warning("請先執行 scanner.py")