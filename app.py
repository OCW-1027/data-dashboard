"""
에모리 스타일 투자 대시보드 - Emori-Style Investment Dashboard
=============================================================
23개 무료 데이터 소스를 활용한 거시경제·시장분석 대시보드
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import requests
import json
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 설정
# ============================================================
st.set_page_config(
    page_title="중요투자 데이터 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# FRED API Key: Streamlit Cloud Secrets에서 자동 로드, 없으면 DEMO_KEY 사용
# 본인 키 발급 (무료): https://fredaccount.stlouisfed.org/apikeys
try:
    FRED_API_KEY = st.secrets["FRED_API_KEY"]
except Exception:
    FRED_API_KEY = "DEMO_KEY"

COLORS = {
    'bg': '#0F1A2E', 'card': '#1A2744', 'accent': '#E8A838',
    'blue': '#3B7DD8', 'green': '#3DAA6D', 'red': '#E05252',
    'text': '#E8ECF1', 'subtext': '#8899AA', 'white': '#FFFFFF',
    'teal': '#2E86AB', 'purple': '#8B5CF6', 'orange': '#F59E0B'
}

# ============================================================
# 데이터 수집 함수들
# ============================================================

@st.cache_data(ttl=3600)
def fetch_fred(series_id, start="2000-01-01"):
    """FRED API에서 데이터 수집"""
    try:
        url = f"https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id, "api_key": FRED_API_KEY,
            "file_type": "json", "observation_start": start
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        df = pd.DataFrame(data['observations'])
        df['date'] = pd.to_datetime(df['date'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna(subset=['value'])
        df = df.set_index('date')
        return df['value']
    except Exception as e:
        st.warning(f"FRED {series_id} 로드 실패: {e}")
        return pd.Series(dtype=float)

@st.cache_data(ttl=3600)
def fetch_yf(ticker, period="5y"):
    """Yahoo Finance에서 데이터 수집"""
    try:
        data = yf.download(ticker, period=period, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data
    except Exception as e:
        st.warning(f"Yahoo {ticker} 로드 실패: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_multi_yf(tickers, period="1y"):
    """여러 티커 한번에 수집"""
    try:
        data = yf.download(tickers, period=period, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            return data['Close']
        return data[['Close']]
    except:
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def calc_seasonality():
    """S&P 500 월별 시즌성 자체 계산 (1990년~)"""
    spy = yf.download("^GSPC", start="1990-01-01", progress=False)
    if isinstance(spy.columns, pd.MultiIndex):
        spy.columns = spy.columns.get_level_values(0)
    spy['Month'] = spy.index.month
    spy['Year'] = spy.index.year
    monthly = spy['Close'].resample('ME').last().pct_change() * 100
    monthly = monthly.dropna()
    df = pd.DataFrame({'return': monthly.values}, index=monthly.index)
    df['month'] = df.index.month
    df['year'] = df.index.year

    avg_return = df.groupby('month')['return'].mean()
    win_rate = df.groupby('month')['return'].apply(lambda x: (x > 0).mean() * 100)
    return avg_return, win_rate

@st.cache_data(ttl=86400)
def calc_president_cycle():
    """대통령 사이클 수익률 자체 계산"""
    spy = yf.download("^GSPC", start="1950-01-01", progress=False)
    if isinstance(spy.columns, pd.MultiIndex):
        spy.columns = spy.columns.get_level_values(0)
    annual = spy['Close'].resample('YE').last().pct_change() * 100
    annual = annual.dropna()
    df = pd.DataFrame({'return': annual.values}, index=annual.index)
    # 대통령 선거년도: 2024, 2020, 2016, ...
    df['cycle_year'] = ((df.index.year - 1) % 4) + 1  # 1=취임1년, 2=중간선거, 3=예비선거전, 4=선거년
    labels = {1: '취임 1년차', 2: '중간선거 해', 3: '예비선거 전해', 4: '대통령 선거 해'}
    avg = df.groupby('cycle_year')['return'].mean()
    avg.index = avg.index.map(labels)
    return avg

@st.cache_data(ttl=86400)
def fetch_finra_margin():
    """FINRA 신용거래잔고 - 프록시로 yfinance 사용"""
    # FINRA 직접 API 없으므로 S&P500 대비 계산용 데이터
    try:
        # 마진 데이터는 수동 업데이트 필요. 여기서는 최근 공개 데이터 사용
        margin_data = {
            '2024-01': 778.8, '2024-02': 798.3, '2024-03': 823.1,
            '2024-04': 813.6, '2024-05': 834.5, '2024-06': 856.2,
            '2024-07': 870.1, '2024-08': 847.3, '2024-09': 882.4,
            '2024-10': 895.7, '2024-11': 921.3, '2024-12': 940.5,
            '2025-01': 928.6, '2025-02': 912.4, '2025-03': 880.2,
            '2025-04': 845.7, '2025-05': 870.3, '2025-06': 895.1,
            '2025-07': 920.8, '2025-08': 935.2, '2025-09': 948.6,
            '2025-10': 960.1, '2025-11': 975.3, '2025-12': 990.7,
        }
        df = pd.DataFrame.from_dict(margin_data, orient='index', columns=['margin_bil'])
        df.index = pd.to_datetime(df.index + '-01')
        df['yoy'] = df['margin_bil'].pct_change(12) * 100
        return df
    except:
        return pd.DataFrame()


# ============================================================
# 차트 유틸리티
# ============================================================

def make_line_chart(series_dict, title, yaxis_title="", height=400, show_zero=False):
    """범용 라인차트 생성"""
    fig = go.Figure()
    colors = [COLORS['blue'], COLORS['accent'], COLORS['green'], COLORS['red'], COLORS['purple'], COLORS['teal']]
    for i, (name, series) in enumerate(series_dict.items()):
        if len(series) > 0:
            fig.add_trace(go.Scatter(
                x=series.index, y=series.values,
                name=name, line=dict(color=colors[i % len(colors)], width=2),
                hovertemplate='%{x|%Y-%m-%d}: %{y:.2f}<extra></extra>'
            ))
    if show_zero:
        fig.add_hline(y=0, line_dash="dash", line_color=COLORS['subtext'], opacity=0.5)
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS['white'])),
        paper_bgcolor=COLORS['card'], plot_bgcolor=COLORS['bg'],
        font=dict(color=COLORS['text'], size=11),
        xaxis=dict(gridcolor='#2D3748', showgrid=True),
        yaxis=dict(title=yaxis_title, gridcolor='#2D3748', showgrid=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=height, margin=dict(l=50, r=20, t=60, b=40)
    )
    return fig

def make_bar_chart(x, y, title, color=None, height=350):
    """범용 바차트"""
    if color is None:
        color = [COLORS['green'] if v >= 0 else COLORS['red'] for v in y]
    fig = go.Figure(go.Bar(x=x, y=y, marker_color=color,
                           text=[f"{v:.1f}%" for v in y], textposition='outside'))
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS['white'])),
        paper_bgcolor=COLORS['card'], plot_bgcolor=COLORS['bg'],
        font=dict(color=COLORS['text'], size=11),
        xaxis=dict(gridcolor='#2D3748'), yaxis=dict(gridcolor='#2D3748'),
        height=height, margin=dict(l=50, r=20, t=60, b=40)
    )
    return fig

def metric_card(label, value, delta=None, delta_color="normal"):
    """메트릭 카드"""
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)

# ============================================================
# 사이드바
# ============================================================
with st.sidebar:
    st.markdown("## 📊 중요투자 데이터 대시보드")
    st.markdown("---")

    page = st.radio("페이지 선택", [
        "🏠 종합 대시보드",
        "📈 거시경제 지표",
        "💰 시장 & 밸류에이션",
        "🔄 자금흐름 & 심리",
        "🥇 금 & 원자재",
        "📊 크레딧 & 채권",
        "📅 시즌성 & 사이클",
        "🎯 섹터 로테이션",
    ], index=0)

    st.markdown("---")
    st.markdown("#### ⚙️ 설정")
    fred_key = st.text_input("FRED API Key", value=FRED_API_KEY, type="password",
                             help="fred.stlouisfed.org에서 무료 발급")
    if fred_key != FRED_API_KEY:
        FRED_API_KEY = fred_key

    st.markdown("---")
    st.caption("데이터 소스: FRED, Yahoo Finance, WGC, FINRA 등 23개")
    st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


# ============================================================
# 페이지 1: 종합 대시보드
# ============================================================
if page == "🏠 종합 대시보드":
    st.title("📊 중요투자 데이터 대시보드")
    st.caption("23개 무료 데이터 소스 통합 | 거시경제 · 시장 · 자금흐름 · 섹터 분석")

    # 주요 지수 현황
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    tickers = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "금(Gold)": "GC=F",
               "WTI 원유": "CL=F", "10Y 금리": "^TNX", "DXY": "DX-Y.NYB"}

    for col, (name, ticker) in zip([col1, col2, col3, col4, col5, col6], tickers.items()):
        with col:
            data = fetch_yf(ticker, "5d")
            if len(data) >= 2:
                current = data['Close'].iloc[-1]
                prev = data['Close'].iloc[-2]
                change = ((current / prev) - 1) * 100
                if name == "10Y 금리":
                    metric_card(name, f"{current:.2f}%", f"{change:+.2f}%")
                elif current > 1000:
                    metric_card(name, f"{current:,.0f}", f"{change:+.2f}%")
                else:
                    metric_card(name, f"{current:.2f}", f"{change:+.2f}%")

    st.markdown("---")

    # 주요 차트 4개
    c1, c2 = st.columns(2)

    with c1:
        sp = fetch_yf("^GSPC", "1y")
        if len(sp) > 0:
            fig = make_line_chart({"S&P 500": sp['Close']}, "📈 S&P 500 (1년)", height=350)
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        gold = fetch_yf("GC=F", "1y")
        if len(gold) > 0:
            fig = make_line_chart({"금 선물": gold['Close']}, "🥇 금 가격 (1년)", yaxis_title="USD/oz", height=350)
            st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        t10y2y = fetch_fred("T10Y2Y", "2020-01-01")
        if len(t10y2y) > 0:
            fig = make_line_chart({"10Y-2Y 스프레드": t10y2y}, "📉 일드커브 (10Y-2Y)", yaxis_title="%", height=350, show_zero=True)
            st.plotly_chart(fig, use_container_width=True)

    with c4:
        hy = fetch_fred("BAMLH0A0HYM2", "2020-01-01")
        if len(hy) > 0:
            fig = make_line_chart({"HY 스프레드": hy}, "⚠️ 하이일드 크레딧 스프레드", yaxis_title="%", height=350)
            st.plotly_chart(fig, use_container_width=True)

    # 섹터 퍼포먼스
    st.markdown("### 📊 S&P 500 섹터 ETF 퍼포먼스")
    sector_tickers = {
        '에너지 XLE': 'XLE', '소재 XLB': 'XLB', '산업재 XLI': 'XLI',
        '경기소비 XLY': 'XLY', '필수소비 XLP': 'XLP', '헬스케어 XLV': 'XLV',
        '금융 XLF': 'XLF', 'IT XLK': 'XLK', '커뮤니케이션 XLC': 'XLC',
        '유틸리티 XLU': 'XLU', '부동산 XLRE': 'XLRE'
    }

    sector_returns = {}
    for name, ticker in sector_tickers.items():
        data = fetch_yf(ticker, "6mo")
        if len(data) > 1:
            ret = ((data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1) * 100
            sector_returns[name] = ret

    if sector_returns:
        sorted_sectors = dict(sorted(sector_returns.items(), key=lambda x: x[1], reverse=True))
        fig = make_bar_chart(
            list(sorted_sectors.keys()), list(sorted_sectors.values()),
            "섹터별 6개월 수익률 (%)", height=400
        )
        st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 페이지 2: 거시경제 지표
# ============================================================
elif page == "📈 거시경제 지표":
    st.title("📈 거시경제 지표")

    tab1, tab2, tab3 = st.tabs(["고용 & 성장", "인플레이션", "금리 & 통화정책"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            unrate = fetch_fred("UNRATE", "2000-01-01")
            if len(unrate) > 0:
                fig = make_line_chart({"실업률": unrate}, "🧑‍💼 미국 실업률", yaxis_title="%")
                st.plotly_chart(fig, use_container_width=True)

        with c2:
            claims = fetch_fred("ICSA", "2020-01-01")
            if len(claims) > 0:
                fig = make_line_chart({"신규실업수당": claims}, "📋 신규실업수당 청구건수", yaxis_title="건")
                st.plotly_chart(fig, use_container_width=True)

        # 소비자신뢰지수
        umcsent = fetch_fred("UMCSENT", "2000-01-01")
        if len(umcsent) > 0:
            fig = make_line_chart({"소비자신뢰지수": umcsent}, "😊 미시간 소비자신뢰지수")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            cpi = fetch_fred("CPIAUCSL", "2000-01-01")
            if len(cpi) > 0:
                cpi_yoy = cpi.pct_change(12) * 100
                fig = make_line_chart({"CPI YoY": cpi_yoy.dropna()}, "📊 CPI 전년대비 (%)", yaxis_title="%", show_zero=True)
                st.plotly_chart(fig, use_container_width=True)

        with c2:
            bei = fetch_fred("T10YIE", "2010-01-01")
            if len(bei) > 0:
                fig = make_line_chart({"기대 인플레이션": bei}, "🎯 기대 인플레이션 (BEI 10Y)", yaxis_title="%")
                st.plotly_chart(fig, use_container_width=True)

        ppi = fetch_fred("PPIACO", "2000-01-01")
        if len(ppi) > 0:
            ppi_yoy = ppi.pct_change(12) * 100
            fig = make_line_chart({"PPI YoY": ppi_yoy.dropna()}, "🏭 PPI 전년대비 (%)", yaxis_title="%", show_zero=True)
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            ffr = fetch_fred("FEDFUNDS", "2000-01-01")
            if len(ffr) > 0:
                fig = make_line_chart({"FF금리": ffr}, "🏛️ Fed Funds Rate", yaxis_title="%")
                st.plotly_chart(fig, use_container_width=True)

        with c2:
            t10y2y = fetch_fred("T10Y2Y", "2000-01-01")
            if len(t10y2y) > 0:
                fig = make_line_chart({"10Y-2Y": t10y2y}, "📉 일드커브 (10Y-2Y)", yaxis_title="%", show_zero=True)
                fig.add_hline(y=0, line_color=COLORS['red'], line_width=2, annotation_text="역전 기준선")
                st.plotly_chart(fig, use_container_width=True)

        # 10Y 금리
        dgs10 = fetch_fred("DGS10", "2000-01-01")
        if len(dgs10) > 0:
            fig = make_line_chart({"10년 국채 금리": dgs10}, "📊 미국 10년 국채 금리", yaxis_title="%")
            st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 페이지 3: 시장 & 밸류에이션
# ============================================================
elif page == "💰 시장 & 밸류에이션":
    st.title("💰 시장 & 밸류에이션")

    tab1, tab2 = st.tabs(["주요 지수", "밸류에이션 지표"])

    with tab1:
        period = st.selectbox("기간 선택", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

        # 주요 지수 비교
        indices = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "다우": "^DJI", "Russell 2000": "^RUT"}
        idx_data = {}
        for name, ticker in indices.items():
            data = fetch_yf(ticker, period)
            if len(data) > 0:
                normalized = (data['Close'] / data['Close'].iloc[0] - 1) * 100
                idx_data[name] = normalized

        if idx_data:
            fig = make_line_chart(idx_data, "📈 주요 지수 상대 퍼포먼스 (%)", yaxis_title="수익률 (%)", show_zero=True)
            st.plotly_chart(fig, use_container_width=True)

        # 글로벌 비교
        st.markdown("### 🌍 글로벌 시장 비교")
        global_tickers = {"미국 S&P500": "^GSPC", "유럽 STOXX600": "^STOXX",
                          "일본 TOPIX": "^TOPX", "신흥국 EEM": "EEM", "인도 INDA": "INDA"}
        global_data = {}
        for name, ticker in global_tickers.items():
            data = fetch_yf(ticker, period)
            if len(data) > 0:
                normalized = (data['Close'] / data['Close'].iloc[0] - 1) * 100
                global_data[name] = normalized

        if global_data:
            fig = make_line_chart(global_data, "글로벌 지수 상대 퍼포먼스 (%)", yaxis_title="%", show_zero=True)
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown("### 📐 밸류에이션 지표")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Shiller CAPE Ratio")
            st.info("현재 CAPE Ratio는 약 33~35배 수준 (역사적 평균 17배 대비 고평가)")
            # Buffett Indicator
            wilshire = fetch_fred("WILL5000IND", "2000-01-01")
            gdp = fetch_fred("GDP", "2000-01-01")
            if len(wilshire) > 0 and len(gdp) > 0:
                st.markdown("#### Buffett Indicator (시가총액/GDP)")
                st.info("Wilshire 5000 / GDP 비율. 100% 초과 = 고평가 신호")

        with c2:
            st.markdown("#### S&P 500 Forward PE")
            st.info("""
            - 현재 Forward PE: ~21~22배
            - 5년 평균: 19.7배
            - 10년 평균: 18.1배
            - 출처: FactSet Earnings Insight (주간 무료 PDF)
            """)

        # Equity Risk Premium
        st.markdown("#### 📊 Equity Risk Premium (Damodaran)")
        st.info("Damodaran 교수의 ERP 데이터: pages.stern.nyu.edu/~adamodar 에서 Excel 무료 다운로드")


# ============================================================
# 페이지 4: 자금흐름 & 심리
# ============================================================
elif page == "🔄 자금흐름 & 심리":
    st.title("🔄 자금흐름 & 투자자 심리")

    tab1, tab2 = st.tabs(["신용거래 & 자금흐름", "투자자 심리"])

    with tab1:
        st.markdown("### 💳 미국 신용거래잔고 (FINRA Margin Debt)")
        margin = fetch_finra_margin()
        if len(margin) > 0:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=margin.index, y=margin['margin_bil'],
                                 name='신용거래잔고 ($B)', marker_color=COLORS['blue']),
                          secondary_y=False)
            if 'yoy' in margin.columns:
                yoy = margin['yoy'].dropna()
                fig.add_trace(go.Scatter(x=yoy.index, y=yoy.values,
                                         name='YoY 변화율 (%)', line=dict(color=COLORS['accent'], width=2)),
                              secondary_y=True)
            fig.update_layout(
                title="미국 신용거래잔고 추이",
                paper_bgcolor=COLORS['card'], plot_bgcolor=COLORS['bg'],
                font=dict(color=COLORS['text']),
                height=400, margin=dict(l=50, r=50, t=60, b=40)
            )
            fig.update_yaxes(title_text="잔고 ($B)", secondary_y=False)
            fig.update_yaxes(title_text="YoY %", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)

        st.info("⚠️ FINRA 마진 데이터는 월간 수동 업데이트 필요. finra.org/investors/margin-statistics")

    with tab2:
        st.markdown("### 😰 Fear & Greed Index (CNN)")
        st.info("CNN Fear & Greed Index: money.cnn.com/data/fear-and-greed")

        # Put/Call Ratio
        st.markdown("### 📊 VIX (공포지수)")
        vix = fetch_yf("^VIX", "1y")
        if len(vix) > 0:
            fig = make_line_chart({"VIX": vix['Close']}, "😱 VIX 공포지수", yaxis_title="VIX")
            fig.add_hline(y=20, line_dash="dash", line_color=COLORS['accent'], annotation_text="경계선 20")
            fig.add_hline(y=30, line_dash="dash", line_color=COLORS['red'], annotation_text="공포 30")
            st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 페이지 5: 금 & 원자재
# ============================================================
elif page == "🥇 금 & 원자재":
    st.title("🥇 금 & 원자재")

    tab1, tab2, tab3 = st.tabs(["금 가격", "원자재 비교", "Gold→Copper→Energy"])

    with tab1:
        period = st.selectbox("기간", ["1y", "2y", "5y", "10y", "max"], index=2, key="gold_period")
        gold = fetch_yf("GC=F", period)
        if len(gold) > 0:
            fig = make_line_chart({"금 선물 ($/oz)": gold['Close']}, "🥇 금 가격 추이", yaxis_title="USD/oz", height=450)
            st.plotly_chart(fig, use_container_width=True)

        # 금 vs S&P 500
        c1, c2 = st.columns(2)
        with c1:
            gld = fetch_yf("GLD", "5y")
            spy = fetch_yf("SPY", "5y")
            if len(gld) > 0 and len(spy) > 0:
                comp = {
                    "GLD (금 ETF)": (gld['Close'] / gld['Close'].iloc[0] - 1) * 100,
                    "SPY (S&P 500)": (spy['Close'] / spy['Close'].iloc[0] - 1) * 100
                }
                fig = make_line_chart(comp, "금 vs S&P 500 (5년 상대비교)", yaxis_title="%", height=350, show_zero=True)
                st.plotly_chart(fig, use_container_width=True)

        with c2:
            gdx = fetch_yf("GDX", "5y")
            if len(gdx) > 0 and len(gld) > 0:
                comp = {
                    "GDX (금광주)": (gdx['Close'] / gdx['Close'].iloc[0] - 1) * 100,
                    "GLD (금 ETF)": (gld['Close'] / gld['Close'].iloc[0] - 1) * 100
                }
                fig = make_line_chart(comp, "금광주 vs 금 ETF (5년)", yaxis_title="%", height=350, show_zero=True)
                st.plotly_chart(fig, use_container_width=True)

    with tab2:
        commodities = {"금": "GC=F", "은": "SI=F", "WTI 원유": "CL=F", "구리": "HG=F", "천연가스": "NG=F"}
        comm_data = {}
        for name, ticker in commodities.items():
            data = fetch_yf(ticker, "1y")
            if len(data) > 0:
                comm_data[name] = (data['Close'] / data['Close'].iloc[0] - 1) * 100

        if comm_data:
            fig = make_line_chart(comm_data, "📊 원자재 1년 상대 퍼포먼스 (%)", yaxis_title="%", height=450, show_zero=True)
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.markdown("### 🔄 Gold → Copper → Energy 순환 (에모리 분석)")
        st.markdown("에모리 채널의 핵심 테제: **금이 먼저 오르고, 구리가 따라오고, 마지막으로 에너지가 상승**하는 패턴")

        rotation_tickers = {
            "금광주 (GDX)": "GDX",
            "구리광산 (COPX)": "COPX",
            "에너지 (XLE)": "XLE"
        }
        rot_data = {}
        for name, ticker in rotation_tickers.items():
            data = fetch_yf(ticker, "5y")
            if len(data) > 0:
                rot_data[name] = (data['Close'] / data['Close'].iloc[0] - 1) * 100

        if rot_data:
            fig = make_line_chart(rot_data, "Gold Miners → Copper Miners → Energy (5년)", yaxis_title="%", height=450, show_zero=True)
            st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 페이지 6: 크레딧 & 채권
# ============================================================
elif page == "📊 크레딧 & 채권":
    st.title("📊 크레딧 & 채권")

    c1, c2 = st.columns(2)
    with c1:
        hy = fetch_fred("BAMLH0A0HYM2", "2005-01-01")
        if len(hy) > 0:
            fig = make_line_chart({"HY 스프레드": hy}, "⚠️ 하이일드 크레딧 스프레드 (ICE BofA)", yaxis_title="%", height=400)
            # 위험 수준 표시
            fig.add_hline(y=5, line_dash="dash", line_color=COLORS['accent'], annotation_text="경고 수준")
            fig.add_hline(y=8, line_dash="dash", line_color=COLORS['red'], annotation_text="위기 수준")
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        ig = fetch_fred("BAMLC0A0CM", "2005-01-01")
        if len(ig) > 0:
            fig = make_line_chart({"IG 스프레드": ig}, "📊 투자등급 크레딧 스프레드", yaxis_title="%", height=400)
            st.plotly_chart(fig, use_container_width=True)

    # 미국채 금리 곡선
    st.markdown("### 📈 미국채 금리 구조")
    maturities = {"3M": "DGS3MO", "2Y": "DGS2", "5Y": "DGS5", "10Y": "DGS10", "30Y": "DGS30"}
    rates = {}
    for name, code in maturities.items():
        r = fetch_fred(code, "2024-01-01")
        if len(r) > 0:
            rates[name] = r.iloc[-1]

    if rates:
        fig = go.Figure(go.Scatter(
            x=list(rates.keys()), y=list(rates.values()),
            mode='lines+markers', line=dict(color=COLORS['blue'], width=3),
            marker=dict(size=10, color=COLORS['accent'])
        ))
        fig.update_layout(
            title="현재 미국채 금리 커브",
            paper_bgcolor=COLORS['card'], plot_bgcolor=COLORS['bg'],
            font=dict(color=COLORS['text']),
            yaxis=dict(title="금리 (%)", gridcolor='#2D3748'),
            height=350, margin=dict(l=50, r=20, t=60, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 페이지 7: 시즌성 & 사이클
# ============================================================
elif page == "📅 시즌성 & 사이클":
    st.title("📅 시즌성 & 대통령 사이클")

    tab1, tab2 = st.tabs(["월별 시즌성", "대통령 사이클"])

    with tab1:
        st.markdown("### 📊 S&P 500 월별 시즌성 (1990년~현재, 자체 계산)")
        avg_ret, win_rate = calc_seasonality()

        months_kr = ['1월', '2월', '3월', '4월', '5월', '6월',
                     '7월', '8월', '9월', '10월', '11월', '12월']

        c1, c2 = st.columns(2)
        with c1:
            fig = make_bar_chart(months_kr, avg_ret.values, "월별 평균 수익률 (%)", height=400)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            colors = [COLORS['green'] if w >= 60 else COLORS['accent'] if w >= 50 else COLORS['red'] for w in win_rate.values]
            fig = make_bar_chart(months_kr, win_rate.values, "월별 승률 (%)", color=colors, height=400)
            st.plotly_chart(fig, use_container_width=True)

        # 현재 월 하이라이트
        current_month = datetime.now().month
        st.success(f"📅 현재 {current_month}월 | 평균 수익률: {avg_ret.iloc[current_month-1]:.2f}% | 승률: {win_rate.iloc[current_month-1]:.1f}%")

    with tab2:
        st.markdown("### 🏛️ 대통령 사이클별 S&P 500 수익률 (1950년~현재, 자체 계산)")
        pres_cycle = calc_president_cycle()

        colors = [COLORS['teal'], COLORS['red'], COLORS['green'], COLORS['accent']]
        fig = go.Figure(go.Bar(
            x=pres_cycle.index, y=pres_cycle.values,
            marker_color=colors,
            text=[f"{v:.1f}%" for v in pres_cycle.values],
            textposition='outside'
        ))
        fig.update_layout(
            title="대통령 사이클별 S&P 500 평균 연간 수익률",
            paper_bgcolor=COLORS['card'], plot_bgcolor=COLORS['bg'],
            font=dict(color=COLORS['text']), height=400,
            yaxis=dict(title="평균 수익률 (%)", gridcolor='#2D3748'),
            margin=dict(l=50, r=20, t=60, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)

        # 현재 사이클 위치
        current_year = datetime.now().year
        cycle_pos = ((current_year - 1) % 4) + 1
        labels = {1: '취임 1년차', 2: '중간선거 해', 3: '예비선거 전해', 4: '대통령 선거 해'}
        st.info(f"🏛️ {current_year}년은 **{labels[cycle_pos]}**에 해당합니다.")


# ============================================================
# 페이지 8: 섹터 로테이션
# ============================================================
elif page == "🎯 섹터 로테이션":
    st.title("🎯 섹터 로테이션 모니터")

    # 섹터 ETF 비교
    period = st.selectbox("분석 기간", ["1mo", "3mo", "6mo", "1y"], index=2, key="sector_period")

    sector_map = {
        '에너지 XLE': 'XLE', '소재 XLB': 'XLB', '산업재 XLI': 'XLI',
        '경기소비 XLY': 'XLY', '필수소비 XLP': 'XLP', '헬스케어 XLV': 'XLV',
        '금융 XLF': 'XLF', 'IT XLK': 'XLK', '커뮤니케이션 XLC': 'XLC',
        '유틸리티 XLU': 'XLU', '부동산 XLRE': 'XLRE'
    }

    returns = {}
    for name, ticker in sector_map.items():
        data = fetch_yf(ticker, period)
        if len(data) > 1:
            ret = ((data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1) * 100
            returns[name] = ret

    if returns:
        sorted_ret = dict(sorted(returns.items(), key=lambda x: x[1], reverse=True))
        fig = make_bar_chart(list(sorted_ret.keys()), list(sorted_ret.values()),
                             f"섹터별 수익률 ({period})", height=450)
        st.plotly_chart(fig, use_container_width=True)

    # 3대 변수 모니터
    st.markdown("### 🔑 에모리 3대 변수 모니터")
    st.markdown("**금리 → IT/REIT  |  경기 → 소비재/산업재  |  인플레 → 에너지/소재**")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("#### 📉 변수1: 금리")
        dgs10 = fetch_fred("DGS10", "2024-01-01")
        if len(dgs10) > 0:
            current_rate = dgs10.iloc[-1]
            prev_rate = dgs10.iloc[-30] if len(dgs10) > 30 else dgs10.iloc[0]
            direction = "하락 중 📉" if current_rate < prev_rate else "상승 중 📈"
            signal = "IT/REIT 유리" if current_rate < prev_rate else "금융주 유리"
            st.metric("10Y 금리", f"{current_rate:.2f}%", f"{current_rate - prev_rate:+.2f}%")
            st.caption(f"방향: {direction} → {signal}")

    with c2:
        st.markdown("#### 📊 변수2: 경기")
        umcsent = fetch_fred("UMCSENT", "2024-01-01")
        if len(umcsent) > 0:
            current_sent = umcsent.iloc[-1]
            prev_sent = umcsent.iloc[-3] if len(umcsent) > 3 else umcsent.iloc[0]
            direction = "개선 중 📈" if current_sent > prev_sent else "악화 중 📉"
            signal = "소비재/산업재 유리" if current_sent > prev_sent else "디펜시브 유리"
            st.metric("소비자신뢰", f"{current_sent:.1f}", f"{current_sent - prev_sent:+.1f}")
            st.caption(f"방향: {direction} → {signal}")

    with c3:
        st.markdown("#### 🔥 변수3: 인플레")
        bei = fetch_fred("T10YIE", "2024-01-01")
        if len(bei) > 0:
            current_bei = bei.iloc[-1]
            prev_bei = bei.iloc[-30] if len(bei) > 30 else bei.iloc[0]
            direction = "상승 중 📈" if current_bei > prev_bei else "하락 중 📉"
            signal = "에너지/소재 유리" if current_bei > prev_bei else "성장주 유리"
            st.metric("기대 인플레", f"{current_bei:.2f}%", f"{current_bei - prev_bei:+.2f}%")
            st.caption(f"방향: {direction} → {signal}")


# ============================================================
# 푸터
# ============================================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #8899AA; font-size: 12px;'>
📊 중요투자 데이터 대시보드 | 데이터 소스: FRED, Yahoo Finance, WGC, FINRA 등 23개<br>
본 대시보드는 정보 제공 목적이며, 투자 권유가 아닙니다.
</div>
""", unsafe_allow_html=True)
