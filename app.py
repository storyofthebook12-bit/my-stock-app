import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 전체 다크모드 CSS 주입
st.set_page_config(page_title="미국주식 분석기 Pro", layout="wide", page_icon="📈")

# 전체 배경 및 텍스트를 다크모드로 강제하는 CSS
st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
        color: #FFFFFF;
    }
    [data-testid="stSidebar"] {
        background-color: #262730;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 수집 함수
@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        df = yf.download("KRW=X", period="1d", progress=False)
        if not df.empty: return float(df['Close'].iloc[-1])
    except: pass
    return 1400.0

@st.cache_data(ttl=3600)
def fetch_data(ticker, start_date, end_date):
    try:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df if not df.empty else None
    except: return None

# 3. 분석 로직 (수정된 MDU 계산 포함)
def calculate_stats(df, is_krw, rate):
    df = df.copy()
    df['Price'] = df['Close'] * (rate if is_krw else 1.0)
    
    # MDD 계산 (최고점 대비 최대 하락)
    df['Peak'] = df['Price'].cummax()
    df['Drawdown'] = (df['Price'] - df['Peak']) / df['Peak']
    mdd_val = df['Drawdown'].min()
    mdd_date = df['Drawdown'].idxmin()
    peak_date = df['Price'].loc[:mdd_date].idxmax()
    
    # MDU 계산 (요청사항: 기간 내 최저점 대비 최고점의 비율)
    low_price = df['Price'].min()
    low_date = df['Price'].idxmin()
    high_price = df['Price'].max()
    high_date = df['Price'].idxmax()
    
    # MDU = (최고가 / 최저가) - 1
    mdu_val = (high_price / low_price) - 1
    
    current_price = df['Price'].iloc[-1]
    current_drawdown = (current_price - df.loc[peak_date, 'Price']) / df.loc[peak_date, 'Price']
    
    return {
        'current': current_price, 'df': df,
        'ath': df.loc[peak_date, 'Price'], 'ath_date': peak_date,
        'low': low_price, 'low_date': low_date,
        'high': high_price, 'high_date': high_date,
        'mdd': mdd_val * 100, 'mdu': mdu_val * 100,
        'current_drawdown': current_drawdown * 100, 'mdd_date': mdd_date
    }

# 4. 사이드바 UI
with st.sidebar:
    st.header("⚙️ 분석 설정")
    ticker_options = {'^IXIC':'나스닥 종합', 'TQQQ':'TQQQ', 'SOXL':'SOXL', 'QQQ':'QQQ', 'SPY':'SPY', 'NVDA':'NVDA', 'TSLA':'TSLA'}
    selected_ticker = st.selectbox("📌 종목 선택", list(ticker_options.keys()), format_func=lambda x: ticker_options[x])
    
    # 기간 선택 모드
    date_mode = st.radio("📅 기간 설정 방식", ["프리셋", "직접 입력"])
    
    if date_mode == "프리셋":
        period_map = {'1개월': 30, '6개월': 180, '1년': 365, '3년': 1095, '5년': 1825, '전체': 36500}
        selected_period = st.selectbox("기간 선택", list(period_map.keys()), index=2)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_map[selected_period])
    else:
        col_s, col_e = st.columns(2)
        start_date = col_s.date_input("시작일", datetime.now() - timedelta(days=365))
        end_date = col_e.date_input("종료일", datetime.now())
    
    st.divider()
    is_krw = st.toggle("🪙 ₩ 원화 보기 (실시간 환율)")

# 5. 메인 화면
st.title(f"📈 {ticker_options[selected_ticker]} 상세 분석")
st.caption(f"분석 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")

rate = get_exchange_rate() if is_krw else 1.0
sym = '₩' if is_krw else '$'

with st.spinner('데이터를 분석 중입니다...'):
    df = fetch_data(selected_ticker, start_date, end_date)

if df is None:
    st.error("데이터를 불러올 수 없습니다. 날짜 범위를 확인하거나 잠시 후 다시 시도해주세요.")
else:
    stats = calculate_stats(df, is_krw, rate)
    
    # 상단 지표
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("현재 주가", f"{sym}{stats['current']:,.2f}")
    m2.metric("고점 대비 하락", f"{stats['current_drawdown']:.2f}%")
    m3.metric("최대 낙폭 (MDD)", f"{stats['mdd']:.2f}%", delta_color="inverse")
    m4.metric("최대 반등 (MDU)", f"+{stats['mdu']:.2f}%")

    # 차트 구성
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=stats['df'].index, y=stats['df']['Price'], mode='lines', name='주가', line=dict(color='#448aff', width=2), fill='tozeroy', fillcolor='rgba(68, 138, 255, 0.1)'))
    
    # MDD 라인 (전고점 -> 최저점)
    fig.add_trace(go.Scatter(
        x=[stats['ath_date'], stats['mdd_date']], 
        y=[stats['ath'], stats['df'].loc[stats['mdd_date'], 'Price']], 
        mode='markers+lines+text', name='MDD 구간',
        marker=dict(color='#ff453a', size=8),
        line=dict(color='#ff453a', width=2, dash='dot'),
        text=["", f"MDD: {stats['mdd']:.2f}%"],
        textposition="bottom center",
        textfont=dict(color='#ff453a', size=14, weight='bold')
    ))
    
    # MDU 라인 (최저점 -> 최고점)
    fig.add_trace(go.Scatter(
        x=[stats['low_date'], stats['high_date']], 
        y=[stats['low'], stats['high']], 
        mode='markers+lines+text', name='MDU 구간',
        marker=dict(color='#32d74b', size=8),
        line=dict(color='#32d74b', width=2, dash='dot'),
        text=["", f"MDU: +{stats['mdu']:.2f}%"],
        textposition="top center",
        textfont=dict(color='#32d74b', size=14, weight='bold')
    ))

    fig.update_layout(
        template="plotly_dark", hovermode="x unified", height=600,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(title=f"가격 ({sym})", tickformat=",.0f" if is_krw else ",.2f"),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, use_container_width=True)
