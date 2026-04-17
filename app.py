"""
Everybody Investment - 중요투자 데이터 대시보드
=============================================================
23개+ 무료 데이터 소스 통합 | 모든 차트에 데이터 출처·단위 명시
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import requests
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="중요투자 데이터 대시보드", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

try:
    FRED_API_KEY = st.secrets["FRED_API_KEY"]
except Exception:
    FRED_API_KEY = "DEMO_KEY"

C = {'bg':'#0F1A2E','card':'#1A2744','accent':'#E8A838','blue':'#3B7DD8','green':'#3DAA6D',
     'red':'#E05252','text':'#E8ECF1','sub':'#8899AA','white':'#FFFFFF','teal':'#2E86AB',
     'purple':'#8B5CF6','orange':'#F59E0B','grid':'#2D3748'}

# === 데이터 수집 ===
@st.cache_data(ttl=3600)
def fred(sid, start="2000-01-01"):
    try:
        r = requests.get("https://api.stlouisfed.org/fred/series/observations",
            params={"series_id":sid,"api_key":FRED_API_KEY,"file_type":"json","observation_start":start}, timeout=10)
        df = pd.DataFrame(r.json()['observations'])
        df['date'] = pd.to_datetime(df['date'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        return df.dropna(subset=['value']).set_index('date')['value']
    except:
        return pd.Series(dtype=float)

@st.cache_data(ttl=3600)
def yfd(ticker, period="5y"):
    try:
        d = yf.download(ticker, period=period, progress=False)
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        return d
    except:
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def calc_seasonality():
    spy = yf.download("^GSPC", start="1990-01-01", progress=False)
    if isinstance(spy.columns, pd.MultiIndex): spy.columns = spy.columns.get_level_values(0)
    m = spy['Close'].resample('ME').last().pct_change()*100
    m = m.dropna()
    df = pd.DataFrame({'r':m.values}, index=m.index); df['m']=df.index.month
    return df.groupby('m')['r'].mean(), df.groupby('m')['r'].apply(lambda x:(x>0).mean()*100)

@st.cache_data(ttl=86400)
def calc_pres_cycle():
    spy = yf.download("^GSPC", start="1950-01-01", progress=False)
    if isinstance(spy.columns, pd.MultiIndex): spy.columns = spy.columns.get_level_values(0)
    a = spy['Close'].resample('YE').last().pct_change()*100; a=a.dropna()
    df = pd.DataFrame({'r':a.values}, index=a.index)
    df['cy'] = ((df.index.year-1)%4)+1
    lb = {1:'취임1년',2:'중간선거',3:'예비선거전',4:'선거해'}
    avg = df.groupby('cy')['r'].mean(); avg.index = avg.index.map(lb)
    return avg

# === 차트 유틸 ===
def layout(fig, title, ya="", src="", h=400, xrot=0):
    ann = []
    if src:
        ann.append(dict(text=f"📊 출처: {src}", xref="paper", yref="paper",
            x=0, y=-0.28, showarrow=False, font=dict(size=9, color=C['sub'])))
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=14, color=C['white']), x=0.01, y=0.98),
        paper_bgcolor=C['card'], plot_bgcolor=C['bg'],
        font=dict(color=C['text'], size=11),
        xaxis=dict(gridcolor=C['grid'], tickangle=xrot, tickfont=dict(size=10)),
        yaxis=dict(title=dict(text=ya, font=dict(size=11)), gridcolor=C['grid'], tickfont=dict(size=10)),
        legend=dict(
            orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5,
            font=dict(size=11, color=C['white']),
            bgcolor="rgba(26,39,68,0.9)", bordercolor=C['grid'], borderwidth=1,
        ),
        height=h, margin=dict(l=60, r=20, t=40, b=110 if src else 90), annotations=ann)
    return fig

def lchart(sd, title, ya="", src="", h=400, zero=False):
    fig = go.Figure()
    cols = [C['blue'],C['accent'],C['green'],C['red'],C['purple'],C['teal']]
    for i,(n,s) in enumerate(sd.items()):
        if len(s)>0:
            fig.add_trace(go.Scatter(x=s.index, y=s.values, name=n,
                line=dict(color=cols[i%len(cols)], width=2),
                hovertemplate=f'{n}<br>%{{x|%Y-%m-%d}}: %{{y:.2f}}<extra></extra>'))
    if zero: fig.add_hline(y=0, line_dash="dash", line_color=C['sub'], opacity=0.5)
    return layout(fig, title, ya, src, h)

def hbar(labels, vals, title, src="", h=400):
    colors = [C['green'] if v>=0 else C['red'] for v in vals]
    fig = go.Figure(go.Bar(y=labels, x=vals, orientation='h', marker_color=colors,
        text=[f"{v:+.1f}%" for v in vals], textposition='outside', textfont=dict(size=10),
        showlegend=False))
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return layout(fig, title, "", src, h)

# === 사이드바 ===
with st.sidebar:
    st.markdown("## 📊 중요투자 데이터 대시보드")
    st.caption("by Everybody Investment")
    st.markdown("---")
    page = st.radio("📑 페이지", [
        "📖 투자 판단 가이드",
        "🏠 종합 대시보드", "📈 거시경제 지표", "📋 미국경제 종합표",
        "💰 시장 밸류에이션", "🔄 자금흐름 & 심리",
        "🥇 금·원자재·에너지", "📊 크레딧 & 채권",
        "📅 시즌성 & 사이클", "🎯 섹터 로테이션", "🌍 글로벌 자산 수익률",
    ], index=0)
    st.markdown("---")
    st.caption(f"업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ============================================================
if page == "📖 투자 판단 가이드":
    st.title("📖 투자 판단 가이드")
    st.caption("대시보드 사용법 + 시장 판단 기준")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗺️ 대시보드 지도", "🎯 3대 핵심 변수", "🧭 판단 프레임워크",
        "📊 지표 해석 가이드", "💼 자산 단계별 전략"
    ])

    with tab1:
        st.markdown("## 🗺️ 어떤 페이지를 언제 봐야 하나")
        st.markdown("""
| 시점/상황 | 추천 페이지 | 핵심 체크 포인트 |
|---|---|---|
| **매일 아침 5분** | 🏠 종합 대시보드 | S&P500, 금, 원유, 10Y, DXY 전일비 / HY 스프레드 / 섹터 순위 |
| **주 1회 시장 점검** | 📈 거시경제 지표 | CPI, PPI, 실업률 최신치 / 연준 목표 2% 대비 |
| **월 1회 심층 분석** | 📋 미국경제 종합표 | 전월 대비 지표 개선/악화 방향 |
| **경기 방향 판단** | 🎯 섹터 로테이션 + 3대 변수 | 금리/경기/인플레 방향 → 유리한 섹터 확인 |
| **밸류에이션 체크** | 💰 시장 밸류에이션 | Forward PE, CAPE Ratio 역사적 평균 대비 |
| **리스크 감지** | 🔄 자금흐름 & 심리 + 📊 크레딧 | VIX 30+ / HY 스프레드 5%+ 경보 |
| **포트폴리오 리밸런싱** | 🥇 금·원자재 + 🌍 글로벌 자산 | 자산군별 상대 퍼포먼스 비교 |
| **계절 전략** | 📅 시즌성 & 사이클 | 현재 월 승률, 대통령 사이클 연차 |
""")

        st.markdown("## 💡 대시보드 활용의 5가지 원칙")
        st.markdown("""
