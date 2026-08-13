# -*- coding: utf-8 -*-
"""분석 결과를 비전공자용 PDF 보고서(HTML 소스)로 조립한다."""
import base64
import json
from pathlib import Path

# 이 스크립트는 scripts/에 있고, 그림/출력은 report/ 아래에 있다.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = PROJECT_ROOT / "report"
FIG_DIR = REPORT_DIR / "figures"

manifest = json.load(open(FIG_DIR / "manifest.json", encoding="utf-8"))
FIGS = {i + 1: m["file"] for i, m in enumerate(manifest)}


def b64(fname):
    p = FIG_DIR / fname
    return base64.b64encode(p.read_bytes()).decode("ascii")


def img(n, caption, width="92%"):
    return f"""
    <div class="figure">
      <img src="data:image/png;base64,{b64(FIGS[n])}" style="width:{width};" />
      <div class="fig-caption">그림 {n}. {caption}</div>
    </div>"""


def note(text):
    return f'<div class="note">💡 <b>쉽게 말하면</b> — {text}</div>'


def warn(text):
    return f'<div class="warn">⚠️ {text}</div>'


CSS = """
@page { size: A4; margin: 22mm 18mm 20mm 18mm; }
* { box-sizing: border-box; }
body {
  font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
  color: #1f2430; line-height: 1.68; font-size: 13.5px;
  background: #ffffff; margin: 0;
}
h1, h2, h3, h4 { font-family: 'Malgun Gothic', 'Segoe UI', sans-serif; color: #1a1f36; }
.cover {
  height: 253mm; display: flex; flex-direction: column; justify-content: center;
  align-items: flex-start; page-break-after: always;
  background: linear-gradient(160deg, #eef1ff 0%, #ffffff 55%);
  padding: 0 8mm;
}
.cover .kicker { color: #4C6FFF; font-weight: 700; letter-spacing: 2px; font-size: 13px; margin-bottom: 14px; }
.cover h1 { font-size: 34px; margin: 0 0 10px 0; line-height: 1.35; }
.cover .subtitle { font-size: 16px; color: #4b5266; margin-bottom: 36px; }
.cover .meta { font-size: 12.5px; color: #6b7280; border-top: 1px solid #d8dcf0; padding-top: 14px; margin-top: 10px; width: 100%; max-width: 480px; }
.cover .meta div { margin-bottom: 4px; }
.cover .badges { display: flex; gap: 8px; margin-top: 22px; flex-wrap: wrap; }
.cover .badge { background: #4C6FFF14; color: #4C6FFF; border: 1px solid #4C6FFF33; padding: 5px 12px; border-radius: 20px; font-size: 11.5px; font-weight: 600; }

section { page-break-before: always; padding-top: 2mm; }
section:first-of-type { page-break-before: auto; }

.section-head { display:flex; align-items:baseline; gap:10px; border-bottom: 3px solid #4C6FFF; padding-bottom: 10px; margin-bottom: 18px; }
.section-num { font-size: 26px; font-weight: 800; color: #4C6FFF; }
.section-title { font-size: 20px; font-weight: 800; color: #1a1f36; }

h3 { font-size: 15.5px; margin-top: 22px; margin-bottom: 8px; color: #2b3363; border-left: 4px solid #00B8A9; padding-left: 8px; }
h4 { font-size: 14px; margin-top: 14px; margin-bottom: 6px; color: #444d6e; }
p { margin: 6px 0 10px 0; }

.note { background: #eef6ff; border: 1px solid #cfe3ff; border-radius: 8px; padding: 9px 13px; margin: 10px 0; font-size: 12.5px; color: #26406b; break-inside: avoid; }
.warn { background: #fff4e8; border: 1px solid #ffd9a8; border-radius: 8px; padding: 9px 13px; margin: 10px 0; font-size: 12.5px; color: #7a4a12; break-inside: avoid; }
.persona { background: #f6f5ff; border: 1px solid #ded9ff; border-radius: 10px; padding: 14px 16px; margin: 12px 0; break-inside: avoid; }
.persona b { color: #5b4fd6; }

.figure { margin: 14px 0 18px 0; text-align: center; break-inside: avoid; }
.figure img { border: 1px solid #e7e9f2; border-radius: 8px; box-shadow: 0 2px 10px rgba(30,40,90,0.06); }
.fig-caption { font-size: 11.5px; color: #6b7280; margin-top: 6px; }

table { width: 100%; border-collapse: collapse; margin: 10px 0 16px 0; font-size: 12px; break-inside: avoid; }
th, td { border: 1px solid #e3e6f0; padding: 6px 8px; text-align: center; }
th { background: #4C6FFF; color: white; font-weight: 700; }
tr:nth-child(even) td { background: #f7f8fc; }
td.left, th.left { text-align: left; }
.best-row td { background: #e8fff8 !important; font-weight: 700; }

.kpi-row { display: flex; gap: 10px; margin: 14px 0 18px 0; }
.kpi { flex: 1; background: #fbfbff; border: 1px solid #e7e9f7; border-radius: 10px; padding: 12px 10px; text-align: center; break-inside: avoid; }
.kpi .v { font-size: 19px; font-weight: 800; color: #4C6FFF; }
.kpi .l { font-size: 11px; color: #6b7280; margin-top: 3px; }

.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

.step-flow { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; margin: 14px 0 20px 0; }
.step { background: #4C6FFF; color: white; padding: 9px 13px; border-radius: 8px; font-size: 12px; font-weight: 700; text-align:center; flex: 1; min-width: 80px; }
.step.alt { background: #00B8A9; }
.arrow { color: #9aa0b4; font-size: 16px; }

.tag { display:inline-block; padding: 2px 9px; border-radius: 12px; font-size: 11px; font-weight: 700; }
.tag.reject { background:#ffe3e3; color:#c92a2a; }
.tag.partial { background:#fff3bf; color:#8a6d00; }

.pagefoot { text-align:center; color:#aab0c0; font-size:10.5px; margin-top: 30px; }
ul, ol { margin: 4px 0 10px 22px; padding:0; }
li { margin-bottom: 4px; }
.small { font-size: 11.5px; color:#6b7280; }
.conclusion-box { background:#1a1f36; color:#fff; border-radius: 12px; padding:18px 20px; margin: 16px 0; break-inside: avoid; }
.conclusion-box b { color:#8ecbff; }
"""

