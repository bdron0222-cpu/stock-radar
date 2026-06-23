import streamlit as st
import pandas as pd
import yfinance as yf
import os
from datetime import datetime

# 從 utils.py 匯入共用函數
from utils import calculate_indicators, get_capital_billion

# --- 設定頁面 ---
st.set_page_config(page_title="小型股選股雷達", layout="wide")

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
                
                df_day, valid_ticker = None, None
                for t in possible:
                    temp_day = yf.download(t, period="1y", interval="1d", progress=False)
                    if not temp_day.empty:
                        if isinstance(temp_day.columns, pd.MultiIndex): temp_day.columns = temp_day.columns.get_level_values(0)
                        df_day = temp_day
                        valid_ticker = t
                        break
                
                if df_day is not None:
                    cap = get_capital_billion(valid_ticker)
                    ma20 = df_day['Close'].rolling(window=20).mean().iloc[-1]
                    ma60 = df_day['Close'].rolling(window=60).mean().iloc[-1]
                    trend_ok = ma20 > ma60
                    
                    df_60m = yf.download(valid_ticker, period="2mo", interval="60m", progress=False)
                    if isinstance(df_60m.columns, pd.MultiIndex): df_60m.columns = df_60m.columns.get_level_values(0)
                    df_60m = calculate_indicators(df_60m)
                    
                    kd_ok = (df_60m['K'].iloc[-1] < df_60m['D'].iloc[-1]) and (df_60m['K'].iloc[-1] > df_60m['K'].iloc[-2])
                    macd_ok = (df_60m['Hist'].iloc[-1] < 0) and (df_60m['Hist'].iloc[-1] > df_60m['Hist'].iloc[-2])
                    
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
    
    # 【新增功能】：顯示檔案更新時間與下載按鈕
    file_path = 'results.csv'
    
    if os.path.exists(file_path):
        # 取得檔案最後修改時間
        mtime = os.path.getmtime(file_path)
        last_updated = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        st.info(f"🕒 數據最後更新時間: {last_updated}")
        
        df = pd.read_csv(file_path)
        st.dataframe(df, use_container_width=True)
        
        # 提供下載按鈕
        st.download_button(
            label="📥 下載完整結果 (CSV)",
            data=df.to_csv(index=False).encode('utf-8-sig'),
            file_name='results.csv',
            mime='text/csv'
        )
    else:
        st.warning("找不到 results.csv，請確認 GitHub Actions 是否已執行完畢。")
    
    if st.button("重新整理資料"):
        st.rerun() # 強制重載頁面