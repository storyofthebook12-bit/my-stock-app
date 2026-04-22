import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 1. 페이지 기본 설정 (가장 먼저 와야 함)
st.set_page_config(page_title="미국주식 분석기 Pro", layout="wide", page_icon="📈")

# 2. 데이터 수집 함수 (나스닥 오류 방지 패치 적용)
@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        df = yf.Ticker("KRW=X").history(period="1d")
        if not df.empty: return float(df['Close'].iloc[-1])
    except:
        pass
    return 1400.0

@st.cache_data(ttl=3600)
def fetch_data(ticker, period):
    try:
        # yf.download 방식을 우선 시도 (지수 데이터 누락 방지)
        df = yf.download(ticker, period=period, progress=False)
        
        # yfinance 최신 버전의 MultiIndex 구조 해결
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # 데이터가 비어있으면 기존 history 방식으로 재시도
        if df.empty:
            df = yf.Ticker(ticker).history(period=period)
            
        return df if not df.empty else None
    except:
        return None

def calculate_stats(df, is_krw, rate):
    df = df.copy()
    df['Price'] = df['Close'] * (rate if is_krw else 1.0)
    
    # MDD 계산 (안전한 인덱싱 적용)
    df['Peak'] = df['Price'].cummax()
    df['Drawdown'] = (df['Price'] - df['Peak']) / df['Peak']
    mdd_val = df['Drawdown'].min()
    mdd_date = df['Drawdown'].idxmin()
    peak_date = df['Price'].loc[:mdd_date].idxmax()
    
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

# 3. 유저 친화적 UI: 사이드바(Sidebar) 구성
with st.sidebar:
    st.header("⚙️ 분석 설정")
    ticker_options = {'^IXIC':'나스닥 종합', 'TQQQ':'TQQQ', 'SOXL':'SOXL', 'QQQ':'QQQ', 'SPY':'SPY', 'NVDA':'NVDA', 'TSLA':'TSLA'}
    selected_ticker = st.selectbox("📌 종목 선택", list(ticker_options.keys()), format_func=lambda x: ticker_options[x])
    
    period_options = {'1mo':'1개월', '6mo':'6개월', '1y':'1년', '3y':'3년', '5y':'5년', 'max':'전체(MAX)'}
    selected_period = st.selectbox("📅 기간 선택", list(period_options.keys()), index=2, format_func=lambda x: period_options[x])
    
    st.divider() # 구분선
    is_krw = st.toggle("🪙 ₩ 원화 보기 (실시간 환율)")
    is_dark = st.toggle("🌙 다크 모드 차트", value=True)

# 4. 메인 화면 구성
st.title(f"📈 {ticker_options[selected_ticker]} MDD/MDU 분석")

rate = get_exchange_rate() if is_krw else 1.0
sym = '₩' if is_krw else '$'

with st.spinner('야후 파이낸스에서 데이터를 안전하게 가져오는 중입니다...'):
    df = fetch_data(selected_ticker, selected_period)

if df is None:
    st.error("데이터를 불러올 수 없습니다. 일시적인 야후 파이낸스 서버 오류이거나 종목 코드가 잘못되었습니다. 잠시 후 다시 시도해주세요.")
else:
    stats = calculate_stats(df, is_krw, rate)
    
    # 상단 4개 주요 수치
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("현재 주가", f"{sym}{stats['current']:,.2f}")
    m2.metric("고점 대비 (Drawdown)", f"{stats['current_drawdown']:.2f}%")
    m3.metric("최대 낙폭 (MDD)", f"{stats['mdd']:.2f}%", delta_color="inverse")
    m4.metric("최대 상승 (MDU)", f"+{stats['mdu']:.2f}%")
    
    # Plotly 차트 그리기
    fig = go.Figure()
    
    # 메인 차트 색상 (다크/라이트 연동)
    line_color = '#448aff' if is_dark else '#2962ff'
    fig.add_trace(go.Scatter(x=stats['df'].index, y=stats['df']['Price'], mode='lines', name='주가', line=dict(color=line_color, width=2), fill='tozeroy', fillcolor='rgba(68, 138, 255, 0.1)'))
    
    # MDD 표시 (명칭 삭제 및 깔끔하게 재배치)
    fig.add_trace(go.Scatter(
        x=[stats['ath_date'], stats['mdd_date']], 
        y=[stats['ath'], stats['df'].loc[stats['mdd_date'], 'Price']], 
        mode='markers+lines+text', name='MDD', 
        marker=dict(color='#ff453a', size=8), 
        line=dict(color='#ff453a', width=2, dash='dot'), 
        text=["", f"MDD: {stats['mdd']:.2f}%"], 
        textposition=["top center", "bottom center"], 
        textfont=dict(color='#ff453a', size=14, weight='bold')
    ))
    
    # MDU 표시 (명칭 삭제 및 깔끔하게 재배치)
    fig.add_trace(go.Scatter(
        x=[stats['low_date'], stats['df'].index[-1]], 
        y=[stats['low'], stats['current']], 
        mode='markers+lines+text', name='MDU', 
        marker=dict(color='#32d74b', size=8), 
        line=dict(color='#32d74b', width=2, dash='dot'), 
        text=["", f"MDU: +{stats['mdu']:.2f}%"], 
        textposition=["bottom right", "top center"], 
        textfont=dict(color='#32d74b', size=14, weight='bold')
    ))
    
    # 다크/라이트 테마 자동 적용
    theme = "plotly_dark" if is_dark else "plotly_white"
    bg_color = '#111111' if is_dark else '#ffffff'
    
    fig.update_layout(
        template=theme, hovermode="x unified", height=600, 
        margin=dict(l=10, r=10, t=30, b=10), 
        yaxis=dict(title=f"가격 ({sym})", tickformat=",.0f" if is_krw else ",.2f"),
        paper_bgcolor=bg_color, plot_bgcolor=bg_color
    )
    
    # 화면에 차트 출력
    st.plotly_chart(fig, use_container_width=True)