# ---------------------------------------------------------------------
cover = f"""
<div class="cover">
  <div class="kicker">DATA-DRIVEN USED-CAR ACQUISITION STRATEGY REPORT</div>
  <h1>인도 중고차 매입가 예측 &<br/>비즈니스 전략 분석 보고서</h1>
  <div class="subtitle">지역 소득 데이터와 중고차 거래 데이터를 결합한 머신러닝 기반 매입가 산정 및 지역/소득 영향력 검증</div>
  <div class="badges">
    <span class="badge">7개 ML 모델 비교</span>
    <span class="badge">SHAP·통계적 가설검증</span>
    <span class="badge">Bid Price 자동산출</span>
  </div>
  <div class="meta">
    <div><b>분석 대상</b> : Car.csv(중고차 거래 7,253건) · 지역별소득수준_krw.csv(11개 도시 · 2011~2020)</div>
    <div><b>작성일</b> : 2026-08-13</div>
    <div><b>작성</b> : AI 데이터 분석팀 (포스코 청년 AI·Big Data 아카데미 기반 분석 파이프라인)</div>
  </div>
</div>
"""

# ---------------------------------------------------------------------
sec1 = f"""
<section>
  <div class="section-head"><div class="section-num">01</div><div class="section-title">문제 정의 및 가설 수립</div></div>

  <div class="persona">
    <b>👤 분석 페르소나</b><br/>
    본 보고서는 <b>인도 중고차 매입 전문 딜러(온라인·오프라인 병행)이자 데이터 사이언티스트</b>의 관점에서 작성되었습니다.
    인도는 지역별 소득 수준·도로 환경·연료 정책 차이가 커서, "이 차를 얼마에 사들여야 손해를 보지 않을지" 판단이 지역마다 크게 달라질 수 있습니다.
    본 분석은 이 매입가 산정 문제를 데이터로 풀어내는 것을 목표로 합니다.
  </div>

  <h3>1) 문제 정의</h3>
  <p>중고차 매입 딜러는 매입 시점에 정확한 "적정 매입가"를 알지 못하면 두 가지 방식으로 손해를 봅니다.</p>
  <ul>
    <li><b>너무 비싸게 사면</b> → 되팔 때 마진이 남지 않아 손실</li>
    <li><b>너무 싸게 불러 놓치면</b> → 경쟁 딜러에게 매물을 빼앗겨 재고 확보 실패</li>
  </ul>
  <p>이 문제를 더 어렵게 만드는 두 가지 불확실성이 있습니다.</p>
  <ol>
    <li><b>지역/소득 불확실성</b>: 도시(지역)나 그 지역의 평균 소득 수준이 중고차 가격에 실제로 영향을 주는지, 준다면 얼마나 주는지 감으로만 판단하고 있음</li>
    <li><b>비선형 감가 불확실성</b>: 주행거리·연식이 늘어날수록 가격이 떨어지는 건 당연하지만, "얼마나 빠르게" 떨어지는지 구간별로 다르게 나타나 예측이 어려움</li>
  </ol>

  {note("한마디로: '어느 지역에서, 어떤 차를, 얼마에 사야 안전하게 남는 장사가 될까?'를 감이 아니라 데이터로 계산하는 것이 이번 분석의 목표입니다.")}

  <h3>2) 가설 수립 — 귀무가설(H0)과 대립가설(H1)</h3>
  <p>
    통계 검증에서는 먼저 "효과가 없다"고 가정하는 <b>귀무가설(H0)</b>을 세우고, 데이터가 이를 뒤집을 만큼 강한 증거를 보이는지 확인합니다.
    증거가 충분하면 H0을 <b>기각(reject)</b>하고, "효과가 있다"는 <b>대립가설(H1)</b>을 채택합니다.
  </p>
  {note("귀무가설(H0)은 '아무 상관 없다'는 심심한 가정, 대립가설(H1)은 '진짜 영향이 있다'는 우리가 확인하고 싶은 가정입니다. 재판에서 '유죄가 입증되기 전까지는 무죄'로 보는 것과 같은 논리입니다.")}

  <table>
    <tr><th class="left" style="width:8%">구분</th><th class="left">귀무가설(H0) — 아무 영향 없다</th><th class="left">대립가설(H1) — 유의미한 영향이 있다</th></tr>
    <tr><td><b>H0-1</b></td><td class="left">지역 소득 수준(KRW)은 중고차 거래가격과 무관하다</td><td class="left">지역 소득 수준이 높을수록 거래가격이 높다</td></tr>
    <tr><td><b>H0-2</b></td><td class="left">거래 도시(Location) 자체는 가격에 영향을 주지 않는다</td><td class="left">동일 소득 수준이라도 도시 고유 특성이 가격에 영향을 준다</td></tr>
    <tr><td><b>H0-3</b></td><td class="left">주행거리·연식에 따른 가격 하락 폭은 항상 일정하다(선형적)</td><td class="left">특정 구간(8만km·7년)을 넘으면 하락 폭이 달라진다(비선형)</td></tr>
    <tr><td><b>H0-4</b></td><td class="left">소유자 이력·연비는 가격에 영향을 주지 않는다</td><td class="left">1인 소유·우수 연비 차량은 프리미엄이 있다</td></tr>
  </table>
  <p class="small">※ 4개 세부가설을 종합해 "지역/소득/차량이력 요인은 중고차 가격과 무관하며, 매입가 산정에 굳이 반영할 필요가 없다"는 것이 이번 분석 전체의 큰 귀무가설(Global H0)입니다. 6장에서 이 큰 H0의 기각 여부를 최종 판정합니다.</p>
</section>
"""

