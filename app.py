import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 (가장 먼저 와야 함)
st.set_page_config(page_title="미국주식 분석기 Pro", layout="wide", page_icon="📈")

# 2. 토스(Toss) 스타일 다크/라이트 모드 동적 CSS 주입 함수
def inject_custom_css(is_dark):
    if is_dark:
        bg_color = "#101013"        # 깊은 다크 배경
        card_bg = "#1C1C1F"         # 카드 배경
        text_primary = "#F9FAFB"    # 밝은 텍스트
        text_secondary = "#8B95A1"  # 보조 텍스트
        border_color = "#2C2D31"
    else:
        bg_color = "#F2F4F6"        # 토스 고유의 연한 회색 배경
        card_bg = "#FFFFFF"         # 순백색 카드
        text_primary = "#333D4B"    # 진한 텍스트
        text_secondary = "#6B7684"  # 보조 텍스트
        border_color = "#E5E8EB"

    custom_css = f"""
    <style>
        /* 전체 배경 및 텍스트 색상 */
        .stApp {{
            background-color: {bg_color};
            color: {text_primary};
        }}
        /* 사이드바 디자인 */
        [data-testid="stSidebar"] {{
            background-color: {card_bg};
            border-right: 1px solid {border_color};
        }}
        /* 상단 여백 줄이기 */
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 2rem;
        }}
        /* 토스 스타일 메트릭(수치) 카드 */
        div[data-testid="metric-container"] {{
            background-color: {card_bg};
            border-radius: 16px;
            padding: 24px 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
            border: 1px solid {border_color};
            transition: all 0.3s ease;
        }}
        div[data-testid="metric-container"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
        }}
        /* 메트릭 라벨 텍스트 */
        div[data-testid="metric-container"] > div > div > div > div > p {{
            color: {text_secondary} !important;
            font-size: 14px !important;
            font-weight: 600 !important;
        }}
        /* 메트릭 본문 수치 */
        div[data-testid="metric-container"] > div > div > div > div > span {{
            color: {text_primary} !important;
            font-size: 28px !important;
            font-weight: 800 !important;
            letter-spacing: -0.5px !important;
        }}
        /* 제목 폰트 강제 설정 */
        h1, h2, h3, p, label, span {{
            color: {text_primary} !important;
            font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Pretendard", Roboto, sans-serif !important;
        }}
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

# 3. 데이터 수집 함수
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

# 4. 분석 로직 (MDU = 기간 내 최저점 대비 최고점 비율)
def calculate_stats(df, is_krw, rate):
    df = df.copy()
    df['Price'] = df['Close'] * (rate if is_krw else 1.0)
    
    # MDD 계산
    df['Peak'] = df['Price'].cummax()
    df['Drawdown'] = (df['Price'] - df['Peak']) / df['Peak']
    mdd_val = df['Drawdown'].min()
    mdd_date = df['Drawdown'].idxmin()
    peak_date = df['Price'].loc[:mdd_date].idxmax()
    
    # MDU 계산 (선택한 기간 내 최고가 / 최저가)
    low_price = df['Price'].min()
    low_date = df['Price'].idxmin()
    high_price = df['Price'].max()
    high_date = df['Price'].idxmax()
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

# 5. 사이드바 UI 설정
with st.sidebar:
    st.markdown("### ⚙️ 분석 설정")
    ticker_options = {'^IXIC':'나스닥 종합', 'TQQQ':'TQQQ', 'SOXL':'SOXL', 'QQQ':'QQQ', 'SPY':'SPY', 'NVDA':'NVDA', 'TSLA':'TSLA'}
    selected_ticker = st.selectbox("📌 종목 선택", list(ticker_options.keys()), format_func=lambda x: ticker_options[x])
    
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
    
    # 핵심: 다크모드 선택 토글
    is_dark = st.toggle("🌙 다크 모드 켜기", value=False)

# CSS 주입 실행 (스위치 상태에 따라 동적 변경)
inject_custom_css(is_dark)

# 6. 메인 화면
st.markdown(f"## 📈 {ticker_options[selected_ticker]} 상세 분석")
st.markdown(f"<p style='color: #8B95A1; font-size: 14px;'>분석 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}</p>", unsafe_allow_html=True)

rate = get_exchange_rate() if is_krw else 1.0
sym = '₩' if is_krw else '$'

with st.spinner('데이터를 분석 중입니다...'):
    df = fetch_data(selected_ticker, start_date, end_date)

if df is None:
    st.error("데이터를 불러올 수 없습니다. 날짜 범위를 확인하거나 잠시 후 다시 시도해주세요.")
else:
    stats = calculate_stats(df, is_krw, rate)
    
    # 상단 4개 토스 스타일 카드
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("현재 주가", f"{sym}{stats['current']:,.2f}")
    m2.metric("고점 대비 하락", f"{stats['current_drawdown']:.2f}%")
    m3.metric("최대 낙폭 (MDD)", f"{stats['mdd']:.2f}%")
    m4.metric("최대 반등 (MDU)", f"+{stats['mdu']:.2f}%")

    st.write("") # 간격 띄우기

    # 7. Plotly 차트 구성 (토스 컬러 적용)
    fig = go.Figure()
    
    toss_blue = '#3182F6'
    toss_red = '#F04452'
    toss_green = '#31C27C'
    
    # 주가 메인 라인
    fig.add_trace(go.Scatter(x=stats['df'].index, y=stats['df']['Price'], mode='lines', name='주가', line=dict(color=toss_blue, width=2.5), fill='tozeroy', fillcolor='rgba(49, 130, 246, 0.08)'))
    
    # MDD 라인
    fig.add_trace(go.Scatter(
        x=[stats['ath_date'], stats['mdd_date']], 
        y=[stats['ath'], stats['df'].loc[stats['mdd_date'], 'Price']], 
        mode='markers+lines+text', name='MDD 구간',
        marker=dict(color=toss_red, size=8), line=dict(color=toss_red, width=2, dash='dot'),
        text=["", f"MDD: {stats['mdd']:.2f}%"], textposition="bottom center",
        textfont=dict(color=toss_red, size=14, weight='bold')
    ))
    
    # MDU 라인
    fig.add_trace(go.Scatter(
        x=[stats['low_date'], stats['high_date']], 
        y=[stats['low'], stats['high']], 
        mode='markers+lines+text', name='MDU 구간',
        marker=dict(color=toss_green, size=8), line=dict(color=toss_green, width=2, dash='dot'),
        text=["", f"MDU: +{stats['mdu']:.2f}%"], textposition="top center",
        textfont=dict(color=toss_green, size=14, weight='bold')
    ))

    # 차트 배경도 다크/라이트에 맞춰 부드럽게 변경
    chart_bg = '#1C1C1F' if is_dark else '#FFFFFF'
    grid_color = '#2C2D31' if is_dark else '#F2F4F6'
    font_color = '#F9FAFB' if is_dark else '#333D4B'

    fig.update_layout(
        hovermode="x unified", height=600,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(title=f"가격 ({sym})", tickformat=",.0f" if is_krw else ",.2f", gridcolor=grid_color),
        xaxis=dict(gridcolor=grid_color),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor=chart_bg,
        font=dict(color=font_color)
    )
    
    st.plotly_chart(fig, use_container_width=True)
