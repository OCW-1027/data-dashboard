# 📊 에모리 스타일 투자 대시보드

## 개요
에모리(江守哲) 미국주식투자채널에서 사용하는 데이터 소스 23개를 통합한 Streamlit 대시보드입니다.

## 🚀 빠른 시작

### 1단계: 환경 설정
```bash
# Python 3.10+ 필요
pip install -r requirements.txt
```

### 2단계: FRED API Key 발급 (무료)
1. https://fred.stlouisfed.org/docs/api/api_key.html 접속
2. 회원가입 후 API Key 발급 (무료, 하루 1,000회)
3. 대시보드 사이드바에서 입력하거나, app.py의 FRED_API_KEY 변수에 직접 입력

### 3단계: 실행
```bash
streamlit run app.py
```
브라우저에서 http://localhost:8501 접속

---

## 📑 대시보드 구성 (8개 페이지)

### 🏠 종합 대시보드
- 주요 6개 지수 실시간 현황 (S&P500, NASDAQ, 금, 원유, 10Y금리, DXY)
- S&P500 & 금 가격 차트
- 일드커브 & HY 스프레드
- 섹터 ETF 6개월 퍼포먼스

### 📈 거시경제 지표
- 고용: 실업률, 신규실업수당, 소비자신뢰지수
- 인플레이션: CPI YoY, PPI YoY, 기대인플레이션(BEI)
- 금리: FF금리, 일드커브(10Y-2Y), 10년 국채금리

### 💰 시장 & 밸류에이션
- 주요 지수 상대 퍼포먼스 (S&P500, NASDAQ, 다우, Russell 2000)
- 글로벌 비교 (미국, 유럽, 일본, 신흥국, 인도)
- 밸류에이션: CAPE Ratio, Forward PE, Buffett Indicator, ERP

### 🔄 자금흐름 & 심리
- FINRA 신용거래잔고 (마진 데이터)
- VIX 공포지수
- Fear & Greed Index, AAII 심리, Put/Call Ratio 링크

### 🥇 금 & 원자재
- 금 가격 장기 추이 (기간 선택 가능)
- 금 vs S&P500, 금광주 vs 금 ETF 비교
- 원자재 상대 퍼포먼스 (금, 은, 원유, 구리, 천연가스)
- Gold → Copper → Energy 순환 패턴 (에모리 핵심 테제)

### 📊 크레딧 & 채권
- 하이일드/투자등급 크레딧 스프레드
- 미국채 금리 커브 (3M~30Y)

### 📅 시즌성 & 사이클
- S&P500 월별 시즌성 (평균 수익률 & 승률, 1990년~ 자체 계산)
- 대통령 사이클 (1950년~ 자체 계산)

### 🎯 섹터 로테이션
- 11개 GICS 섹터 ETF 수익률 비교 (기간 선택)
- 에모리 3대 변수 모니터 (금리 → IT/REIT, 경기 → 소비재, 인플레 → 에너지)

---

## 📋 데이터 소스 전체 목록 (23개)

### 자동 수집 (API/라이브러리)
| # | 데이터 | 출처 | 수집 방법 | FRED 코드 |
|---|--------|------|----------|----------|
| 1 | 실업률 | FRED | API | UNRATE |
| 2 | 신규실업수당 | FRED | API | ICSA |
| 3 | 소비자신뢰지수 | FRED | API | UMCSENT |
| 4 | CPI | FRED | API | CPIAUCSL |
| 5 | PPI | FRED | API | PPIACO |
| 6 | 기대인플레이션 | FRED | API | T10YIE |
| 7 | FF금리 | FRED | API | FEDFUNDS |
| 8 | 일드커브 10Y-2Y | FRED | API | T10Y2Y |
| 9 | 10Y 국채금리 | FRED | API | DGS10 |
| 10 | HY 크레딧 스프레드 | FRED | API | BAMLH0A0HYM2 |
| 11 | IG 크레딧 스프레드 | FRED | API | BAMLC0A0CM |
| 12 | S&P500 / 섹터ETF | Yahoo Finance | yfinance | - |
| 13 | 금/은/원유/구리 | Yahoo Finance | yfinance | - |
| 14 | DXY 달러인덱스 | Yahoo Finance | yfinance | - |
| 15 | 글로벌지수 (TOPIX, EEM 등) | Yahoo Finance | yfinance | - |
| 16 | VIX 공포지수 | Yahoo Finance | yfinance | - |

### 수동/반자동 수집
| # | 데이터 | 출처 | URL |
|---|--------|------|-----|
| 17 | 신용거래잔고 | FINRA | finra.org/investors/margin-statistics |
| 18 | Shiller CAPE | Robert Shiller | econ.yale.edu/~shiller |
| 19 | Forward PE | FactSet | factset.com (주간 PDF) |
| 20 | ERP | Damodaran | pages.stern.nyu.edu/~adamodar |
| 21 | 금 리서치 전체 | WGC Gold Hub | gold.org/goldhub |

### 자체 계산
| # | 데이터 | 원본 | 계산 방법 |
|---|--------|------|----------|
| 22 | 월별 시즌성 | Yahoo (^GSPC) | 1990년~ 월별 수익률/승률 집계 |
| 23 | 대통령 사이클 | Yahoo (^GSPC) | 1950년~ 4년 사이클별 수익률 집계 |

---

## 🔧 커스터마이징

### FRED API Key 교체
app.py 상단의 `FRED_API_KEY`를 본인 키로 교체:
```python
FRED_API_KEY = "여기에_본인_키_입력"
```

### 데이터 자동 갱신
- `@st.cache_data(ttl=3600)` : 1시간 캐시 (기본)
- ttl=86400 으로 변경하면 24시간 캐시
- 매일 자동 실행: cron 또는 Streamlit Cloud 활용

### 배포 옵션
1. **로컬**: `streamlit run app.py`
2. **Streamlit Cloud**: github에 push → share.streamlit.io에서 무료 배포
3. **자체 서버**: Docker 또는 VPS ($5/월)

---

## 📌 향후 확장 계획
- [ ] FINRA 마진 데이터 자동 스크래핑
- [ ] Fear & Greed Index 자동 수집
- [ ] AAII 심리 데이터 자동 수집
- [ ] WGC 금 리서치 데이터 자동 다운로드
- [ ] Shiller CAPE 자동 업데이트
- [ ] 알림 기능 (일드커브 역전, VIX 급등 등)
- [ ] 일본 시장 (TOPIX-17) 탭 추가
- [ ] PDF 리포트 자동 생성