# ---------------------------------------------------------------------
sec2 = f"""
<section>
  <div class="section-head"><div class="section-num">02</div><div class="section-title">분석 계획</div></div>

  <p>가설을 검증하고 실제로 쓸 수 있는 매입가 산정 도구를 만들기 위해, 아래 6단계로 분석을 설계했습니다.</p>

  <div class="step-flow">
    <div class="step">① 데이터 수집·확인</div><div class="arrow">→</div>
    <div class="step alt">② 전처리·병합</div><div class="arrow">→</div>
    <div class="step">③ 탐색적 분석(EDA)</div><div class="arrow">→</div>
    <div class="step alt">④ 머신러닝 모델링</div><div class="arrow">→</div>
    <div class="step">⑤ 가설 통계 검증</div><div class="arrow">→</div>
    <div class="step alt">⑥ 매입가·전략 도출</div>
  </div>

  <h3>사용한 분석 도구</h3>
  <table>
    <tr><th class="left" style="width:24%">구분</th><th class="left">사용 기법</th><th class="left">역할</th></tr>
    <tr><td>회귀모델</td><td class="left">선형회귀(OLS), Ridge</td><td class="left">가장 단순한 "기준선" 성능 측정</td></tr>
    <tr><td>트리 앙상블</td><td class="left">RandomForest, GradientBoosting</td><td class="left">비선형 패턴을 잡는 범용 모델</td></tr>
    <tr><td>고급 부스팅</td><td class="left">XGBoost, LightGBM, CatBoost</td><td class="left">최고 성능을 노리는 정밀 모델</td></tr>
    <tr><td>중요도 분석</td><td class="left">Permutation Importance, SHAP</td><td class="left">"어떤 변수가 가격을 좌우하는지" 설명</td></tr>
    <tr><td>통계 검증</td><td class="left">회귀계수 t-검정, F-검정(ANOVA류)</td><td class="left">가설의 통계적 유의성(p-value) 판정</td></tr>
  </table>

  <h3>검증 방식 및 평가 지표</h3>
  <p>모델이 "새로운 차량"을 만나도 잘 맞히는지 확인하기 위해 <b>5-fold 교차검증</b>을 사용했습니다.</p>
  {note("5-fold 교차검증: 전체 데이터를 5조각으로 나눈 뒤, 4조각으로 학습하고 나머지 1조각(모델이 한 번도 보지 못한 데이터)으로 성적을 매기는 과정을 5번 반복해 평균을 냅니다. '족집게 과외'가 아니라 '실전 모의고사'로 실력을 검증하는 방식입니다.")}
  <ul>
    <li><b>R²(결정계수)</b>: 모델이 실제 가격 변동의 몇 %를 설명하는지. 0.86이면 "86%를 설명한다"는 뜻(1.0에 가까울수록 좋음)</li>
    <li><b>RMSE</b>: 예측이 실제 가격과 평균적으로 얼마나(천원 단위) 차이 나는지(작을수록 좋음)</li>
    <li><b>MAE</b>: RMSE와 비슷하지만 큰 오차에 덜 민감한 "평균 절대 오차"</li>
  </ul>
</section>
"""