1. **"과거 데이터를 우선, 뉴스는 후순위"** — 이슈(재료)는 시장이 이미 반영한 경우가 많음. 실제 움직인 데이터로 판단.
2. **"하나의 지표만 보지 말고 여러 지표의 일치를 확인"** — 예: 일드커브 역전 + HY 스프레드 상승 + VIX 급등이 동시 발생해야 신뢰.
3. **"방향이 바뀌는 순간을 포착"** — 절대 수준보다 변화 방향이 중요. Delta(변화분) 주시.
4. **"극단적 상황을 기다림"** — VIX 30+, HY 스프레드 5%+ 같은 명확한 시그널에서만 큰 베팅.
5. **"자신의 자산 단계에 맞는 전략"** — 5천만엔 미만 vs 1억엔 이상은 완전히 다른 전략 (5번 탭 참조).
""")

    with tab2:
        st.markdown("## 🎯 3대 핵심 변수 모니터링")
        st.caption("모든 투자 판단의 출발점")

        st.markdown("""
### 변수 1: **금리 (Interest Rate)**
- **측정 지표**: 미국 10Y 국채금리 (FRED: DGS10)
- **의미**: 모든 자산 가치의 할인율 기준
- **방향별 영향**:
  - 🔻 **금리 하락** → IT주·성장주·REIT(부동산) 유리, 금 상승
  - 🔺 **금리 상승** → 금융주 유리, 성장주 불리, 채권가격 하락
- **주시 레벨**:
  - 4.5% 이상 = 경기 부담 가능성 높음
  - 일드커브(10Y-2Y) < 0 = 경기침체 선행 경고 (1년 이내 침체 가능성 ↑)

### 변수 2: **경기 (Economic Growth)**
- **측정 지표**: 미시간대 소비자신뢰 (UMCSENT), ISM PMI, NFP 고용
- **의미**: 기업 이익 증감의 근본 동력
- **방향별 영향**:
  - 🔺 **경기 개선** → 소비재·산업재·경기민감주 유리
  - 🔻 **경기 악화** → 필수소비재·헬스케어·유틸리티 등 디펜시브 유리
- **주시 레벨**:
  - ISM 제조업 PMI > 50 = 확장, < 50 = 위축
  - NFP(비농업고용) 월 10만 미만 = 경기 둔화 신호

### 변수 3: **인플레이션 (Inflation)**
- **측정 지표**: CPI YoY, 기대인플레(T10YIE), PPI YoY
- **의미**: 실질 수익률을 결정하는 핵심 변수
- **방향별 영향**:
  - 🔺 **인플레 상승** → 에너지·소재·금/은(실물) 유리
  - 🔻 **인플레 하락** → IT·바이오·성장주 유리
- **주시 레벨**:
  - CPI > 3% = 연준 긴축 지속 압력
  - 기대인플레 > 2.5% = 장기 인플레 고착 우려
""")

        st.info("💡 **실전 팁**: 🎯 섹터 로테이션 페이지에서 이 3개 변수의 현재 방향을 실시간으로 볼 수 있습니다.")

    with tab3:
        st.markdown("## 🧭 시장 국면별 판단 프레임워크")

        st.markdown("""
### 📍 현재 국면을 파악하는 체크리스트

**1단계: 매크로 환경 확인 (월 1회)**
- [ ] 일드커브(10Y-2Y) 역전 여부 → 역전 상태면 **경계**
- [ ] 미국 10Y 금리 방향 → 하락 중이면 **성장주 유리**
- [ ] CPI vs 2% 목표 → 2% 초과면 **긴축 지속 가능성**
- [ ] 실업률 방향 → 상승 반전 시 **침체 신호**

**2단계: 시장 밸류에이션 (월 1회)**
- [ ] S&P500 Forward PE > 20배 → **과열 구간**
- [ ] Shiller CAPE > 30 → **역사적 고평가**
- [ ] Buffett Indicator > 150% → **거품 주의**
- [ ] Equity Risk Premium < 3% → **주식 프리미엄 낮음**

**3단계: 리스크 게이지 (주 1회)**
- [ ] VIX 수준: 20 미만 = 안정, 20~30 = 주의, 30+ = 공포
- [ ] HY 크레딧 스프레드: 3%pt 미만 = 안정, 5%pt+ = 경고, 8%pt+ = 위기
- [ ] IG 크레딧 스프레드: 1%pt 미만 = 안정, 2%pt+ = 경고

**4단계: 단기 모멘텀 (일 1회)**
- [ ] S&P500 50일선 대비 위치
- [ ] 섹터 순위 변화 (디펜시브가 상위로 올라오면 경계)
- [ ] 금·국채 등 안전자산 강세 여부
""")

        st.markdown("""
### 🚦 국면별 액션 가이드

| 국면 | 시그널 | 추천 전략 |
|------|-------|---------|
| 🟢 **확장 초기** | 일드커브 정상, PMI>50, VIX<20 | 경기민감주(IT/산업재/소비재) 비중 확대 |
| 🟡 **확장 말기** | PMI 둔화, 밸류에이션 과열 | 현금 비중 10~20% 확보, 디펜시브 추가 |
| 🟠 **경기 침체 진입** | 일드커브 역전 지속, HY 급등 | 금·미국채·현금 비중 대폭 확대 |
| 🔴 **위기 국면** | VIX 30+, HY 8%+, 주가 -20%+ | 저점매수 준비 (단계적 분할매수) |
| 🔵 **회복 초기** | 저점 3개월 + 지표 개선 | 성장주·경기민감주 재진입 |
""")

        st.warning("⚠️ **2026년 4월 현재 체크포인트**: 일드커브 상태, 크레딧 스프레드, VIX를 매일 확인하세요. 🏠 종합 대시보드에서 3개 차트를 한 화면에 볼 수 있습니다.")

    with tab4:
        st.markdown("## 📊 개별 지표 해석 가이드")

        with st.expander("🧑‍💼 실업률 (Unemployment Rate)"):
            st.markdown("""
- **출처**: FRED (UNRATE), 미 노동통계국 BLS, 월간 발표
- **정상 범위**: 3.5% ~ 5.0%
- **해석**:
  - 3% 미만 = 완전고용, 인플레 압력
  - 5% 초과 = 경기 둔화 신호
  - **방향이 중요**: 상승 반전이 침체 선행 신호 (Sahm Rule)
- **투자 판단**: 상승 반전 시 디펜시브·금·채권 비중 확대
""")

        with st.expander("🔥 CPI (소비자물가지수)"):
            st.markdown("""
- **출처**: FRED (CPIAUCSL), BLS, 월간 발표
- **주목 수치**:
  - 전년대비 2% = 연준 목표
  - 3% 초과 = 긴축 지속
  - 4% 초과 = 공격적 긴축 가능성
- **Core CPI** (식료품·에너지 제외)가 더 중요
- **투자 판단**: 상승 추세 → 에너지·금·실물자산 / 하락 추세 → 성장주·채권
""")

        with st.expander("📉 일드커브 (Yield Curve, 10Y-2Y)"):
            st.markdown("""
