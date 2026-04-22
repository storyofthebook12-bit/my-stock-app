import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="미국주식 분석기 Pro", layout="wide", page_icon="📈")

# 2. Toss 스타일 UI 및 색상/볼드 커스텀 CSS
def inject_custom_css(is_dark):
    if is_dark:
        bg_color, card_bg, text_p, text_s, border = "#101013", "#1C1C1F", "#F9FAFB", "#8B95A1", "#2C2D31"
        mdd_color, mdu_color = "#F04452", "#31C27C"
    else:
        bg_color, card_bg, text_p, text_s, border = "#F2F4F6", "#FFFFFF", "#333D4B", "#6B7684", "#E5E8EB"
        mdd_color, mdu_color = "#F04452", "#31C27C"

    st.markdown(f"""
    <style>
        .stApp {{ background-color: {bg_color}; color: {text_p}; }}
        [data-testid="stSidebar"] {{ background-color: {card_bg}; border-right: 1px solid {border}; }}
        
        /* 메트릭 카드 스타일링 */
        div[data-testid="metric-container"] {{
            background-color: {card_bg};
            border-radius: 16px;
            padding: 24px 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
            border: 1px solid {border};
        }}
        /* 라벨 텍스트 볼드 */
        div[data-testid="stMetricLabel"] > div {{
            color: {text_s} !important;
            font-weight: 700 !important;
            font-size: 15px !important;
        }}
        /* 수치 텍스트 볼드 */
        div[data-testid="stMetricValue"] > div {{
            color: {text_p} !important;
            font-weight: 800 !important;
            font-size: 30px !important;
        }}
        /* MDD (3번째) 및 MDU (4번째) 색상 강제 지정 */
        div[data-testid="stMetric"]:nth-of-type(3) div[data-testid="stMetricValue"] > div {{
            color: {mdd_color} !important;
        }}
        div[data-testid="stMetric"]:nth-of-type(4) div[data-testid="stMetricValue"] > div {{
            color: {mdu_color} !important;
        }}
        h1, h2, h3, p, label {{ font-family: "Pretendard", sans-serif !important; }}
    </style>
    """, unsafe_allow_html=True)

# 3. 데이터 엔진
@st.cache_data(ttl=3600)
def fetch_data(ticker, start, end):
    try:
        df = yf.download(ticker, start=start, end=end, progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df if not df.empty else None
    except: return None

# 4. 분석 로직 (MDU: 최저점 이후 반등 기준)
def calculate_advanced_stats(df, is_krw, rate):
    df = df.copy()
    df['Price'] = df['Close'] * (rate if is_krw else 1.0)
    
    # MDD (Peak to Trough)
    df['Peak_So_Far'] = df['Price'].cummax()
    df['Drawdown'] = (df['Price'] - df['Peak_So_Far']) / df['Peak_So_Far']
    mdd_val = df['Drawdown'].min()
    mdd_date = df['Drawdown'].idxmin() # 기간 내 최저점 (Trough)
    ath_date = df['Price'].loc[:mdd_date].idxmax() # 최저점 이전의 전고점
    
    # MDU (Trough to Max After Trough)
    after_trough_df = df.loc[mdd_date:]
    max_after_trough = after_trough_df['Price'].max()
    mdu_val = (max_after_trough / df.loc[mdd_date, 'Price']) - 1
    mdu_peak_date = after_trough_df['Price'].idxmax()
    
    current_price = df['Price'].iloc[-1]
    cur_dd = (current_price - df.loc[ath_date, 'Price']) / df.loc[ath_date, 'Price']
    
    return {
        'current': current_price, 'df': df,
        'ath': df.loc[ath_date, 'Price'], 'ath_date': ath_date,
        'trough': df.loc[mdd_date, 'Price'], 'trough_date': mdd_date,
        'mdu_peak': max_after_trough, 'mdu_peak_date': mdu_peak_date,
        'mdd': mdd_val * 100, 'mdu': mdu_val * 100, 'cur_dd': cur_dd * 100
    }

# 5. 메인 레이아웃
with st.sidebar:
    st.title("📈 분석 설정")
    ticker_dict = {'^IXIC':'나스닥 종합', 'TQQQ':'TQQQ', 'SOXL':'SOXL', 'QQQ':'QQQ', 'SPY':'SPY', 'NVDA':'NVDA', 'TSLA':'TSLA'}
    selected_ticker = st.selectbox("종목 선택", list(ticker_dict.keys()), format_func=lambda x: ticker_dict[x])
    
    mode = st.radio("기간 설정", ["프리셋", "직접 입력"])
    if mode == "프리셋":
        p_map = {'1개월': 30, '6개월': 180, '1년': 365, '3년': 1095, '5년': 1825, '전체': 36500}
        selected_p = st.selectbox("기간", list(p_map.keys()), index=2)
        end_d, start_d = datetime.now(), datetime.now() - timedelta(days=p_map[selected_p])
    else:
        start_d, end_d = st.date_input("시작일", datetime.now()-timedelta(days=365)), st.date_input("종료일", datetime.now())
    
    st.divider()
    is_krw = st.toggle("₩ 원화 보기 (실시간 환율)")
    is_dark = st.toggle("🌙 다크 모드", value=True)

inject_custom_css(is_dark)

# 실행 및 표시
st.title(f"📈 {ticker_dict[selected_ticker]} 상세 분석")
rate = yf.download("KRW=X", period="1d", progress=False)['Close'].iloc[-1] if is_krw else 1.0
sym = '₩' if is_krw else '$'

df = fetch_data(selected_ticker, start_d, end_d)
if df is not None:
    s = calculate_advanced_stats(df, is_krw, rate)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("현재주가", f"{sym}{s['current']:,.2f}")
    m2.metric("고점대비 하락", f"{s['cur_dd']:.2f}%")
    m3.metric("최대낙폭", f"{s['mdd']:.2f}%")
    m4.metric("최대반등", f"+{s['mdu']:.2f}%")

    # 차트 시각화
    fig = go.Figure()
    main_color = '#3182F6' # 토스 블루
    fig.add_trace(go.Scatter(x=s['df'].index, y=s['df']['Price'], mode='lines', line=dict(color=main_color, width=2.5), fill='tozeroy', fillcolor='rgba(49, 130, 246, 0.05)', name='주가'))
    
    # MDD 구간 (전고점 -> 최저점)
    fig.add_trace(go.Scatter(x=[s['ath_date'], s['trough_date']], y=[s['ath'], s['trough']], mode='markers+lines', line=dict(color='#F04452', width=2, dash='dot'), marker=dict(size=8), name='MDD'))
    
    # MDU 구간 (최저점 -> 최저점 이후 최고점)
    fig.add_trace(go.Scatter(x=[s['trough_date'], s['mdu_peak_date']], y=[s['trough'], s['mdu_peak']], mode='markers+lines', line=dict(color='#31C27C', width=2, dash='dot'), marker=dict(size=8), name='MDU'))

    chart_theme = "plotly_dark" if is_dark else "plotly_white"
    fig.update_layout(template=chart_theme, hovermode="x unified", height=600, margin=dict(l=10, r=10, t=30, b=10), 
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)' if not is_dark else "#1C1C1F")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("데이터 로드 실패")