# ---------------------------------------------------------------------
sec3 = f"""
<section>
  <div class="section-head"><div class="section-num">03</div><div class="section-title">데이터 파악 및 전처리</div></div>

  <h3>1) 데이터셋 소개</h3>
  <div class="kpi-row">
    <div class="kpi"><div class="v">7,253건</div><div class="l">중고차 거래 원본 데이터</div></div>
    <div class="kpi"><div class="v">110행</div><div class="l">지역별 소득 데이터(11개 도시×10개년)</div></div>
    <div class="kpi"><div class="v">13개→32개</div><div class="l">전처리·병합 후 컬럼 수</div></div>
    <div class="kpi"><div class="v">6,200 / 1,053</div><div class="l">가격 라벨 有 / 無 (매입심사 대상)</div></div>
  </div>
  <p>
    <b>중고차 데이터</b>에는 차량명, 지역, 연식, 주행거리, 연료타입, 변속기, 소유이력, 연비, 배기량, 출력, 좌석수, 신차가격, 실제 거래가격(Price)이 담겨 있습니다.
    <b>소득 데이터</b>에는 11개 도시별로 2011~2020년 매년 평균 소득(KRW, 천원 단위)이 담겨 있습니다.
  </p>
  {img(1, "중고차 거래 데이터의 도시(Location) 수, 소득 데이터의 도시 수·주(State) 수 비교. 두 데이터셋의 '도시' 기준이 11개로 정확히 일치함을 확인했습니다.")}
  {warn("최초 분석 설계 시에는 '중고차 11개 도시 vs 소득 데이터 9개 도시'로 서로 어긋난다고 가정했지만, 실제 파일을 열어 직접 대조한 결과 소득 데이터도 도시 기준 11개로 정확히 일치했습니다(주(State) 기준으로는 9개). 가정에 의존하지 않고 실제 데이터를 검증하는 것이 데이터 분석의 기본 원칙입니다.")}

  <h3>2) 단위가 섞인 텍스트에서 숫자만 뽑아내기</h3>
  <p>
    원본 데이터에는 "26.6 kmpl", "998 CC", "58.16 bhp"처럼 <b>숫자와 단위가 한 칸에 섞여</b> 있어 컴퓨터가 그대로는 계산에 쓸 수 없습니다.
    정규식(패턴 찾기 규칙)으로 숫자만 추출했고, 연비(Mileage)는 가솔린/디젤 차량이 쓰는 "kmpl(리터당 km)"과 CNG/LPG 차량이 쓰는 "km/kg(kg당 km)" 두 단위를 같은 기준으로 맞추기 위해 <b>환산계수 1.4</b>를 곱해 통일했습니다.
  </p>
  {img(2, "숫자만 추출한 뒤의 연비(Mileage)·배기량(Engine)·출력(Power) 값 분포. 극소수 이상치(0.0 kmpl 등)는 결측으로 처리한 뒤 중앙값으로 채웠습니다.")}

  <h3>3) 지역(State)·연도(Year) 기준 정밀 데이터 결합</h3>
  <p>중고차의 거래 도시와 연식을, 소득 데이터의 도시·연도와 정확히 짝지어 결합했습니다. 짝이 맞지 않는 경우(주로 2011년 이전 연식 차량)에는 데이터가 통째로 비지 않도록 <b>해당 도시의 가장 최근 소득값(2020년)</b>으로 대체했습니다.</p>
  {img(3, "차량-소득 데이터 연도 매칭 결과. 89.3%(5,989건)는 연식과 소득 연도가 정확히 일치했고, 나머지 10.7%(1,264건)는 최신 소득값으로 대체했습니다. 완전히 값을 못 채운 건수는 0건입니다.")}

  <h3>4) 결측치 처리 및 파생변수</h3>
  <table>
    <tr><th class="left">항목</th><th>결측 건수</th><th class="left">처리 방법</th></tr>
    <tr><td class="left">연비(Mileage)</td><td>2건 + 이상치 81건</td><td class="left">중앙값(18.2 kmpl) 대체</td></tr>
    <tr><td class="left">배기량(Engine)</td><td>46건</td><td class="left">중앙값(1,493cc) 대체</td></tr>
    <tr><td class="left">출력(Power)</td><td>46건</td><td class="left">중앙값(94bhp) 대체</td></tr>
    <tr><td class="left">좌석수(Seats)</td><td>53건</td><td class="left">중앙값(5석) 대체</td></tr>
  </table>
  <p>추가로 <b>차량 나이(Age = 2020년 − 연식)</b>, <b>소유이력 순위(Owner_Rank, 1인 소유=1 ~ 4인 이상=4)</b> 두 변수를 새로 만들어 모델에 투입했습니다.</p>

  <h3>5) 목표 변수(가격) 로그 변환</h3>
  <p>
    중고차 가격은 저가 차량은 매우 많고 초고가 차량은 소수만 있는 <b>오른쪽으로 긴 꼬리 분포</b>를 가집니다(평균 14,913천원 vs 중앙값 8,815천원).
    이런 분포를 그대로 학습하면 모델이 소수의 고가 차량에 휘둘리기 쉬워, <b>자연로그 변환</b>으로 분포를 종 모양에 가깝게 만든 뒤 학습하고, 예측 후 다시 원래 단위로 되돌렸습니다.
  </p>
  {img(4, "로그 변환 전(왼쪽, 왜도 2.47)과 후(오른쪽, 왜도 0.02)의 가격 분포 비교. 변환 후 훨씬 대칭적인 종 모양이 되어 모델 학습에 유리해졌습니다.")}
</section>
"""

