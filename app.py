import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 (가장 먼저 와야 함)
st.set_page_config(page_title="미국주식 분석기 Pro", layout="wide", page_icon="📈")

# 2. 토스(Toss) 스타일 다크/라이트 모드 및 사이드바 가독성 강화 CSS
def inject_custom_css(is_dark):
    if is_dark:
        bg, card, text_p, text_s, border = "#101013", "#1C1C1F", "#FFFFFF", "#8B95A1", "#2C2D31"
    else:
        bg, card, text_p, text_s, border = "#F2F4F6", "#FFFFFF", "#191F28", "#6B7684", "#E5E8EB"

    st.markdown(f"""
    <style>
        /* CSS 변수 설정 */
        :root {{
            --bg-color: {bg};
            --card-bg: {card};
            --text-primary: {text_p};
            --text-secondary: {text_s};
            --border-color: {border};
        }}
        
        /* 전체 배경 및 텍스트 */
        .stApp {{ background-color: var(--bg-color); color: var(--text-primary); }}
        
        /* 사이드바 배경 및 테두리 */
        [data-testid="stSidebar"] {{ 
            background-color: var(--card-bg) !important; 
            border-right: 1px solid var(--border-color); 
        }}
        
        /* 🔥 1. 사이드바 메뉴/글자 가독성 & 볼드(굵게) 처리 🔥 */
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] div[data-baseweb="select"] * {{
            color: var(--text-primary) !important;
            font-weight: 800 !important;
            font-size: 16px !important;
        }}
        
        /* 폰트 일괄 적용 */
        h1, h2, h3, p, label, span {{ font-family: "Pretendard", "Apple SD Gothic Neo", sans-serif !important; }}
    </style>
    """, unsafe_allow_html=True)

# 3. 토스 스타일 수치 카드 커스텀 HTML 생성 함수 (색상 강제 고정용)
def toss_metric_card(title, value, value_color="var(--text-primary)"):
    return f"""
    <div style="background-color: var(--card-bg); border-radius: 16px; padding: 24px 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); border: 1px solid var(--border-color); margin-bottom: 20px;">
        <div style="color: var(--text-secondary); font-size: 15px; font-weight: 800; margin-bottom: 8px;">{title}</div>
        <div style="color: {value_color}; font-size: 32px; font-weight: 900; letter-spacing: -1px;">{value}</div>
    </div>
    """

