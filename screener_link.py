# -*- coding: utf-8 -*-
"""
screener_link.py — 섹터 로테이션 → 종목 스크리너 연결
======================================================
daiji-data(거시·섹터 판단)에서 고른 섹터를,
JPN-STOCK-SCREENER(개별 종목)의 업종 필터가 걸린 화면으로 바로 잇는다.

사용법 (pages/섹터_로테이션.py 등에서):

    from screener_link import sector_links, render_sector_links

    # ① 섹터별 수익률 차트 아래에 링크 묶음 표시
    render_sector_links(st, ["IT(XLK)", "금융(XLF)", "헬스케어(XLV)"])

    # ② 또는 URL만 필요할 때
    links = sector_links("IT(XLK)")        # {'일본': 'https://...', '한국': ..., '미국': ...}

스크리너는 URL 쿼리로 필터를 받는다 (v27부터):
    ?sector=전자·반도체        업종 필터
    ?min=10                    거래대금 하한
    ?tab=grow                  탭 (all/short/long/fund/grow/sup/mine/dis)
    ?sig=13,14&and=1           시그널 비트 + AND 모드
    ?sort=12&dir=desc          정렬
"""
from urllib.parse import quote

BASE = "https://stock-screener-ev3.pages.dev"     # Cloudflare (GitHub Pages도 동일 구조)
MARKETS = [("일본", "jp"), ("한국", "kr"), ("미국", "us")]

# SPDR 11섹터 ETF → 스크리너 업종명 (한 섹터가 여러 업종에 걸치면 대표 1개)
# 스크리너 업종은 3개 시장 공통 20종.
SECTOR_MAP = {
    "XLK":  ("IT", "전자·반도체"),          # 기술 — 반도체가 핵심
    "XLF":  ("금융", "금융"),
    "XLV":  ("헬스케어", "제약·바이오"),
    "XLE":  ("에너지", "에너지"),
    "XLI":  ("산업재", "기계·제조"),
    "XLB":  ("소재", "소재·금속"),
    "XLY":  ("소비재", "내구소비재"),
    "XLP":  ("필수소비", "필수소비재"),
    "XLU":  ("유틸리티", "유틸리티"),
    "XLRE": ("부동산", "상업서비스"),        # 스크리너에 부동산 업종이 없어 근사
    "XLC":  ("통신", "통신"),
}
# 보조 업종 — "관련 업종 더 보기"에 함께 노출
SECTOR_EXTRA = {
    "XLK": ["IT서비스·SW"],
    "XLV": ["의료서비스"],
    "XLY": ["소매", "소비자서비스"],
    "XLI": ["산업서비스", "운송"],
    "XLB": ["화학·공정"],
    "XLP": ["유통"],
}

MIN_TURNOVER = {"jp": 10, "kr": 10, "us": 5}   # 유동성 하한 (억엔·억원·$M)


def _etf_code(label):
    """'IT(XLK)' · 'XLK' · 'IT' 무엇이 와도 ETF 코드로 정규화."""
    s = str(label).upper()
    for code in SECTOR_MAP:
        if code in s:
            return code
    for code, (ko, _) in SECTOR_MAP.items():
        if ko.upper() in s:
            return code
    return None


def sector_url(label, market="jp", tab=None, extra_sector=None):
    """섹터 라벨 → 스크리너 URL. 업종을 못 찾으면 필터 없이 시장 첫 화면."""
    code = _etf_code(label)
    sector = extra_sector or (SECTOR_MAP[code][1] if code else None)
    q = []
    if sector:
        q.append("sector=" + quote(sector))
    q.append(f"min={MIN_TURNOVER.get(market, 10)}")
    if tab:
        q.append(f"tab={tab}")
    return f"{BASE}/{market}/?" + "&".join(q)


def sector_links(label, tab=None):
    """{'일본': url, '한국': url, '미국': url}"""
    return {name: sector_url(label, mk, tab) for name, mk in MARKETS}


def render_sector_links(st, labels=None, tab=None, title="이 섹터의 종목 보기"):
    """Streamlit에 섹터별 링크 버튼을 렌더링.

    st       : streamlit 모듈
    labels   : ['IT(XLK)', '금융(XLF)', ...]  (섹터 차트에 쓴 라벨 그대로)
    tab      : 스크리너 진입 탭. 예) 'grow'(성장주) 'sup'(수급) 'long'(중장기)
    """
    if labels is None:                      # 기본값: 11섹터 전부
        labels = list(SECTOR_MAP.keys())
    st.markdown(f"#### 🔗 {title}")
    st.caption("거시·섹터에서 방향을 잡고 → 그 섹터의 개별 종목으로. "
               "유동성 하한이 걸린 채로 열립니다.")
    for label in labels:
        code = _etf_code(label)
        if not code:
            continue
        ko, main = SECTOR_MAP[code]
        cols = st.columns([2, 1, 1, 1])
        cols[0].markdown(f"**{ko}** · `{main}`")
        for i, (name, mk) in enumerate(MARKETS, start=1):
            cols[i].link_button(name, sector_url(label, mk, tab), use_container_width=True)
        extras = SECTOR_EXTRA.get(code, [])
        if extras:
            links = " · ".join(
                f"[{e}]({sector_url(label, 'jp', tab, extra_sector=e)})" for e in extras)
            st.caption(f"　└ 관련 업종: {links}")


def render_quick_links(st):
    """섹터와 무관한 상시 링크 — 사이드바나 페이지 하단용."""
    st.markdown("#### 🔗 종목 스크리너")
    rows = [
        ("성장주", "grow", "매출·이익이 함께 늘고 있는 종목"),
        ("수급", "sup", "숏스퀴즈·손바뀜·바닥매집 신호"),
        ("중장기 시그널", "long", "추세 전환 구간"),
        ("가치·펀더", "fund", "저평가·고배당·우량"),
    ]
    for ko, tab, desc in rows:
        cols = st.columns([2, 1, 1, 1])
        cols[0].markdown(f"**{ko}**  \n<small>{desc}</small>", unsafe_allow_html=True)
        for i, (name, mk) in enumerate(MARKETS, start=1):
            cols[i].link_button(
                name, f"{BASE}/{mk}/?tab={tab}&min={MIN_TURNOVER.get(mk,10)}",
                use_container_width=True)