# ---------------------------------------------------------------------
sec4 = f"""
<section>
  <div class="section-head"><div class="section-num">04</div><div class="section-title">탐색적 데이터 분석 (EDA)</div></div>
  <p>본격적인 모델링 전에, 데이터가 실제로 어떤 패턴을 보이는지 눈으로 먼저 확인했습니다.</p>

  <h3>1) 지역 소득이 높으면 중고차도 비쌀까?</h3>
  {img(5, "도시별 중앙값 소득(KRW)과 중앙값 중고차 가격(Price)의 관계. 점 크기는 해당 도시의 거래건수입니다.")}
  <p>
    전체적으로는 소득이 높을수록 가격도 높아지는 <b>완만한 우상향 경향</b>(상관계수 r=0.39, 중간 정도의 관계)이 보입니다.
    하지만 예외가 뚜렷합니다 — <b>Delhi는 소득 1위인데 가격은 7위(중위권)</b>, 반대로 <b>Coimbatore·Kochi는 소득이 중위권인데 가격은 1·3위</b>입니다.
    즉 "소득"만으로는 설명이 부족하고, 그 도시만의 다른 특성이 함께 작용하고 있다는 신호입니다.
  </p>

  <h3>2) 도시별 가격 분포</h3>
  {img(6, "도시(Location)별 거래가격 분포(상자그림). 상자가 위에 있을수록 그 도시의 중고차가 대체로 비싸게 거래된다는 뜻입니다.")}

  <h3>3) 주행거리·연식이 늘면 가격은 어떻게 떨어질까?</h3>
  {img(7, "왼쪽: 주행거리 구간별 중앙값 가격(막대 위 숫자는 직전 구간 대비 하락률). 오른쪽: 연식 구간별 동일 분석.")}
  <p>
    <b>주행거리</b>는 8만km를 지나면서 하락률이 -18.2% → -9.6% → -4.3%로 <b>점점 완만해지는</b> 전형적인 비선형 감가 패턴을 보입니다(많이 달린 차는 "추가로 더 달린 것"에 대한 가격 민감도가 낮아짐).
    반대로 <b>연식</b>은 10년을 넘는 순간 하락률이 -43.0%로 오히려 <b>가장 크게 뛰는</b> 정반대 패턴을 보였습니다 — 10년 넘은 차는 이미 상태가 안 좋은 차들만 시장에 남아있을 가능성이 있습니다.
  </p>

  <h3>4) 소유자 이력·연료 타입별 가격</h3>
  {img(8, "왼쪽: 소유자 이력(1인/2인/3인/4인 이상)별 가격 분포. 오른쪽: 연료 타입별 가격 분포.")}

  <h3>5) 변수 간 상관관계 한눈에 보기</h3>
  {img(9, "수치형 변수들 사이의 상관관계 히트맵. 빨간색에 가까울수록 강한 양(+)의 관계, 파란색에 가까울수록 강한 음(-)의 관계입니다.")}
  {note("출력(Power_bhp)·배기량(Engine_cc)이 가격과 가장 강한 양의 관계를, 차량 나이(Age)가 가장 강한 음의 관계를 보입니다. 이는 5장 모델링 결과와도 정확히 일치합니다.")}
</section>
"""

# ---------------------------------------------------------------------
model_rows = [
    ("LightGBM", 0.8587, 6643.9, 2502.9, 0.9410, 35.4, True),
    ("XGBoost", 0.8405, 7057.7, 2594.8, 0.9475, 42.6, False),
    ("CatBoost", 0.8302, 7283.5, 2819.1, 0.9003, 23.4, False),
    ("RandomForest", 0.8281, 7326.5, 2765.1, 0.9399, 40.9, False),
    ("GradientBoosting", 0.8271, 7349.5, 2979.7, 0.8800, 16.7, False),
    ("Ridge", 0.5421, 11958.5, 4139.1, 0.5667, 2.7, False),
    ("OLS(선형회귀)", 0.5371, 12024.4, 4106.6, 0.5680, 3.4, False),
]
model_table_rows = "\n".join(
    f'<tr class="{"best-row" if best else ""}"><td class="left">{"🏆 " if best else ""}{name}</td>'
    f'<td>{r2:.3f}</td><td>{rmse:,.0f}</td><td>{mae:,.0f}</td><td>{r2t:.3f}</td><td>{gap:.1f}%</td></tr>'
    for name, r2, rmse, mae, r2t, gap, best in model_rows
)