- **출처**: FRED (T10Y2Y)
- **정상**: 양수 (장기금리 > 단기금리)
- **역전** (음수): 경기침체 선행 신호 (과거 8회 중 8회 적중)
- **시차**: 역전 후 평균 12~18개월 뒤 침체 발생
- **주의**: 역전 후 "정상화" 시점이 실제 침체 시작과 가까움
- **투자 판단**: 역전 시작 → 현금 확보 / 정상화 시 → 디펜시브 전환
""")

        with st.expander("⚠️ HY 크레딧 스프레드 (ICE BofA)"):
            st.markdown("""
- **출처**: FRED (BAMLH0A0HYM2)
- **의미**: 하이일드 채권과 미국채의 금리차
- **레벨**:
  - 3%pt 이하 = 매우 안정 (위험 무시)
  - 3~5%pt = 정상
  - 5~8%pt = 경고 (경기 악화)
  - 8%pt 이상 = 위기 (2008, 2020 수준)
- **가장 빠른 시장 위험 감지 지표 중 하나**
- **투자 판단**: 5%pt 돌파 시 주식 비중 축소 고려
""")

        with st.expander("😱 VIX (공포지수)"):
            st.markdown("""
- **출처**: Yahoo Finance (^VIX), CBOE
- **의미**: S&P500 옵션의 내재변동성
- **레벨**:
  - 12~15 = 매우 안정
  - 15~20 = 평균
  - 20~30 = 주의
  - 30+ = 공포 (매수 기회 검토)
  - 40+ = 극도 공포 (역사적 저점 부근)
- **투자 판단**: 30+ 에서 분할 매수, 15 미만 장기 지속 시 현금 확보
""")

        with st.expander("🥇 금 (Gold) 판단 기준"):
            st.markdown("""
- **핵심 관계**: 금 가격 ∝ -실질금리 (역상관)
  - 실질금리 = 명목금리 - 기대인플레
  - 실질금리 하락 → 금 상승
- **시스템 리스크 지표**: 금융위기, 지정학적 긴장 시 상승
- **과거 3대 상승 사이클**:
  - 1968-80: 인플레 + 스태그플레이션 (약 20배 상승)
  - 1999-2011: 닷컴붕괴 + 금융위기 (약 7배 상승)
  - 2015~현재: 저금리 + 중앙은행 매수 (진행 중)
- **투자 판단**: 실질금리 하락 + 지정학 리스크 = 매수 타이밍
""")

        with st.expander("🛢️ 원유 (Oil) 판단 기준"):
            st.markdown("""
- **생산비 하한선**: 글로벌 평균 약 $50/배럴 (OPEC $30, 셰일 $55)
- **$50 미만 지속 시**: 생산 감소 → 반등 가능성 높음
- **$100 돌파 시**: 수요 파괴 우려, 경기 침체 위험
- **OPEC 감산/증산** 결정이 가장 큰 가격 동인
- **투자 판단**: $50 부근 지지 확인 시 에너지주 비중 확대
""")

    with tab5:
        st.markdown("## 💼 자산 규모별 투자 전략")
        st.caption("자산 규모별 단계별 접근")

        st.markdown("""
### 💰 Stage 1: ~5천만엔 (약 4.5억원)
**핵심: 공격적 자산 증식 + 입금력 향상**

- **전략**: 신중하지만 적극적 운용, CFD 등 레버리지도 활용 가능
- **포트폴리오 예시**:
  - 주식 70~80% (성장주 중심, 개별종목)
  - 현금/단기채 10~20%
  - 금/원자재 5~10%
- **중점**: **입금력 향상**이 수익률보다 중요. 사업소득·근로소득 확대
- **리스크**: 드로다운 -30%까지 감내 가능
""")

        st.markdown("""
### 💎 Stage 2: 5천만엔 ~ 1억엔 (약 4.5억~9억원)
**핵심: 성장 유지 + 안정성 추가**

- **전략**: 적극적 운용 지속, 배당주·분배금 투자 점진 도입
- **포트폴리오 예시**:
  - 주식 60~70% (성장주 + 배당주 혼합)
  - 배당주/REIT 10~20%
  - 현금/채권 10~15%
  - 금/원자재 5~10%
- **중점**: 자산이 "가속도적으로" 증가하는 구간. 기반 자산 확대가 목표
- **리스크**: 드로다운 -20% 수준 관리
""")

        st.markdown("""
### 🏦 Stage 3: 1억엔+ (약 9억원 이상)
**핵심: 안정 운용 + 자본 보전**

- **전략**: 배당·분산 중심, CFD·레버리지 비중 축소
- **포트폴리오 예시**:
  - 주식 40~50% (배당주·블루칩 중심)
  - 채권 20~30% (국채·IG 크레딧)
  - 금/원자재 10~15%
  - 현금 10~15%
  - 대체투자 (부동산 등) 5~10%
- **중점**: 일시적 쇼크로 인한 자산 급감 방지
- **리스크**: 드로다운 -10% 이내 관리

### ⚠️ 공통 원칙
- **"자산이 커질수록 가속도적으로 증가"** — 복리의 힘
- **"급격한 자산 증가는 일시적 쇼크에 취약"** — 분산의 중요성
- **포트폴리오 구축 3요소**:
  1. **무엇을** 살 것인가 (Stock Selection)
  2. **언제** 살 것인가 (Timing)
  3. **얼마나** 살 것인가 (Allocation)
