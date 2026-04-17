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
def layout(fig, title, yaxis="", src="", h=400, xrot=0):
    ann = []
    if src:
        ann.append(dict(text=f"📊 출처: {src}", xref="paper", yref="paper",
            x=0, y=-0.28, showarrow=False, font=dict(size=9, color=C['sub'])))
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=14, color=C['white']), x=0.01, y=0.98),
        paper_bgcolor=C['card'], plot_bgcolor=C['bg'],
        font=dict(color=C['text'], size=11),
        xaxis=dict(gridcolor=C['grid'], tickangle=xrot, tickfont=dict(size=10)),
        yaxis=dict(title=dict(text=yaxis, font=dict(size=11)), gridcolor=C['grid'], tickfont=dict(size=10)),
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
        "🏠 종합 대시보드", "📈 거시경제 지표", "💰 시장 밸류에이션",
        "🔄 자금흐름 & 심리", "🥇 금·원자재·에너지", "📊 크레딧 & 채권",
        "📅 시즌성 & 사이클", "🎯 섹터 로테이션", "🌍 글로벌 자산 수익률",
    ], index=0)
    st.markdown("---")
    st.caption(f"업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ============================================================
if page == "🏠 종합 대시보드":
    st.title("📊 중요투자 데이터 대시보드")
    st.caption("Everybody Investment | 실시간 글로벌 시장 모니터링")
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    for col,(nm,tk,u) in zip([c1,c2,c3,c4,c5,c6],[
        ("S&P 500","^GSPC","pt"),("NASDAQ","^IXIC","pt"),("금(Gold)","GC=F","$/oz"),
        ("WTI원유","CL=F","$/bbl"),("미국10Y","^TNX","%"),("달러DXY","DX-Y.NYB","pt")]):
        with col:
            d=yfd(tk,"5d")
            if len(d)>=2:
                cur,prev=d['Close'].iloc[-1],d['Close'].iloc[-2]
                chg=((cur/prev)-1)*100
                if u=="%": col.metric(nm, f"{cur:.2f}%", f"{chg:+.2f}%")
                elif cur>1000: col.metric(nm, f"{cur:,.0f}", f"{chg:+.2f}%")
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
            st.plotly_chart(fig,use_container_width=True)

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
    st.caption("영상 '主要資産のリターン' 스타일 | Yahoo Finance 실시간")
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