sec5 = f"""
<section>
  <div class="section-head"><div class="section-num">05</div><div class="section-title">모델링 및 가격 예측</div></div>

  <h3>1) 7개 알고리즘 성능 비교</h3>
  <p>단순한 "직선 자"에 가까운 회귀모델부터, 여러 개의 작은 모델이 힘을 합치는 최신 부스팅 모델까지 7종을 동일한 조건에서 겨루게 했습니다.</p>
  {note("선형회귀(OLS)는 '가격 = 출력×a + 나이×b + …' 처럼 모든 변수를 직선 공식 하나로 설명하려 합니다. 반면 트리·부스팅 계열은 '출력이 100 넘고, 나이가 5년 미만이면…' 식으로 조건을 잘게 쪼개 맞히기 때문에 실제 세상의 복잡하고 굴곡진 패턴을 훨씬 잘 잡아냅니다.")}

  <table>
    <tr><th class="left">모델</th><th>R²</th><th>RMSE(천원)</th><th>MAE(천원)</th><th>학습데이터 R²</th><th>과대적합 갭</th></tr>
    {model_table_rows}
  </table>
  {img(10, "7개 모델의 5-fold 교차검증 R²(왼쪽, 높을수록 우수)와 RMSE(오른쪽, 낮을수록 우수) 비교. 붉은색 막대가 최고 성능인 LightGBM입니다.")}

  <p>
    <b>선형회귀·Ridge는 R² 0.54 안팎</b>에 그쳐 가격 변동의 절반 정도밖에 설명하지 못했습니다. 이는 중고차 가격이 여러 변수가 복잡하게 얽힌 <b>비선형적</b> 구조를 갖고 있다는 뜻입니다.
    반면 <b>LightGBM은 R² 0.86</b>으로 가격 변동의 86%를 설명해 가장 우수했고, 예측이 실제 가격과 평균 6,644천원 정도 차이나는 수준까지 정확도를 끌어올렸습니다.
  </p>
  {note("과대적합(오버피팅) 갭 = '학습에 쓴 데이터'와 '한 번도 안 본 검증 데이터'의 성능 차이입니다. 갭이 크면 '족집게 문제만 잘 푸는' 모델이라는 뜻이라 주의가 필요합니다. LightGBM은 성능 1위지만 갭도 35.4%로 다소 큰 편이라, 안정성이 더 중요한 상황에서는 갭이 가장 작은 CatBoost(23.4%)를 보조 모델로 함께 쓰는 것을 권장합니다.")}

  <h3>2) 최적 모델(LightGBM) 예측 진단</h3>
  {img(11, "왼쪽: 실제 가격 vs 모델 예측 가격 산점도(점선에 가까울수록 정확). 오른쪽: 잔차(실제-예측) 플롯 — 0 선 주위에 고르게 흩어져 있어 체계적인 편향이 크지 않음을 보여줍니다.")}

  <h3>3) 어떤 변수가 가격을 가장 크게 좌우할까? — 변수 중요도</h3>
  <p>변수 중요도는 두 가지 방식으로 교차 검증했습니다.</p>
  {note("① 순열중요도(Permutation Importance): 어떤 변수의 값을 일부러 마구 뒤섞은 뒤, 모델 성능이 얼마나 나빠지는지로 그 변수의 '진짜 쓸모'를 측정합니다. ② SHAP: 게임이론에서 빌려온 방법으로, 각 변수가 개별 차량의 예측 가격을 얼마나 올리고 내렸는지를 세밀하게 분해합니다.")}
  {img(12, "순열중요도 기준 변수 중요도. 값이 클수록 '그 정보를 잃었을 때 예측이 크게 나빠지는' 핵심 변수입니다. (범주형 변수는 도시·연료·소유이력처럼 여러 항목을 통째로 하나의 변수로 섞어 측정)")}
  {img(13, "SHAP 기준 변수 중요도 Top 15 (막대그래프).")}
  {img(14, "SHAP Summary Plot — 각 점은 한 대의 차량입니다. 오른쪽으로 갈수록 그 변수가 가격을 끌어올렸다는 뜻이며, 색이 붉을수록(값이 큼) 어느 방향으로 작용하는지 함께 보여줍니다.")}
  <p>
    두 방법 모두 <b>출력(Power_bhp) → 차량 나이(Age) → 배기량(Engine_cc)</b> 순으로 압도적인 영향력을 보였습니다.
    반면 <b>소득(KRW)은 순열중요도 9위</b>로, 예측 정확도에 대한 실질적인 기여는 크지 않았습니다 — 이는 6장의 통계 검증 결과와도 이어집니다.
  </p>
</section>
"""

# ---------------------------------------------------------------------
hyp_rows = [
    ("H0-1", "지역 소득(KRW)은 가격과 무관하다", "0.0039", "계수 -0.000033(부호 반대)", "reject", "기각(주의: 효과 방향 반대·크기 매우 작음)"),
    ("H0-2", "거래 도시 자체는 가격에 영향 없다", "6.7×10⁻⁸⁰", "F-검정(도시 11곳 공동)", "reject", "강하게 기각"),
    ("H0-3", "주행거리·연식 감가는 항상 일정하다", "2.1×10⁻¹⁹", "주행거리 8만km 임계 교호항", "reject", "기각(주행거리 기준만 해당)"),
    ("H0-4", "소유이력·연비는 가격과 무관하다", "6.2×10⁻⁸ / 3.3×10⁻¹⁰", "Owner_Rank / Mileage 계수", "reject", "기각(연비는 효과방향 반대)"),
]
hyp_table_rows = "\n".join(
    f'<tr><td><b>{h}</b></td><td class="left">{desc}</td><td>{p}</td><td class="left">{stat}</td>'
    f'<td><span class="tag reject">기각</span></td><td class="left">{note_}</td></tr>'
    for h, desc, p, stat, _, note_ in hyp_rows
)