""")


# ============================================================
elif page == "🏠 종합 대시보드":
    st.title("📊 중요투자 데이터 대시보드")
    st.caption("Everybody Investment | 실시간 글로벌 시장 모니터링")

    # Reduce metric value font size so full numbers are visible
    st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.85rem !important; }
    [data-testid="stMetricDelta"] { font-size: 0.85rem !important; }
    </style>
    """, unsafe_allow_html=True)

    metrics_data = [
        ("S&P 500","^GSPC","pt"),("NASDAQ","^IXIC","pt"),("금(Gold)","GC=F","$/oz"),
        ("WTI원유","CL=F","$/bbl"),("미국10Y","^TNX","%"),("달러DXY","DX-Y.NYB","pt")
    ]
    # First row: 3 metrics
    r1 = st.columns(3)
    for col, (nm, tk, u) in zip(r1, metrics_data[:3]):
        with col:
            d = yfd(tk, "5d")
            if len(d) >= 2:
                cur, prev = d['Close'].iloc[-1], d['Close'].iloc[-2]
                chg = ((cur/prev)-1)*100
                if u == "%": col.metric(nm, f"{cur:.2f}%", f"{chg:+.2f}%")
                elif cur > 1000: col.metric(nm, f"{cur:,.0f}", f"{chg:+.2f}%")
                else: col.metric(nm, f"{cur:.2f}", f"{chg:+.2f}%")
    # Second row: 3 metrics
    r2 = st.columns(3)
    for col, (nm, tk, u) in zip(r2, metrics_data[3:]):
        with col:
            d = yfd(tk, "5d")
            if len(d) >= 2:
                cur, prev = d['Close'].iloc[-1], d['Close'].iloc[-2]
                chg = ((cur/prev)-1)*100
                if u == "%": col.metric(nm, f"{cur:.2f}%", f"{chg:+.2f}%")
                elif cur > 1000: col.metric(nm, f"{cur:,.0f}", f"{chg:+.2f}%")
                else: col.metric(nm, f"{cur:.2f}", f"{chg:+.2f}%")

    st.markdown("---")
    c1,c2 = st.columns(2)
    with c1:
        sp=yfd("^GSPC","1y")
        if len(sp)>0:
            st.plotly_chart(lchart({"S&P 500 지수":sp['Close']},
                "S&P 500 지수 (1년)", ya="지수 (포인트)", src="Yahoo Finance (^GSPC)"), use_container_width=True)
    with c2:
        g=yfd("GC=F","1y")
        if len(g)>0:
            st.plotly_chart(lchart({"금 선물":g['Close']},
                "금(Gold) 선물 가격 (1년)", ya="USD / 온스", src="Yahoo Finance (GC=F, COMEX)"), use_container_width=True)
    c3,c4 = st.columns(2)
    with c3:
        t=fred("T10Y2Y","2020-01-01")
        if len(t)>0:
            fig=lchart({"10Y-2Y 금리차":t}, "일드커브 스프레드 (10Y-2Y 국채)", ya="금리차 (%pt)", src="FRED (T10Y2Y)", zero=True)
            fig.add_hline(y=0,line_color=C['red'],line_width=2,annotation_text="역전 기준선",annotation_font_size=9,annotation_font_color=C['red'])
            st.plotly_chart(fig, use_container_width=True)
    with c4:
        h=fred("BAMLH0A0HYM2","2020-01-01")
        if len(h)>0:
            fig=lchart({"HY 스프레드":h}, "하이일드 크레딧 스프레드", ya="스프레드 (%pt)", src="FRED (BAMLH0A0HYM2, ICE BofA)")
            fig.add_hline(y=5,line_dash="dash",line_color=C['accent'],annotation_text="경고 5%",annotation_font_size=9)
            st.plotly_chart(fig, use_container_width=True)
    st.markdown("### 📊 S&P 500 섹터별 6개월 수익률")
    sm = {'에너지(XLE)':'XLE','소재(XLB)':'XLB','산업재(XLI)':'XLI','소비재(XLY)':'XLY',
          '필수소비(XLP)':'XLP','헬스케어(XLV)':'XLV','금융(XLF)':'XLF','IT(XLK)':'XLK',
          '통신(XLC)':'XLC','유틸리티(XLU)':'XLU','부동산(XLRE)':'XLRE'}
    rets={}
    for n,t in sm.items():
        d=yfd(t,"6mo")
        if len(d)>1: rets[n]=((d['Close'].iloc[-1]/d['Close'].iloc[0])-1)*100
    if rets:
        sr=dict(sorted(rets.items(),key=lambda x:x[1]))
        st.plotly_chart(hbar(list(sr.keys()),list(sr.values()),
            "섹터별 6개월 수익률 (가로 바 차트)", src="Yahoo Finance (SPDR 섹터 ETF)", h=450), use_container_width=True)

elif page == "📈 거시경제 지표":
    st.title("📈 미국 거시경제 지표")
    tab1,tab2,tab3 = st.tabs(["🧑‍💼 고용","🔥 인플레","🏛️ 금리"])
    with tab1:
        c1,c2=st.columns(2)
        with c1:
            u=fred("UNRATE","2000-01-01")
            if len(u)>0: st.plotly_chart(lchart({"실업률":u},"미국 실업률 (U-3)",ya="실업률 (%)",src="FRED (UNRATE, BLS)"),use_container_width=True)
        with c2:
            ic=fred("ICSA","2020-01-01")
            if len(ic)>0: st.plotly_chart(lchart({"신규실업수당":ic},"신규 실업수당 청구 (주간)",ya="건수",src="FRED (ICSA, 미 노동부)"),use_container_width=True)
        um=fred("UMCSENT","2000-01-01")
        if len(um)>0: st.plotly_chart(lchart({"소비자신뢰":um},"미시간대 소비자신뢰지수",ya="지수 (1966=100)",src="FRED (UMCSENT)"),use_container_width=True)
    with tab2:
        c1,c2=st.columns(2)
        with c1:
            cp=fred("CPIAUCSL","2000-01-01")
            if len(cp)>0:
                cy=cp.pct_change(12)*100
                fig=lchart({"CPI YoY":cy.dropna()},"소비자물가 (CPI) 전년동월비",ya="상승률 (%YoY)",src="FRED (CPIAUCSL, BLS)",zero=True)
                fig.add_hline(y=2,line_dash="dot",line_color=C['accent'],annotation_text="연준 목표 2%",annotation_font_size=9)
                st.plotly_chart(fig,use_container_width=True)
        with c2:
            be=fred("T10YIE","2010-01-01")
            if len(be)>0: st.plotly_chart(lchart({"10Y BEI":be},"기대인플레 (10Y BEI = TIPS 스프레드)",ya="기대인플레 (%)",src="FRED (T10YIE, TIPS)"),use_container_width=True)
        pp=fred("PPIACO","2000-01-01")
        if len(pp)>0:
            py=pp.pct_change(12)*100
            st.plotly_chart(lchart({"PPI YoY":py.dropna()},"생산자물가 (PPI) 전년동월비",ya="상승률 (%YoY)",src="FRED (PPIACO, BLS)",zero=True),use_container_width=True)
    with tab3:
        c1,c2=st.columns(2)
        with c1:
            ff=fred("FEDFUNDS","2000-01-01")
            if len(ff)>0: st.plotly_chart(lchart({"FF금리":ff},"연방기금금리 (Fed Funds Rate)",ya="금리 (%)",src="FRED (FEDFUNDS, 연준)"),use_container_width=True)
        with c2:
            t=fred("T10Y2Y","2000-01-01")
            if len(t)>0:
                fig=lchart({"10Y-2Y":t},"일드커브 (10Y-2Y 국채금리차)",ya="금리차 (%pt)",src="FRED (T10Y2Y)",zero=True)
                fig.add_hline(y=0,line_color=C['red'],line_width=2,annotation_text="역전 = 침체 선행신호",annotation_font_size=9,annotation_font_color=C['red'])
                st.plotly_chart(fig,use_container_width=True)
        st.markdown("### 🌍 주요국 국채 금리 비교")
        rd={}
        u10=fred("DGS10","2023-01-01")
        if len(u10)>0: rd["미국 10Y"]=u10
        j10=fred("IRLTLT01JPM156N","2023-01-01")
        if len(j10)>0: rd["일본 10Y"]=j10
        d10=fred("IRLTLT01DEM156N","2023-01-01")
        if len(d10)>0: rd["독일 10Y"]=d10
        if rd: st.plotly_chart(lchart(rd,"주요국 장기 국채금리 비교",ya="금리 (%)",src="FRED (DGS10, IRLTLT01JPM156N, IRLTLT01DEM156N)"),use_container_width=True)

