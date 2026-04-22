import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 1. 페이지 기본 설정 (가장 먼저 와야 함)
st.set_page_config(page_title="미국주식 MDD/MDU 분석기", layout="wide", page_icon="📈")

# 2. 데이터 수집 함수 (캐싱을 적용하여 속도 극대화)
@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        df = yf.Ticker("KRW=X").history(period="1d")
        if not df.empty: return df['Close'].iloc[-1]
    except:
        pass
    return 1400.0

@st.cache_data(ttl=3600)
def fetch_data(ticker, period):
    try:
        df = yf.Ticker(ticker).history(period=period)
        return df if not df.empty else None
    except:
        return None

def calculate_stats(df, is_krw, rate):
    df = df.copy()
    df['Price'] = df['Close'] * (rate if is_krw else 1.0)
    
    # MDD 계산
    df['Peak'] = df['Price'].cummax()
    df['Drawdown'] = (df['Price'] - df['Peak']) / df['Peak']
    mdd_val = df['Drawdown'].min()
    mdd_date = df['Drawdown'].idxmin()
    peak_date = df['Price'][:mdd_date].idxmax()
    
    # MDU 계산
    low_val = df['Price'].min()
    low_date = df['Price'].idxmin()
    current_price = df['Price'].iloc[-1]
    mdu_val = (current_price - low_val) / low_val
    current_drawdown = (current_price - df.loc[peak_date, 'Price']) / df.loc[peak_date, 'Price']
    
    return {
        'current': current_price, 'df': df,
        'ath': df.loc[peak_date, 'Price'], 'ath_date': peak_date,
        'low': low_val, 'low_date': low_date,
        'mdd': mdd_val * 100, 'mdu': mdu_val * 100,
        'current_drawdown': current_drawdown * 100, 'mdd_date': mdd_date
    }

# 3. 화면 UI 구성
st.title("📈 미국주식 MDD/MDU 분석기 (Pro)")

# 컨트롤 패널 (3칸으로 나누기)
col1, col2, col3 = st.columns(3)
with col1:
    ticker_options = {'^IXIC':'나스닥 종합', 'TQQQ':'TQQQ', 'SOXL':'SOXL', 'QQQ':'QQQ', 'SPY':'SPY', 'NVDA':'NVDA', 'TSLA':'TSLA'}
    selected_ticker = st.selectbox("종목 선택", list(ticker_options.keys()), format_func=lambda x: ticker_options[x])
with col2:
    period_options = {'1mo':'1개월', '6mo':'6개월', '1y':'1년', '3y':'3년', '5y':'5년', 'max':'전체(MAX)'}
    selected_period = st.selectbox("기간 선택", list(period_options.keys()), index=2, format_func=lambda x: period_options[x])
with col3:
    st.write("") # 위아래 간격 맞추기
    st.write("")
    is_krw = st.toggle("₩ 원화 보기 (실시간 환율)")

# 4. 데이터 분석 및 차트 출력
rate = get_exchange_rate() if is_krw else 1.0
sym = '₩' if is_krw else '$'

with st.spinner('데이터를 분석 중입니다...'):
    df = fetch_data(selected_ticker, selected_period)

if df is None:
    st.error("데이터를 불러올 수 없습니다. 야후 파이낸스 서버를 확인해주세요.")
else:
    stats = calculate_stats(df, is_krw, rate)
    
    # 상단 4개 주요 수치 (Metrics)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("현재 주가", f"{sym}{stats['current']:,.2f}")
    m2.metric("고점 대비 (Drawdown)", f"{stats['current_drawdown']:.2f}%")
    m3.metric("최대 낙폭 (MDD)", f"{stats['mdd']:.2f}%", delta_color="inverse")
    m4.metric("최대 상승 (MDU)", f"+{stats['mdu']:.2f}%")
    
    # Plotly 차트 그리기
    fig = go.Figure()
    
    # 메인 차트
    fig.add_trace(go.Scatter(x=stats['df'].index, y=stats['df']['Price'], mode='lines', name='주가', line=dict(color='#448aff', width=2), fill='tozeroy', fillcolor='rgba(68, 138, 255, 0.1)'))
    
    # MDD 표시
    fig.add_trace(go.Scatter(x=[stats['ath_date'], stats['mdd_date']], y=[stats['ath'], stats['df'].loc[stats['mdd_date'], 'Price']], mode='markers+lines+text', name='MDD', marker=dict(color='#ff453a', size=10), line=dict(color='#ff453a', width=3, dash='dot'), text=["▲ 전고점", f"▼ MDD: {stats['mdd']:.2f}%"], textposition=["top center", "bottom center"], textfont=dict(color='#ff453a', size=13, weight='bold')))
    
    # MDU 표시
    fig.add_trace(go.Scatter(x=[stats['low_date'], stats['df'].index[-1]], y=[stats['low'], stats['current']], mode='markers+lines+text', name='MDU', marker=dict(color='#32d74b', size=10), line=dict(color='#32d74b', width=3, dash='dot'), text=["▼ 최저점", f"▲ MDU: +{stats['mdu']:.2f}%"], textposition=["bottom right", "top center"], textfont=dict(color='#32d74b', size=13, weight='bold')))
    
    fig.update_layout(template="plotly_dark", hovermode="x unified", height=600, margin=dict(l=10, r=10, t=30, b=10), yaxis=dict(title=f"가격 ({sym})", tickformat=",.0f" if is_krw else ",.2f"))
    
    # 화면에 차트 출력
    st.plotly_chart(fig, use_container_width=True)