# 4. 데이터 엔진
@st.cache_data(ttl=3600)
def fetch_data(ticker, start, end):
    try:
        df = yf.download(ticker, start=start, end=end, progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df if not df.empty else None
    except: return None

# 5. 분석 로직 (MDU: 최저점 이후 반등)
def calculate_advanced_stats(df, is_krw, rate):
    df = df.copy()
    df['Price'] = df['Close'] * (rate if is_krw else 1.0)
    
    # MDD (Peak to Trough)
    df['Peak_So_Far'] = df['Price'].cummax()
    df['Drawdown'] = (df['Price'] - df['Peak_So_Far']) / df['Peak_So_Far']
    mdd_val = df['Drawdown'].min()
    mdd_date = df['Drawdown'].idxmin() 
    ath_date = df['Price'].loc[:mdd_date].idxmax() 
    
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

# 6. 사이드바 UI
with st.sidebar:
    st.markdown("## ⚙️ 분석 설정")
    ticker_dict = {'^IXIC':'나스닥 종합', 'TQQQ':'TQQQ', 'SOXL':'SOXL', 'QQQ':'QQQ', 'SPY':'SPY', 'NVDA':'NVDA', 'TSLA':'TSLA'}
    selected_ticker = st.selectbox("📌 종목 선택", list(ticker_dict.keys()), format_func=lambda x: ticker_dict[x])
    
    mode = st.radio("📅 기간 설정 방식", ["프리셋", "직접 입력"])
    if mode == "프리셋":
        p_map = {'1개월': 30, '6개월': 180, '1년': 365, '3년': 1095, '5년': 1825, '전체': 36500}
        selected_p = st.selectbox("⏳ 기간 선택", list(p_map.keys()), index=2)
        end_d, start_d = datetime.now(), datetime.now() - timedelta(days=p_map[selected_p])
    else:
        col_s, col_e = st.columns(2)
        start_d = col_s.date_input("시작일", datetime.now()-timedelta(days=365))
        end_d = col_e.date_input("종료일", datetime.now())
    
    st.divider()
    is_krw = st.toggle("🪙 ₩ 원화 보기 (실시간 환율)")
    is_dark = st.toggle("🌙 다크 모드", value=True)

# 다크모드/라이트모드 CSS 실행
inject_custom_css(is_dark)

# 7. 메인 화면 출력
st.markdown(f"## 📈 {ticker_dict[selected_ticker]} 상세 분석")
st.markdown(f"<p style='color: var(--text-secondary); font-size: 15px; font-weight: 600;'>분석 기간: {start_d.strftime('%Y-%m-%d')} ~ {end_d.strftime('%Y-%m-%d')}</p>", unsafe_allow_html=True)

rate = yf.download("KRW=X", period="1d", progress=False)['Close'].iloc[-1] if is_krw else 1.0
sym = '₩' if is_krw else '$'

df = fetch_data(selected_ticker, start_d, end_d)

if df is not None:
    s = calculate_advanced_stats(df, is_krw, rate)
    
    # 🔥 2. 상단 지표 (MDD 붉은색, MDU 녹색 강제 고정) 🔥
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(toss_metric_card("현재주가", f"{sym}{s['current']:,.2f}"), unsafe_allow_html=True)
    with col2: st.markdown(toss_metric_card("고점대비 하락", f"{s['cur_dd']:.2f}%"), unsafe_allow_html=True)
    with col3: st.markdown(toss_metric_card("최대낙폭 (MDD)", f"{s['mdd']:.2f}%", "#F04452"), unsafe_allow_html=True)
    with col4: st.markdown(toss_metric_card("최대반등 (MDU)", f"+{s['mdu']:.2f}%", "#31C27C"), unsafe_allow_html=True)

    # 8. 차트 시각화
    fig = go.Figure()
    
    # 메인 주가 라인 (토스 블루)
    fig.add_trace(go.Scatter(x=s['df'].index, y=s['df']['Price'], mode='lines', line=dict(color='#3182F6', width=3), fill='tozeroy', fillcolor='rgba(49, 130, 246, 0.08)', name='주가'))
    
    # MDD 라인 (전고점 -> 최저점)
    fig.add_trace(go.Scatter(x=[s['ath_date'], s['trough_date']], y=[s['ath'], s['trough']], mode='markers+lines', line=dict(color='#F04452', width=2.5, dash='dot'), marker=dict(size=10, color='#F04452'), name='MDD 구간'))
    
    # MDU 라인 (최저점 -> 최저점 이후 최고점)
    fig.add_trace(go.Scatter(x=[s['trough_date'], s['mdu_peak_date']], y=[s['trough'], s['mdu_peak']], mode='markers+lines', line=dict(color='#31C27C', width=2.5, dash='dot'), marker=dict(size=10, color='#31C27C'), name='MDU 구간'))

    # 🔥 3. 차트 내 수치 표기 복구 및 색상 강화 🔥
    fig.add_annotation(
        x=s['trough_date'], y=s['trough'],
        text=f"MDD: {s['mdd']:.2f}%",
        showarrow=True, arrowhead=2, arrowsize=1.5, arrowwidth=2, arrowcolor='#F04452',
        font=dict(color='#F04452', size=16, family="Pretendard, bold"),
        bgcolor="rgba(255, 255, 255, 0.8)" if not is_dark else "rgba(0, 0, 0, 0.6)",
        ax=0, ay=50
    )
    
    fig.add_annotation(
        x=s['mdu_peak_date'], y=s['mdu_peak'],
        text=f"MDU: +{s['mdu']:.2f}%",
        showarrow=True, arrowhead=2, arrowsize=1.5, arrowwidth=2, arrowcolor='#31C27C',
        font=dict(color='#31C27C', size=16, family="Pretendard, bold"),
        bgcolor="rgba(255, 255, 255, 0.8)" if not is_dark else "rgba(0, 0, 0, 0.6)",
        ax=0, ay=-50
    )

    # 차트 배경 및 레이아웃 디테일 설정
    chart_bg = '#1C1C1F' if is_dark else '#FFFFFF'
    grid_color = '#2C2D31' if is_dark else '#F2F4F6'
    
    fig.update_layout(
        template="plotly_dark" if is_dark else "plotly_white", 
        hovermode="x unified", height=600, margin=dict(l=10, r=10, t=30, b=10), 
        yaxis=dict(title=f"가격 ({sym})", tickformat=",.0f" if is_krw else ",.2f", gridcolor=grid_color),
        xaxis=dict(gridcolor=grid_color),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor=chart_bg,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("데이터 로드 실패: 야후 파이낸스 서버 상태를 확인해주세요.")