elif page == "📋 미국경제 종합표":
    st.title("📋 미국 경제지표 종합표")
    st.caption("미국 주요 경제지표 실시간 종합 | FRED 데이터")

    tab1, tab2, tab3 = st.tabs(["📊 종합 테이블", "💼 고용 상세", "🏭 ISM & 생산"])

    with tab1:
        st.markdown("### 📅 월별 주요 경제지표 추이 (최근 15개월)")
        st.caption("녹색: 전월 대비 개선 / 빨간색: 악화")

        # Gather data
        indicators = {
            "소비자신뢰지수": ("UMCSENT", ""),
            "ISM제조업PMI": ("MANEMP", "인덱스 대체"),  # proxy
            "CPI YoY (%)": ("CPIAUCSL", "YoY"),
            "PPI YoY (%)": ("PPIACO", "YoY"),
            "실업률 (%)": ("UNRATE", ""),
            "신규 실업수당 (천건)": ("ICSA", ""),
            "소매판매 YoY (%)": ("RSAFS", "YoY"),
            "주택판매 YoY (%)": ("HSN1F", "YoY"),
        }

        df_list = []
        for name, (code, calc) in indicators.items():
            s = fred(code, "2024-01-01")
            if len(s) > 0:
                if calc == "YoY":
                    s = s.pct_change(12) * 100
                s = s.dropna()
                # Get last 15 months
                m = s.resample('ME').last().tail(15)
                df_list.append(pd.Series(m.values, index=m.index.strftime('%Y-%m'), name=name))

        if df_list:
            df = pd.DataFrame(df_list).T
            df.index.name = "월"
            df = df.iloc[::-1]  # 최신이 위로

            def highlight_change(col):
                styles = [''] * len(col)
                for i in range(len(col)-1):
                    try:
                        if pd.notna(col.iloc[i]) and pd.notna(col.iloc[i+1]):
                            if col.iloc[i] > col.iloc[i+1]:
                                styles[i] = 'background-color: #1B7A3D; color: white'
                            elif col.iloc[i] < col.iloc[i+1]:
                                styles[i] = 'background-color: #C0392B; color: white'
                    except:
                        pass
                return styles

            styled = df.style.format(precision=2).apply(highlight_change)
            st.dataframe(styled, use_container_width=True, height=550)
            st.caption("📊 출처: FRED (세인트루이스 연준) | 녹색=전월 대비 지표 개선, 빨강=악화 (실업률·CPI는 낮을수록 좋음)")

    with tab2:
        st.markdown("### 💼 미국 고용 상황 (NFP·실업률·임금)")
        st.caption("NFP(비농업고용) + 실업률 + 평균 시급 추이")

        c1, c2 = st.columns(2)
        with c1:
            nfp = fred("PAYEMS", "2010-01-01")
            if len(nfp) > 0:
                nfp_mom = nfp.diff().dropna()
                fig = go.Figure()
                recent = nfp_mom.tail(60)
                colors = [C['green'] if v > 0 else C['red'] for v in recent.values]
                fig.add_trace(go.Bar(x=recent.index, y=recent.values, marker_color=colors,
                    name="월간 고용 증감", hovertemplate='%{x|%Y-%m}: %{y:,.0f}<extra></extra>'))
                unrate = fred("UNRATE", "2010-01-01")
                if len(unrate) > 0:
                    unrate_recent = unrate.tail(60)
                    fig.add_trace(go.Scatter(x=unrate_recent.index, y=unrate_recent.values*200,
                        name="실업률 x200 (우축 참조)", yaxis="y2", line=dict(color=C['accent'], width=2)))
                    fig.update_layout(yaxis2=dict(overlaying='y', side='right', title="실업률 (%)",
                        tickvals=[3*200, 4*200, 5*200, 6*200], ticktext=['3%', '4%', '5%', '6%']))
                layout(fig, "NFP 월간 고용 증감 + 실업률 (최근 5년)",
                    ya="고용 증감 (명)", src="FRED (PAYEMS, UNRATE)")
                st.plotly_chart(fig, use_container_width=True)

        with c2:
            wages = fred("CES0500000003", "2010-01-01")  # Average Hourly Earnings
            if len(wages) > 0:
                wages_yoy = wages.pct_change(12) * 100
                fig = lchart({"평균 시급 YoY": wages_yoy.dropna()},
                    "평균 시급 상승률 (YoY)", ya="상승률 (%)",
                    src="FRED (CES0500000003, 평균 시급)")
                fig.add_hline(y=3, line_dash="dot", line_color=C['accent'],
                    annotation_text="역사적 평균 ~3%", annotation_font_size=9)
                st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.markdown("### 🏭 ISM & 산업 활동 지표")
        st.caption("ISM PMI · 산업생산 · 소매판매 · 주택 지표")

        # ISM proxy via FRED (실제 ISM PMI는 유료, NAPM은 대체)
        napm = fred("NAPM", "2000-01-01")  # ISM Manufacturing PMI (historical)
        if len(napm) == 0:
            # Try industrial production as alternative
            ipm = fred("INDPRO", "2000-01-01")
            if len(ipm) > 0:
                ipm_yoy = ipm.pct_change(12) * 100
                fig = lchart({"산업생산 YoY": ipm_yoy.dropna()},
                    "산업생산지수 (YoY) - ISM PMI 대체지표",
                    ya="증감률 (%)", src="FRED (INDPRO)", zero=True)
                st.plotly_chart(fig, use_container_width=True)
        else:
            # PMI chart
            fig = lchart({"ISM 제조업 PMI": napm}, "ISM 제조업 경기지수",
                ya="PMI (50=확장/위축 기준)", src="FRED (NAPM)")
            fig.add_hline(y=50, line_dash="dash", line_color=C['red'],
                annotation_text="확장/위축 기준선 (50)", annotation_font_size=9)
            st.plotly_chart(fig, use_container_width=True)

        # Retail Sales
        rs = fred("RSAFS", "2010-01-01")
        if len(rs) > 0:
            rs_yoy = rs.pct_change(12) * 100
            fig = lchart({"소매판매 YoY": rs_yoy.dropna()},
                "미국 소매판매 (YoY)", ya="증감률 (%)",
                src="FRED (RSAFS)", zero=True)
            st.plotly_chart(fig, use_container_width=True)

        # Housing
        c1, c2 = st.columns(2)
        with c1:
            hs = fred("HOUST", "2010-01-01")
            if len(hs) > 0:
                fig = lchart({"신규주택 착공": hs},
                    "신규 주택 착공 건수", ya="건수 (천)", src="FRED (HOUST)")
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            mort = fred("MORTGAGE30US", "2010-01-01")
            if len(mort) > 0:
                fig = lchart({"30년 고정 모기지": mort},
                    "30년 고정 모기지 금리", ya="금리 (%)", src="FRED (MORTGAGE30US)")
                st.plotly_chart(fig, use_container_width=True)

elif page == "💰 시장 밸류에이션":
    st.title("💰 시장 밸류에이션")
    period=st.selectbox("비교기간",["1mo","3mo","6mo","1y","2y","5y"],index=3)
    idx={"S&P 500":"^GSPC","NASDAQ 100":"^NDX","다우30":"^DJI","Russell 2000":"^RUT"}
    id_d={}
    for n,t in idx.items():
        d=yfd(t,period)
        if len(d)>0: id_d[n]=(d['Close']/d['Close'].iloc[0]-1)*100
    if id_d: st.plotly_chart(lchart(id_d,f"미국 주요 지수 상대 퍼포먼스 ({period})",ya="누적수익률 (%)",src="Yahoo Finance",zero=True),use_container_width=True)
    st.markdown("### 🌍 글로벌 지수 비교")
    gl={"S&P500":"^GSPC","TOPIX":"^TOPX","DAX":"^GDAXI","SENSEX":"^BSESN","EEM":"EEM"}
    gd={}
    for n,t in gl.items():
        d=yfd(t,period)
        if len(d)>0: gd[n]=(d['Close']/d['Close'].iloc[0]-1)*100
    if gd: st.plotly_chart(lchart(gd,f"글로벌 지수 상대 퍼포먼스 ({period})",ya="누적수익률 (%)",src="Yahoo Finance",zero=True),use_container_width=True)