sec6 = f"""
<section>
  <div class="section-head"><div class="section-num">06</div><div class="section-title">결론 — 가설 검증 및 대응 전략</div></div>

  <h3>1) 통계적 가설 검증 결과</h3>
  <p>회귀분석(statsmodels, 이분산에 강건한 Robust 표준오차 적용)으로 4개 세부가설의 귀무가설(H0)을 검증했습니다. 판정 기준은 유의수준 <b>α=0.05</b>이며, p-value가 0.05보다 작으면 "우연이라고 보기 어렵다"고 판단해 H0을 기각합니다.</p>
  {img(15, "가설별 통계적 유의성. 막대가 길수록(즉 p-value가 작을수록) 강하게 유의합니다. 점선은 유의수준 기준선(α=0.05)이며, 4개 가설 모두 이 기준선을 훌쩍 넘어 유의했습니다.")}

  <table>
    <tr><th>가설</th><th class="left">귀무가설(H0) 내용</th><th>p-value</th><th class="left">검정 방법</th><th>판정</th><th class="left">해석 시 유의사항</th></tr>
    {hyp_table_rows}
  </table>

  <div class="conclusion-box">
    <b>최종 결론 — 4개 귀무가설(H0) 모두 기각</b><br/><br/>
    통계 검증 결과, "지역·소득·비선형 감가·소유이력/연비는 중고차 가격과 무관하다"는 귀무가설(H0)은 <b>4개 항목 모두 통계적으로 기각</b>되었습니다.
    즉 이들 요인은 <b>우연이 아니라 실제로 가격에 유의미한 영향을 미친다</b>는 대립가설(H1)이 채택되었습니다.
    다만 아래 두 가지는 방향과 크기를 신중하게 해석해야 합니다.
  </div>

  <h3>2) 신중하게 읽어야 할 두 가지 결과</h3>
  <h4>① 소득(H0-1) — 기각되었지만 "생각과 반대 방향"</h4>
  <p>
    도시 단위로 단순 비교하면 소득이 높을수록 가격도 높은 경향(r=0.39)이 있었지만, 차량 스펙과 <b>도시 고유효과를 함께 통제</b>한 정밀 회귀분석에서는 소득의 순수한 효과가 통계적으로는 유의하되(p=0.004) <b>부호가 반대이고 크기가 매우 작았습니다.</b>
    쉽게 말해 "그 도시가 어디인지"를 이미 알고 있다면, "그 도시의 평균 소득이 얼마인지"는 가격 예측에 추가로 알려주는 정보가 거의 없다는 뜻입니다. 도시 고유 효과(H0-2)가 소득 효과를 사실상 흡수해버린 것입니다.
  </p>
  <h4>② 연비(H0-4의 일부) — 기각되었지만 "프리미엄이 아니라 페널티"</h4>
  <p>
    가설은 "연비가 좋을수록 비쌀 것"이었지만, 배기량·출력을 통제하고 보면 연비가 좋을수록 오히려 가격이 낮았습니다(계수 음수).
    이는 연비가 좋은 차 = 대개 배기량이 작은 소형·경제형 차량이기 때문으로, "연비 자체의 프리미엄"이 아니라 "차량 등급의 차이"가 진짜 원인임을 시사합니다.
  </p>

  <h3>3) 대응 전략 — H0가 기각되었다는 것은 무엇을 의미하나</h3>
  <p>귀무가설이 기각되었다는 것은 <b>"감으로 매입가를 정해도 된다"는 안일한 전제가 틀렸다는 뜻</b>입니다. 즉 데이터 기반 매입가 산정 체계 도입이 통계적으로 정당화됩니다. 다만 효과가 반대이거나 미미했던 항목은 아래처럼 대응합니다.</p>
  <ul>
    <li><b>도시(H0-2, 강하게 기각)</b> → 매입가 산정 시 "도시" 자체를 핵심 보정 변수로 사용(소득 대신)</li>
    <li><b>소득(H0-1, 기각되었으나 효과 미미)</b> → 소득 데이터는 참고용 모니터링 지표로만 유지하고, 매입가 산식에서 직접 가중치를 주지 않음</li>
    <li><b>비선형 감가(H0-3, 부분 기각)</b> → 주행거리 8만km를 매입 리스크 구간의 기준선으로 사용(연식보다 신뢰도 높음)</li>
    <li><b>소유이력·연비(H0-4, 기각)</b> → 소유이력은 프리미엄/디스카운트 변수로 그대로 사용하되, 연비는 배기량·출력과 함께 봐야 하므로 단독 가점 요인에서 제외</li>
  </ul>
</section>
"""