elif page == "🔄 자금흐름 & 심리":
    st.title("🔄 자금흐름 & 심리")
    vx=yfd("^VIX","1y")
    if len(vx)>0:
        fig=lchart({"VIX":vx['Close']},"VIX 공포지수 (CBOE 변동성지수)",ya="VIX (포인트)",src="Yahoo Finance (^VIX, CBOE)")
        fig.add_hline(y=20,line_dash="dash",line_color=C['accent'],annotation_text="평균 20",annotation_font_size=9)
        fig.add_hline(y=30,line_dash="dash",line_color=C['red'],annotation_text="공포 30+",annotation_font_size=9)
        st.plotly_chart(fig,use_container_width=True)
    st.markdown("### 📌 외부 참조")
    st.markdown("- **Fear & Greed**: [CNN](https://money.cnn.com/data/fear-and-greed/) | **AAII 심리**: [AAII](https://www.aaii.com/sentimentsurvey) | **FINRA 마진**: [FINRA](https://www.finra.org/investors/learn-to-invest/advanced-investing/margin-statistics)")

elif page == "🥇 금·원자재·에너지":
    st.title("🥇 금·원자재·에너지")
    tab1,tab2,tab3=st.tabs(["금(Gold)","원자재 비교","원유"])
    with tab1:
        gp=st.selectbox("기간",["1y","2y","5y","10y"],index=2,key="gp")
        g=yfd("GC=F",gp)
        if len(g)>0: st.plotly_chart(lchart({"금 선물":g['Close']},f"금(Gold) 선물 ({gp})",ya="USD / 온스",src="Yahoo Finance (GC=F, COMEX)"),use_container_width=True)
        c1,c2=st.columns(2)
        with c1:
            gl,sp=yfd("GLD","5y"),yfd("SPY","5y")
            if len(gl)>0 and len(sp)>0:
                st.plotly_chart(lchart({"GLD (금ETF)":(gl['Close']/gl['Close'].iloc[0]-1)*100,"SPY (S&P500)":(sp['Close']/sp['Close'].iloc[0]-1)*100},
                    "금 ETF vs S&P 500 (5년)",ya="누적수익률 (%)",src="Yahoo Finance (GLD, SPY)",zero=True),use_container_width=True)
        with c2:
            gx=yfd("GDX","5y")
            if len(gx)>0 and len(gl)>0:
                st.plotly_chart(lchart({"GDX (금광주)":(gx['Close']/gx['Close'].iloc[0]-1)*100,"GLD (금ETF)":(gl['Close']/gl['Close'].iloc[0]-1)*100},
                    "금광주 vs 금 ETF (5년)",ya="누적수익률 (%)",src="Yahoo Finance (GDX, GLD)",zero=True),use_container_width=True)
        st.markdown("### 금 vs 실질금리")
        tips=fred("DFII10","2010-01-01"); gf=yfd("GC=F","10y")
        if len(tips)>0 and len(gf)>0:
            fig=make_subplots(specs=[[{"secondary_y":True}]])
            fig.add_trace(go.Scatter(x=gf.index,y=gf['Close'],name="금 (좌, USD/oz)",line=dict(color=C['accent'],width=2)),secondary_y=False)
            fig.add_trace(go.Scatter(x=tips.index,y=tips.values,name="10Y 실질금리 (우, %, 역축)",line=dict(color=C['teal'],width=2)),secondary_y=True)
            fig.update_yaxes(title_text="금 (USD/oz)",secondary_y=False)
            fig.update_yaxes(title_text="실질금리 (%)",autorange="reversed",secondary_y=True)
            layout(fig,"금 가격 vs 10Y 실질금리 (역상관, 우축 반전)",src="Yahoo Finance (GC=F) + FRED (DFII10)")
            st.plotly_chart(fig,use_container_width=True)

        # 금 상승 사이클 비교
        st.markdown("### 🔄 금 상승 패턴 비교: 3대 Bull Market")
        st.caption("과거 금 Bull Market 3개 사이클 비교 - 각 사이클 시작점 = 100")

        # Historical gold data - use approximate historical prices
        # Cycle 1: 1968-1980 (from $35 to $850)
        # Cycle 2: 1999-2011 (from $250 to $1,900)
        # Cycle 3: 2015-current
        c1_months = 144  # 12 years
        c1_returns = [100, 101, 100, 108, 118, 135, 180, 195, 195, 220, 250, 280, 300, 320, 340,
                      350, 360, 370, 380, 400, 420, 440, 450, 460, 470, 500, 540, 560, 580, 600,
                      610, 620, 640, 660, 680, 700, 720, 740, 760, 780, 800, 820, 840, 860, 880,
                      900, 920, 940, 960, 980, 1000, 1050, 1100, 1150, 1200, 1250, 1300, 1350,
                      1400, 1450, 1500, 1550, 1600, 1650, 1700, 1750, 1800, 1850, 1900, 1950, 2000,
                      2050, 2100, 2150, 2200, 2250, 2300, 2400, 2500, 2600, 2428]
        # Simpler: fetch from Yahoo if possible, else use current cycle only
        g_now = yfd("GC=F", "max")
        if len(g_now) > 0:
            # Calculate current cycle (2015~): use 2015-12-01 as low point
            g_cycle3 = g_now[g_now.index >= "2015-12-01"]['Close']
            if len(g_cycle3) > 0:
                g_c3 = (g_cycle3 / g_cycle3.iloc[0]) * 100
                # X-axis: months from cycle start
                g_c3_months = [(d - g_cycle3.index[0]).days / 30 for d in g_cycle3.index]

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=g_c3_months, y=g_c3.values,
                    name="2015~현재 사이클",
                    line=dict(color=C['red'], width=2.5),
                    hovertemplate='%{x:.0f}개월차: %{y:.0f}<extra></extra>'
                ))

                # Reference lines for past cycles (historical patterns)
                # 1968-1980: peaked at ~2400% after ~140 months
                # 1999-2011: peaked at ~660% after ~140 months
                past_months = list(range(0, 145, 6))
                # 1968-1980 historical normalized (approximate)
                c1_hist = [100, 105, 108, 112, 118, 125, 140, 180, 260, 330, 380, 420, 470, 520,
                          600, 680, 750, 820, 900, 1100, 1400, 1700, 2100, 2400, 2300]
                fig.add_trace(go.Scatter(
                    x=past_months[:len(c1_hist)], y=c1_hist,
                    name="1968-1980 사이클 (인플레·스태그플레이션)",
                    line=dict(color=C['blue'], width=2, dash='dot'),
                    hovertemplate='%{x:.0f}개월차: %{y:.0f}<extra></extra>'
                ))
                c2_hist = [100, 102, 105, 110, 115, 120, 125, 135, 145, 160, 175, 190, 210, 230,
                          250, 275, 300, 330, 360, 400, 450, 500, 560, 620, 660]
                fig.add_trace(go.Scatter(
                    x=past_months[:len(c2_hist)], y=c2_hist,
                    name="1999-2011 사이클 (닷컴·금융위기)",
                    line=dict(color=C['teal'], width=2, dash='dash'),
                    hovertemplate='%{x:.0f}개월차: %{y:.0f}<extra></extra>'
                ))

                layout(fig, "금 상승 사이클 비교 (시작점 = 100)",
                    ya="상대 지수 (시작=100)",
                    src="Yahoo Finance (GC=F) + 과거 사이클은 역사 데이터 기반 근사치",
                    h=500)
                fig.update_xaxes(title="사이클 시작 이후 경과 월 수")
                st.plotly_chart(fig, use_container_width=True)

                st.info(f"""
                💡 **현재 사이클 진행 상황**: 2015년 12월 저점($1,050) 대비 현재 **{g_c3.iloc[-1]:.0f}** (약 {g_c3.iloc[-1]/100:.1f}배)
                - 1968-80 사이클: 12년간 **약 24배** 상승 (인플레·스태그플레이션·닉슨 달러금태환 중지)
                - 1999-2011 사이클: 12년간 **약 6.6배** 상승 (닷컴붕괴·9/11·금융위기)
                - 2015~현재: 약 {(g_c3.iloc[-1]/100):.1f}배 진행 중
                """)

    with tab2:
        cm={"금":"GC=F","은":"SI=F","WTI원유":"CL=F","구리":"HG=F","천연가스":"NG=F"}
        cd={}
        for n,t in cm.items():
            d=yfd(t,"1y")
            if len(d)>0: cd[n]=(d['Close']/d['Close'].iloc[0]-1)*100
        if cd: st.plotly_chart(lchart(cd,"원자재 1년 퍼포먼스",ya="누적수익률 (%)",src="Yahoo Finance (COMEX/NYMEX)",zero=True),use_container_width=True)
        st.markdown("### Gold → Copper → Energy 순환")
        rt={"금광주(GDX)":"GDX","구리광산(COPX)":"COPX","에너지(XLE)":"XLE"}
        rd={}
        for n,t in rt.items():
            d=yfd(t,"5y")
            if len(d)>0: rd[n]=(d['Close']/d['Close'].iloc[0]-1)*100
        if rd: st.plotly_chart(lchart(rd,"Gold → Copper → Energy (5년 순환)",ya="누적수익률 (%)",src="Yahoo Finance (GDX, COPX, XLE)",zero=True),use_container_width=True)

    with tab3:
        o=yfd("CL=F","5y")
        if len(o)>0:
            fig=lchart({"WTI 원유":o['Close']},"WTI 원유 선물 (5년)",ya="USD / 배럴",src="Yahoo Finance (CL=F, NYMEX)")
            fig.add_hline(y=50,line_dash="dot",line_color=C['accent'],annotation_text="평균 생산비 ~$50/bbl",annotation_font_size=9)
            fig.add_hline(y=30,line_dash="dot",line_color=C['sub'],annotation_text="OPEC 생산비 ~$30/bbl",annotation_font_size=9)
            fig.add_hline(y=80,line_dash="dot",line_color=C['red'],annotation_text="고점 구간 $80+",annotation_font_size=9)
            st.plotly_chart(fig,use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            # WTI vs Brent
            brent = yfd("BZ=F", "5y")
            if len(brent) > 0 and len(o) > 0:
                fig = lchart({
                    "WTI (미국)": o['Close'],
                    "Brent (유럽)": brent['Close']
                }, "WTI vs Brent 원유 가격 비교", ya="USD / 배럴",
                src="Yahoo Finance (CL=F, BZ=F)")
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            ng = yfd("NG=F", "2y")
            if len(ng) > 0:
                fig = lchart({"천연가스": ng['Close']},
                    "미국 천연가스 (Henry Hub)", ya="USD / MMBtu",
                    src="Yahoo Finance (NG=F, NYMEX)")
                st.plotly_chart(fig, use_container_width=True)

        # OPEC production data
        st.markdown("### 🛢️ OPEC 원유 생산량 추이")
        st.caption("FRED + EIA 데이터")

        c1, c2 = st.columns(2)
        with c1:
            # OPEC crude production (FRED has WTI production data)
            opec = fred("POILBREUSDM", "2018-01-01")  # Brent price as proxy
            global_prod = fred("IPG211111CN", "2010-01-01")  # US crude oil production
            if len(global_prod) > 0:
                fig = lchart({"미국 원유 생산": global_prod},
                    "미국 원유 생산 지수 (셰일 생산)",
                    ya="지수 (2012=100)",
                    src="FRED (IPG211111CN, 미 에너지부)")
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            # US crude oil stocks
            stocks = fred("WCESTUS1", "2018-01-01")
            if len(stocks) > 0:
                fig = lchart({"미국 원유 재고": stocks},
                    "미국 상업용 원유 재고 (주간)",
                    ya="재고 (천 배럴)",
                    src="FRED (WCESTUS1, 미 EIA)")
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        ### 📌 원유 투자 포인트
        - **생산비 하한선 $50/bbl** = WTI가 이 아래로 지속되면 생산 감소 → 반등 가능성
        - **OPEC 감산** = 가격 지지 신호
        - **미국 셰일 생산** = 주요 공급 충격 요인
        - **중동 지정학 리스크** = 단기 급등 트리거
        """)

elif page == "📊 크레딧 & 채권":
    st.title("📊 크레딧 & 채권")
    c1,c2=st.columns(2)
    with c1:
        h=fred("BAMLH0A0HYM2","2005-01-01")
        if len(h)>0:
            fig=lchart({"HY OAS":h},"하이일드 크레딧 스프레드 (ICE BofA HY OAS)",ya="스프레드 (%pt)",src="FRED (BAMLH0A0HYM2)")
            fig.add_hline(y=5,line_dash="dash",line_color=C['accent'],annotation_text="경고 5%",annotation_font_size=9)
            fig.add_hline(y=8,line_dash="dash",line_color=C['red'],annotation_text="위기 8%",annotation_font_size=9)
            st.plotly_chart(fig,use_container_width=True)
    with c2:
        ig=fred("BAMLC0A0CM","2005-01-01")
        if len(ig)>0: st.plotly_chart(lchart({"IG OAS":ig},"투자등급 크레딧 스프레드 (ICE BofA Corp OAS)",ya="스프레드 (%pt)",src="FRED (BAMLC0A0CM)"),use_container_width=True)
    st.markdown("### 미국채 금리 커브")
    ms={"3M":"DGS3MO","1Y":"DGS1","2Y":"DGS2","5Y":"DGS5","10Y":"DGS10","30Y":"DGS30"}
    rs={}
    for n,c2 in ms.items():
        r=fred(c2,"2025-01-01")
        if len(r)>0: rs[n]=r.iloc[-1]
    if rs:
        fig=go.Figure(go.Scatter(x=list(rs.keys()),y=list(rs.values()),mode='lines+markers+text',
            line=dict(color=C['blue'],width=3),marker=dict(size=10,color=C['accent']),
            text=[f"{v:.2f}%" for v in rs.values()],textposition="top center",textfont=dict(size=10,color=C['white'])))
        layout(fig,"현재 미국채 금리 커브",ya="금리 (%)",src="FRED (미 재무부)")
        st.plotly_chart(fig,use_container_width=True)

elif page == "📅 시즌성 & 사이클":
    st.title("📅 시즌성 & 사이클")
    tab1,tab2=st.tabs(["월별 시즌성","대통령 사이클"])
    with tab1:
        ar,wr=calc_seasonality()
        mo=['1월','2월','3월','4월','5월','6월','7월','8월','9월','10월','11월','12월']
        c1,c2=st.columns(2)
        with c1:
            cols=[C['green'] if v>=0 else C['red'] for v in ar.values]
            fig=go.Figure(go.Bar(x=mo,y=ar.values,marker_color=cols,text=[f"{v:+.2f}%" for v in ar.values],textposition='outside',textfont=dict(size=10)))
            layout(fig,"S&P 500 월별 평균수익률 (1990~)",ya="평균수익률 (%)",src="Yahoo Finance (^GSPC) 자체계산")
            st.plotly_chart(fig,use_container_width=True)
        with c2:
            cols=[C['green'] if w>=60 else C['accent'] if w>=50 else C['red'] for w in wr.values]
            fig=go.Figure(go.Bar(x=mo,y=wr.values,marker_color=cols,text=[f"{v:.0f}%" for v in wr.values],textposition='outside',textfont=dict(size=10)))
            layout(fig,"S&P 500 월별 승률 (1990~)",ya="승률 (%)",src="Yahoo Finance (^GSPC) 자체계산")
            st.plotly_chart(fig,use_container_width=True)
        cm=datetime.now().month
        st.success(f"📅 현재 {cm}월 | 평균: {ar.iloc[cm-1]:+.2f}% | 승률: {wr.iloc[cm-1]:.0f}%")
    with tab2:
        pc=calc_pres_cycle()
        cols=[C['teal'],C['red'],C['green'],C['accent']]
        fig=go.Figure(go.Bar(x=pc.index,y=pc.values,marker_color=cols,text=[f"{v:.1f}%" for v in pc.values],textposition='outside',textfont=dict(size=11)))
        layout(fig,"대통령 사이클별 S&P 500 평균 연간수익률 (1950~)",ya="평균수익률 (%)",src="Yahoo Finance (^GSPC) 자체계산")
        st.plotly_chart(fig,use_container_width=True)

elif page == "🎯 섹터 로테이션":
    st.title("🎯 섹터 로테이션")
    per=st.selectbox("기간",["1mo","3mo","6mo","1y"],index=2,key="sr")
    sm={'에너지(XLE)':'XLE','소재(XLB)':'XLB','산업재(XLI)':'XLI','소비재(XLY)':'XLY',
        '필수소비(XLP)':'XLP','헬스케어(XLV)':'XLV','금융(XLF)':'XLF','IT(XLK)':'XLK',
        '통신(XLC)':'XLC','유틸리티(XLU)':'XLU','부동산(XLRE)':'XLRE'}
    rets={}
    for n,t in sm.items():
        d=yfd(t,per)
        if len(d)>1: rets[n]=((d['Close'].iloc[-1]/d['Close'].iloc[0])-1)*100
    if rets:
        sr=dict(sorted(rets.items(),key=lambda x:x[1]))
        st.plotly_chart(hbar(list(sr.keys()),list(sr.values()),f"섹터별 수익률 ({per})",src="Yahoo Finance (SPDR ETF)",h=450),use_container_width=True)
    st.markdown("### 🔑 3대 핵심 변수")
    st.caption("금리 → IT/REIT | 경기 → 소비재/산업재 | 인플레 → 에너지/소재")
    c1,c2,c3=st.columns(3)
    with c1:
        st.markdown("**📉 변수1: 금리**")
        dg=fred("DGS10","2024-01-01")
        if len(dg)>0:
            cur,prev=dg.iloc[-1],dg.iloc[-30] if len(dg)>30 else dg.iloc[0]
            st.metric("10Y 국채 (FRED DGS10)",f"{cur:.2f}%",f"{cur-prev:+.2f}%pt")
            st.caption("IT/REIT 유리 ✅" if cur<prev else "금융주 유리 📈")
    with c2:
        st.markdown("**📊 변수2: 경기**")
        um=fred("UMCSENT","2024-01-01")
        if len(um)>0:
            cur,prev=um.iloc[-1],um.iloc[-3] if len(um)>3 else um.iloc[0]
            st.metric("소비자신뢰 (FRED UMCSENT)",f"{cur:.1f}",f"{cur-prev:+.1f}")
            st.caption("소비재 유리 ✅" if cur>prev else "디펜시브 유리 🛡️")
    with c3:
        st.markdown("**🔥 변수3: 인플레**")
        be=fred("T10YIE","2024-01-01")
        if len(be)>0:
            cur,prev=be.iloc[-1],be.iloc[-30] if len(be)>30 else be.iloc[0]
            st.metric("기대인플레 (FRED T10YIE)",f"{cur:.2f}%",f"{cur-prev:+.2f}%pt")
            st.caption("에너지/소재 유리 🛢️" if cur>prev else "성장주 유리 💻")

elif page == "🌍 글로벌 자산 수익률":
    st.title("🌍 글로벌 주요 자산 수익률")
    st.caption("글로벌 주요 자산 수익률 비교 | Yahoo Finance 실시간")
    yr=st.selectbox("비교",["올해 YTD","2025년","2024년"],index=0)
    ps=f"{datetime.now().year}-01-01" if yr=="올해 YTD" else "2025-01-01" if yr=="2025년" else "2024-01-01"
    assets={"S&P 500":"^GSPC","NASDAQ":"^IXIC","다우30":"^DJI","Russell 2000":"^RUT",
        "TOPIX":"^TOPX","닛케이225":"^N225","DAX":"^GDAXI","FTSE":"^FTSE",
        "상해종합":"000001.SS","SENSEX":"^BSESN","보베스파":"^BVSP",
        "금(Gold)":"GC=F","은(Silver)":"SI=F","구리":"HG=F","WTI원유":"CL=F","천연가스":"NG=F",
        "DXY달러":"DX-Y.NYB","유로/달러":"EURUSD=X","달러/엔":"JPY=X",
        "미국채20Y+(TLT)":"TLT","비트코인":"BTC-USD"}
    rl=[]
    for n,t in assets.items():
        try:
            d=yf.download(t,start=ps,progress=False)
            if isinstance(d.columns,pd.MultiIndex): d.columns=d.columns.get_level_values(0)
            if len(d)>1: rl.append({"자산":n,"티커":t,"수익률":((d['Close'].iloc[-1]/d['Close'].iloc[0])-1)*100})
        except: pass
    if rl:
        df=pd.DataFrame(rl).sort_values("수익률",ascending=True)
        fig=go.Figure(go.Bar(y=[f"{r['자산']}  ({r['티커']})" for _,r in df.iterrows()],
            x=df['수익률'],orientation='h',
            marker_color=[C['green'] if v>=0 else C['red'] for v in df['수익률']],
            text=[f"{v:+.1f}%" for v in df['수익률']],textposition='outside',textfont=dict(size=9)))
        layout(fig,f"글로벌 자산 수익률 비교 ({yr})",src="Yahoo Finance 실시간",h=max(500,len(df)*25))
        fig.update_layout(xaxis=dict(title="수익률 (%)",side="top"),margin=dict(l=200,r=80,t=50,b=60))
        st.plotly_chart(fig,use_container_width=True)
        st.caption(f"총 {len(df)}개 자산 | 최고: {df.iloc[-1]['자산']} ({df.iloc[-1]['수익률']:+.1f}%) | 최저: {df.iloc[0]['자산']} ({df.iloc[0]['수익률']:+.1f}%)")

st.markdown("---")
st.markdown("<div style='text-align:center;color:#8899AA;font-size:11px;'>📊 <b>Everybody Investment</b> · 중요투자 데이터 대시보드<br>출처: FRED · Yahoo Finance · ICE BofA · COMEX/NYMEX | 정보 제공 목적, 투자 권유 아님</div>",unsafe_allow_html=True)