# ---------------------------------------------------------------------
sec7 = f"""
<section>
  <div class="section-head"><div class="section-num">07</div><div class="section-title">인사이트 분석 및 비즈니스 전략</div></div>

  <h3>1) 데이터 기반 매입가(Bid Price) 자동 산출</h3>
  <p>최적 모델(LightGBM)로 계산한 "예측 판매가"에서, 리스크가 큰 차량일수록 마진을 더 두텁게 잡는 <b>차등 마진</b>을 적용해 매입가를 계산합니다.</p>
  <div class="note" style="font-family:monospace; font-size:12.5px;">
    매입가(Bid Price) = 예측 판매가 × (1 − 적용 마진율)<br/>
    적용 마진율 = 기본 12% + (연식 7년 초과 또는 주행거리 8만km 초과 시 +6%p) + (소유자 3인 이상 시 +3%p), 상한 25%
  </div>
  <p>실제로 가격이 기재되지 않은(=매입 검토가 필요한) 차량 1,053건에 이 로직을 적용한 결과입니다.</p>
  <div class="kpi-row">
    <div class="kpi"><div class="v">7,758.9천원</div><div class="l">예측 판매가 중앙값</div></div>
    <div class="kpi"><div class="v">6,675.7천원</div><div class="l">산출 매입가 중앙값</div></div>
    <div class="kpi"><div class="v">14.9%</div><div class="l">평균 적용 마진율</div></div>
    <div class="kpi"><div class="v">1,053대</div><div class="l">매입 검토 대상 차량</div></div>
  </div>
  {img(16, "매입 검토 대상 1,053대의 예측 판매가 분포(왼쪽)와 적용 마진율 분포(오른쪽).")}

  <h3>2) 지역(도시) 기반 매입 전략</h3>
  <table>
    <tr><th class="left">전략 구분</th><th class="left">대상 도시</th><th class="left">권장 액션</th></tr>
    <tr><td class="left">🔵 프리미엄 매입 지역</td><td class="left">Coimbatore, Bangalore, Kochi</td><td class="left">도시 고유 프리미엄이 확인된 지역 → 매입가를 다소 상향해서라도 적극 확보, 재고 우선 배분</td></tr>
    <tr><td class="left">⚪ 표준 매입 지역</td><td class="left">Ahmedabad, Hyderabad, Mumbai, Delhi</td><td class="left">전국 평균 수준의 표준 매입가 로직 적용</td></tr>
    <tr><td class="left">🟠 보수적 매입 지역</td><td class="left">Chennai, Pune, Jaipur, Kolkata</td><td class="left">도시 디스카운트가 확인된 지역 → 매입가를 보수적으로 산정해 재판매 리스크 축소</td></tr>
  </table>
  {note("주의: 앞서 살펴본 대로 '그 도시의 평균 소득'이 아니라 '그 도시 자체(수요·딜러 밀집도·차량 선호 등 복합 요인)'가 기준입니다. 소득 통계만 보고 지역 전략을 세우면 Delhi(고소득·중위가격)처럼 예측이 빗나갈 수 있습니다.")}

  <h3>3) 재고 회전 및 리스크 관리 전략</h3>
  <ul>
    <li><b>주행거리 8만km 이상 차량</b>: 이미 감가율이 완만해진 구간이므로 추가 하락 리스크가 낮음 → 표준 마진으로 회전 우선 처리</li>
    <li><b>연식 10년 이상 차량</b>: 감가가 가속되는 구간에 진입 → 매입을 더 보수적으로 하거나, 빠른 처분이 가능한 경매/B2B 채널로 신속 회전</li>
    <li><b>3인 이상 소유이력 차량</b>: 프리미엄이 사라지는 구간 → 자동으로 마진을 높여 리스크 상쇄(위 산식에 이미 반영)</li>
  </ul>

  <h3>4) 종합 액션 플랜 요약</h3>
  <ol>
    <li>LightGBM 기반 예측 판매가 산출 → 리스크 연동 차등 마진 적용 → Bid Price를 매입 현장(딜러 태블릿/시스템)에 실시간 제공</li>
    <li>지역(도시) 등급표를 분기별로 갱신해 매입가 보정계수로 반영</li>
    <li>주행거리 8만km·연식 10년을 재고 회전 우선순위 기준선으로 운영 프로세스에 반영</li>
  </ol>

  {warn("<b>안전 고지</b> — 본 보고서의 예측 가격은 등록된 스펙·주행거리·연식·지역 데이터를 바탕으로 한 시장 추정치입니다. 실제 매입 시에는 사고 이력 조회와 차량 외관·기계 상태에 대한 현장 실사(In-person Inspection)를 반드시 병행해야 하며, 모델 예측값만으로 최종 매입가를 확정해서는 안 됩니다.")}

  <div class="pagefoot">인도 중고차 매입가 예측 &amp; 비즈니스 전략 분석 보고서 · AI 데이터 분석팀 · 2026-08-13</div>
</section>
"""

html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<title>인도 중고차 매입가 예측 &amp; 비즈니스 전략 분석 보고서</title>
<style>{CSS}</style>
</head>
<body>
{cover}
{sec1}
{sec2}
{sec3}
{sec4}
{sec5}
{sec6}
{sec7}
</body>
</html>
"""

out_path = REPORT_DIR / "report.html"
out_path.write_text(html, encoding="utf-8")
print("report.html 생성 완료:", out_path, len(html), "chars")
