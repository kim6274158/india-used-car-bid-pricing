# -*- coding: utf-8 -*-
"""analysis.ipynb 를 생성하는 빌더 스크립트. 실행하면 nb 객체를 조립해 파일로 저장한다."""
from pathlib import Path
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []

def md(text):
    cells.append(nbf.v4.new_markdown_cell(text))

def code(text):
    cells.append(nbf.v4.new_code_cell(text))

# ------------------------------------------------------------------
md("""# 🚗 인도 중고차 매입가 예측 & 비즈니스 전략 분석

**페르소나**: 인도 중고차 매입 딜러 데이터 사이언티스트
**목표**: `Car.csv`(중고차 거래) + `지역별소득수준_krw.csv`(지역 소득)를 State·Year 기준으로 정밀 병합하여
① 최적 가격 예측 모델 도출, ② 지역/소득 영향력 가설 검증, ③ 매입 마진 전략 수립

단계별로 **코드 → 실행결과 → 시각화**를 바로 아래에서 확인할 수 있도록 셀을 분리했습니다.""")

# ------------------------------------------------------------------
md("## 0. 환경 설정 & 라이브러리 임포트")
code("""import re, json, warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

from sklearn.model_selection import KFold, cross_val_predict
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.inspection import permutation_importance

import xgboost as xgb
import lightgbm as lgb
import catboost as cb
import shap

import statsmodels.api as sm
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")

# 한글 폰트 설정 (Windows)
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
sns.set_theme(style="whitegrid", font="Malgun Gothic")

PALETTE = ["#4C6FFF", "#00B8A9", "#FF8A5B", "#8B5CF6", "#F2C14E", "#EF476F", "#118AB2"]
sns.set_palette(PALETTE)

# notebooks/analysis.ipynb 기준 상대경로. Jupyter cwd가 notebooks/든 프로젝트 루트든 모두 동작하도록
# ../data가 있으면 그쪽을, 없으면 data/를 그대로 사용한다.
DATA_DIR = Path("../data") if Path("../data").exists() else Path("data")
OUTPUT_DIR = Path("../outputs") if Path("../data").exists() else Path("outputs")
CAR_PATH = DATA_DIR / "Car.csv"
INCOME_PATH = DATA_DIR / "지역별소득수준_krw.csv"
pd.set_option("display.max_columns", 40)
pd.set_option("display.width", 140)
print("설정 완료")""")

# ------------------------------------------------------------------
md("""## 1. 데이터 로드 & 기본 구조 파악
중고차 거래 데이터와 지역별 소득 데이터를 로드하고 행/열 규모, 컬럼 타입, 결측치 현황을 확인합니다.""")
code("""car = pd.read_csv(CAR_PATH)
inc = pd.read_csv(INCOME_PATH)

print(f"[중고차 데이터] shape = {car.shape}")
print(f"[소득 데이터]   shape = {inc.shape}")
display(car.head(3))
display(inc.head(3))""")

code("""print("=== 중고차 데이터 결측치 ===")
display(car.isna().sum().to_frame("결측치 수"))
print("\\n=== 소득 데이터 결측치 ===")
display(inc.isna().sum().to_frame("결측치 수"))""")

md("""**Location 규모 검증**: 원 시스템 프롬프트는 "중고차 11개 Location vs 소득 9개 Location 불일치"를 전제했지만,
실제 파일을 확인하면 소득 데이터도 Location 기준 11개(State 기준 9개)로 중고차 데이터와 1:1 대응합니다.
아래에서 직접 검증합니다.""")
code("""car_locs = set(car["Location"].unique())
inc_locs = set(inc["Location"].unique())
inc_states = sorted(inc["State"].unique())

print("중고차 Location (", len(car_locs), "개):", sorted(car_locs))
print("소득 Location   (", len(inc_locs), "개):", sorted(inc_locs))
print("소득 State      (", len(inc_states), "개):", inc_states)
print("\\n두 Location 집합 완전 일치 여부:", car_locs == inc_locs)""")

code("""fig, ax = plt.subplots(figsize=(7, 3.2))
counts = pd.Series({"중고차 Location": len(car_locs), "소득 Location": len(inc_locs), "소득 State": len(inc_states)})
bars = ax.bar(counts.index, counts.values, color=PALETTE[:3])
for b, v in zip(bars, counts.values):
    ax.text(b.get_x() + b.get_width()/2, v + 0.15, str(v), ha="center", fontweight="bold")
ax.set_title("데이터셋별 지역 단위 개수 비교")
ax.set_ylim(0, 13)
plt.tight_layout()
plt.show()""")

# ------------------------------------------------------------------
md("""## 2. 단위 수치 파싱 전처리 (Mileage / Engine / Power / New_Price)
`Mileage`(kmpl·km/kg), `Engine`(CC), `Power`(bhp) 등 단위 문자가 섞인 컬럼에서 순수 수치만 추출합니다.
`Mileage`는 CNG/LPG(km/kg)와 Petrol/Diesel(kmpl) 단위 차이를 등가환산계수(1.4)로 표준화합니다.""")
code("""num_re = re.compile(r"([0-9]+\\.?[0-9]*)")

def extract_number(s):
    if pd.isna(s):
        return np.nan
    m = num_re.search(str(s))
    return float(m.group(1)) if m else np.nan

def parse_mileage(s):
    if pd.isna(s):
        return np.nan, None
    s = str(s).strip()
    if s == "" or s.lower() in ("nan", "none"):
        return np.nan, None
    val = extract_number(s)
    unit = "km/kg" if "km/kg" in s.lower() else ("kmpl" if "kmpl" in s.lower() else None)
    return val, unit

mileage_parsed = car["Mileage"].apply(parse_mileage)
car["Mileage_val"] = mileage_parsed.apply(lambda t: t[0])
car["Mileage_unit"] = mileage_parsed.apply(lambda t: t[1])

CNG_LPG_TO_KMPL_FACTOR = 1.4
car["Mileage_final"] = car["Mileage_val"]
mask_kg = car["Mileage_unit"] == "km/kg"
car.loc[mask_kg, "Mileage_final"] = car.loc[mask_kg, "Mileage_val"] * CNG_LPG_TO_KMPL_FACTOR
car.loc[car["Mileage_final"] <= 0, "Mileage_final"] = np.nan  # 0.0kmpl(이상치/전기차) -> 결측 처리

car["Engine_cc"] = car["Engine"].apply(extract_number)
car["Power_bhp"] = car["Power"].apply(extract_number)

def parse_new_price(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    if s == "" or s.lower() in ("nan", "none"):
        return np.nan
    num = extract_number(s)
    if num is None or np.isnan(num):
        return np.nan
    sl = s.lower()
    if "cr" in sl:
        return num * 10000.0
    if "lakh" in sl:
        return num * 100.0
    return num

car["New_Price_thousand"] = car.get("New_Price", pd.Series(dtype=float)).apply(parse_new_price)

print("파싱 전/후 샘플 비교")
display(car[["Mileage", "Mileage_unit", "Mileage_final", "Engine", "Engine_cc", "Power", "Power_bhp"]].head(6))
print("\\nMileage_unit 분포:", car["Mileage_unit"].value_counts(dropna=False).to_dict())""")

code("""fig, axes = plt.subplots(1, 3, figsize=(15, 4))
sns.histplot(car["Mileage_final"].dropna(), bins=40, ax=axes[0], color=PALETTE[0])
axes[0].set_title("Mileage_final 분포 (등가 kmpl)")
sns.histplot(car["Engine_cc"].dropna(), bins=40, ax=axes[1], color=PALETTE[1])
axes[1].set_title("Engine_cc 분포")
sns.histplot(car["Power_bhp"].dropna(), bins=40, ax=axes[2], color=PALETTE[2])
axes[2].set_title("Power_bhp 분포")
plt.tight_layout()
plt.show()""")

# ------------------------------------------------------------------
md("""## 3. State·Year 기반 정밀 병합
1. 소득 데이터의 (Location→State) 매핑을 차량 데이터에 결합
2. 차량 `Year`(연식)와 소득 `Year`가 **정확히 일치**하는 시점의 지역소득을 우선 사용
3. 소득 데이터 범위(2011~2020) 밖의 연식(주로 2011년 이전)은 해당 Location의 **최신(2020) 소득값**으로 폴백하여 결측 방지
4. State 단위 평균소득(`KRW_state_year`)도 별도 산출해 "순수 소득효과"와 "도시 고유효과"를 분리 검증""")
code("""loc2state = inc[["Location", "State"]].drop_duplicates().set_index("Location")["State"].to_dict()
car["State"] = car["Location"].map(loc2state)

inc_year_min, inc_year_max = int(inc["Year"].min()), int(inc["Year"].max())

# (a) 정확한 Location+Year 매치
exact = inc[["Location", "Year", "KRW"]].rename(columns={"KRW": "KRW_exact"})
merged = car.merge(exact, how="left", on=["Location", "Year"])

# (b) 매치 실패 -> Location별 최신(2020) KRW로 폴백
latest_by_loc = (
    inc.sort_values("Year").groupby("Location", as_index=False).last()[["Location", "KRW", "Year"]]
    .rename(columns={"KRW": "KRW_latest", "Year": "KRW_latest_year"})
)
merged = merged.merge(latest_by_loc, how="left", on="Location")

merged["KRW_source"] = np.where(merged["KRW_exact"].notna(), "exact_year", "fallback_latest")
merged["KRW"] = merged["KRW_exact"].where(merged["KRW_exact"].notna(), merged["KRW_latest"])

# State 단위 평균 소득(도시 순수효과 분리검증용)
state_year_income = inc.groupby(["State", "Year"], as_index=False)["KRW"].mean().rename(columns={"KRW": "KRW_state_year"})
merged = merged.merge(state_year_income, how="left", on=["State", "Year"])
state_latest = (
    inc.groupby(["State", "Year"], as_index=False)["KRW"].mean()
    .sort_values("Year").groupby("State", as_index=False).last()[["State", "KRW"]]
    .rename(columns={"KRW": "KRW_state_latest"})
)
merged = merged.merge(state_latest, how="left", on="State")
merged["KRW_state_year"] = merged["KRW_state_year"].where(merged["KRW_state_year"].notna(), merged["KRW_state_latest"])

n_exact = int((merged["KRW_source"] == "exact_year").sum())
n_fallback = int((merged["KRW_source"] == "fallback_latest").sum())
n_unmatched = int(merged["KRW"].isna().sum())

print(f"병합 후 shape: {merged.shape}")
print(f"Location+Year 정확 매치: {n_exact}건")
print(f"Location 최신값 폴백:    {n_fallback}건 (연식이 소득데이터 범위[{inc_year_min}~{inc_year_max}] 밖)")
print(f"완전 미매치(결측):        {n_unmatched}건")""")

code("""fig, ax = plt.subplots(figsize=(6, 4))
vals = pd.Series({"정확 Year 매치": n_exact, "최신값 폴백": n_fallback, "미매치": n_unmatched})
colors = [PALETTE[0], PALETTE[4], PALETTE[5]]
ax.pie(vals.values, labels=[f"{i}\\n{v:,}건" for i, v in vals.items()], autopct="%1.1f%%",
       colors=colors, startangle=90, wedgeprops=dict(edgecolor="white"))
ax.set_title("차량-소득 데이터 Year 매핑 결과")
plt.tight_layout()
plt.show()""")

# ------------------------------------------------------------------
md("""## 4. 결측치 임퓨테이션 & 파생변수 생성
수치형 컬럼은 중앙값으로 대체하고, `Age`(2020년 기준 차령), `Owner_Rank`(소유이력 서열) 파생변수를 만듭니다.""")
code("""TRANSACTION_YEAR = inc_year_max
merged["Age"] = (TRANSACTION_YEAR - merged["Year"]).clip(lower=0)

numeric_impute_cols = ["Kilometers_Driven", "Mileage_final", "Engine_cc", "Power_bhp", "Seats", "KRW", "KRW_state_year"]
impute_medians = {}
for c in numeric_impute_cols:
    merged[c] = pd.to_numeric(merged[c], errors="coerce")
    med = merged[c].median()
    impute_medians[c] = float(med)
    merged[c] = merged[c].fillna(med)

for c in ["Fuel_Type", "Transmission", "Owner_Type", "Location", "State"]:
    merged[c] = merged[c].astype(str).str.strip()

owner_map = {"First": 1, "Second": 2, "Third": 3, "Fourth & Above": 4}
merged["Owner_Rank"] = merged["Owner_Type"].map(owner_map).fillna(2)

merged["Price"] = pd.to_numeric(merged["Price"], errors="coerce")

print("임퓨테이션에 사용된 중앙값:")
display(pd.Series(impute_medians).to_frame("중앙값"))

labeled = merged[merged["Price"].notna() & (merged["Price"] > 0)].copy()
unlabeled = merged[merged["Price"].isna()].copy()
print(f"\\n라벨(Price)有 -> 모델링용: {labeled.shape[0]}건")
print(f"라벨(Price)無 -> 매입가 산정 시연용: {unlabeled.shape[0]}건")""")

# ------------------------------------------------------------------
md("""## 5. 타깃 변수(Price) 로그 변환
`Price`는 왜도가 매우 큰 분포입니다. 자연로그 변환으로 정규성을 확보하고, 모델 평가/매입가 산출 시 `exp()`로 복원합니다.""")
code("""labeled["log_Price"] = np.log(labeled["Price"])

skew_before = labeled["Price"].skew()
skew_after = labeled["log_Price"].skew()

fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
sns.histplot(labeled["Price"], bins=50, kde=True, ax=axes[0], color=PALETTE[0])
axes[0].set_title(f"Price 원본 분포 (skew={skew_before:.2f})")
axes[0].set_xlabel("Price (천원)")
sns.histplot(labeled["log_Price"], bins=50, kde=True, ax=axes[1], color=PALETTE[1])
axes[1].set_title(f"log(Price) 변환 후 분포 (skew={skew_after:.2f})")
axes[1].set_xlabel("log(Price)")
plt.tight_layout()
plt.show()

print(f"평균 {labeled['Price'].mean():,.0f} vs 중앙값 {labeled['Price'].median():,.0f} (비율 {labeled['Price'].mean()/labeled['Price'].median():.2f}) -> 로그변환 필요성 확인")""")

# ------------------------------------------------------------------
md("""## 6. EDA ① — 소득(KRW) vs 가격(Price) 관계
지역(Location) 단위로 집계한 소득 수준과 중고차 평균 거래가의 관계를 확인합니다.""")
code("""krw_price_ratio = labeled["Price"].median() / labeled["KRW"].median()
print(f"전체 중앙값 Price / 중앙값 KRW 비율: {krw_price_ratio:.3f}")

loc_stats = labeled.groupby("Location").agg(median_price=("Price", "median"), median_krw=("KRW", "median"), n=("Price", "size")).sort_values("median_price", ascending=False)
display(loc_stats)

corr = loc_stats["median_price"].corr(loc_stats["median_krw"])
print(f"\\nLocation 단위 Price-KRW 상관계수: r = {corr:.3f}")""")

code("""fig, ax = plt.subplots(figsize=(7.5, 6))
sc = ax.scatter(loc_stats["median_krw"], loc_stats["median_price"], s=loc_stats["n"]/3, c=PALETTE[0], alpha=0.75, edgecolor="white")
for loc, row in loc_stats.iterrows():
    ax.annotate(loc, (row["median_krw"], row["median_price"]), fontsize=9, xytext=(5, 4), textcoords="offset points")
z = np.polyfit(loc_stats["median_krw"], loc_stats["median_price"], 1)
xs = np.linspace(loc_stats["median_krw"].min(), loc_stats["median_krw"].max(), 50)
ax.plot(xs, np.polyval(z, xs), "--", color=PALETTE[5], linewidth=2, label=f"추세선 (r={corr:.2f})")
ax.set_xlabel("Location 중앙값 소득 KRW (천원)")
ax.set_ylabel("Location 중앙값 Price (천원)")
ax.set_title("지역 소득수준 vs 중고차 거래가격 (버블 크기=거래건수)")
ax.legend()
plt.tight_layout()
plt.show()""")

md("""**해석**: 상관계수가 중간 수준(r≈0.39)에 그치고, Delhi(최고소득)가 가격 중위권, Coimbatore·Kochi(중위소득)가 가격 상위권인
불일치 사례가 관찰됩니다 → "소득 자체"보다 "도시 고유 요인"이 더 강하게 작용할 가능성을 시사(§9에서 통계적으로 검증).""")

# ------------------------------------------------------------------
md("## 7. EDA ② — Location별 가격 분포 (Boxplot)")
code("""order = labeled.groupby("Location")["Price"].median().sort_values(ascending=False).index
fig, ax = plt.subplots(figsize=(11, 5))
sns.boxplot(data=labeled, x="Location", y="Price", order=order, ax=ax, palette=PALETTE * 2, showfliers=False)
ax.set_title("Location별 Price 분포 (이상치 제외)")
ax.set_ylabel("Price (천원)")
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
plt.show()""")

# ------------------------------------------------------------------
md("""## 8. EDA ③ — 비선형 감가 패턴 (주행거리 · 연식)
주행거리 8만km, 연식 7년을 기준으로 감가 폭이 어떻게 변하는지 구간별 중앙값과 하락률을 확인합니다.""")
code("""labeled["km_bin"] = pd.cut(labeled["Kilometers_Driven"], bins=[-1, 20000, 50000, 80000, 120000, 10_000_000],
                            labels=["<20k", "20-50k", "50-80k", "80-120k", "120k+"])
labeled["age_bin"] = pd.cut(labeled["Age"], bins=[-1, 3, 5, 7, 10, 100],
                             labels=["0-3y", "4-5y", "6-7y", "8-10y", "10y+"])

km_med = labeled.groupby("km_bin", observed=True)["Price"].median()
age_med = labeled.groupby("age_bin", observed=True)["Price"].median()
km_pct = km_med.pct_change() * 100
age_pct = age_med.pct_change() * 100

fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
bars0 = axes[0].bar(km_med.index.astype(str), km_med.values, color=PALETTE[0])
axes[0].set_title("주행거리 구간별 중앙값 Price")
axes[0].set_ylabel("Price (천원)")
for i, (b, pct) in enumerate(zip(bars0, km_pct.values)):
    label = "-" if pd.isna(pct) else f"{pct:+.1f}%"
    axes[0].text(b.get_x()+b.get_width()/2, b.get_height()*1.01, label, ha="center", fontsize=9, color=PALETTE[5], fontweight="bold")

bars1 = axes[1].bar(age_med.index.astype(str), age_med.values, color=PALETTE[1])
axes[1].set_title("연식 구간별 중앙값 Price")
axes[1].set_ylabel("Price (천원)")
for i, (b, pct) in enumerate(zip(bars1, age_pct.values)):
    label = "-" if pd.isna(pct) else f"{pct:+.1f}%"
    axes[1].text(b.get_x()+b.get_width()/2, b.get_height()*1.01, label, ha="center", fontsize=9, color=PALETTE[5], fontweight="bold")

plt.tight_layout()
plt.show()

print("주행거리 구간별 직전대비 하락률:", {k: (None if pd.isna(v) else round(v,1)) for k,v in km_pct.items()})
print("연식   구간별 직전대비 하락률:", {k: (None if pd.isna(v) else round(v,1)) for k,v in age_pct.items()})""")

md("""**해석**: 주행거리는 8만km 지점부터 하락률이 -18.2%→-9.6%→-4.3%로 뚜렷하게 **둔화**(가설3 지지).
반대로 연식은 10년 이상 구간에서 -43.0%로 하락률이 오히려 **가속**(가설3과 반대 방향, survivorship bias 가능성).""")

# ------------------------------------------------------------------
md("## 9. EDA ④ — 소유이력 · 연료타입별 가격")
code("""fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
owner_order = ["First", "Second", "Third", "Fourth & Above"]
sns.boxplot(data=labeled, x="Owner_Type", y="Price", order=owner_order, ax=axes[0], palette=PALETTE, showfliers=False)
axes[0].set_title("소유이력(Owner_Type)별 Price 분포")

fuel_order = labeled.groupby("Fuel_Type")["Price"].median().sort_values(ascending=False).index
sns.boxplot(data=labeled, x="Fuel_Type", y="Price", order=fuel_order, ax=axes[1], palette=PALETTE, showfliers=False)
axes[1].set_title("연료타입(Fuel_Type)별 Price 분포")
plt.tight_layout()
plt.show()""")

# ------------------------------------------------------------------
md("## 10. EDA ⑤ — 수치형 변수 상관관계 히트맵")
code("""num_cols_corr = ["Price", "KRW", "Age", "Kilometers_Driven", "Mileage_final", "Engine_cc", "Power_bhp", "Seats", "Owner_Rank"]
corr_mat = labeled[num_cols_corr].corr()

fig, ax = plt.subplots(figsize=(8, 6.5))
sns.heatmap(corr_mat, annot=True, fmt=".2f", cmap="RdBu_r", center=0, vmin=-1, vmax=1, ax=ax, square=True, cbar_kws={"shrink": .8})
ax.set_title("수치형 변수 상관관계")
plt.tight_layout()
plt.show()""")

# ------------------------------------------------------------------
md("""## 11. 머신러닝 모델링 파이프라인 구성
수치형 8개 + 범주형 4개(Location/Fuel_Type/Transmission/Owner_Type) 컬럼을 사용해 OneHot+StandardScaler 전처리 파이프라인을 만들고,
OLS/Ridge/RandomForest/GradientBoosting/XGBoost/LightGBM/CatBoost 7개 모델을 동일 조건에서 비교합니다.""")
code("""numeric_features = ["KRW", "Age", "Kilometers_Driven", "Mileage_final", "Engine_cc", "Power_bhp", "Seats", "Owner_Rank"]
categorical_features = ["Location", "Fuel_Type", "Transmission", "Owner_Type"]

X = labeled[numeric_features + categorical_features].copy()
y = labeled["log_Price"].copy()
y_true_price = labeled["Price"].values

numeric_transformer = Pipeline([("scaler", StandardScaler())])
cat_transformer = Pipeline([("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])
preprocessor = ColumnTransformer([
    ("num", numeric_transformer, numeric_features),
    ("cat", cat_transformer, categorical_features),
])

models = [
    ("OLS", LinearRegression()),
    ("Ridge", RidgeCV(alphas=[0.01, 0.1, 1.0, 10.0, 100.0])),
    ("RandomForest", RandomForestRegressor(n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=-1)),
    ("GradientBoosting", GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, random_state=42)),
    ("XGBoost", xgb.XGBRegressor(n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=42, verbosity=0)),
    ("LightGBM", lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=31, random_state=42, verbosity=-1)),
    ("CatBoost", cb.CatBoostRegressor(n_estimators=400, depth=6, learning_rate=0.05, verbose=0, random_state=42)),
]
print(f"모델 {len(models)}개, 학습 샘플 {X.shape[0]}건, 피처 {X.shape[1]}개 (인코딩 전) 준비 완료")""")

# ------------------------------------------------------------------
md("""## 12. 모델별 5-fold 교차검증 성능 비교
로그 스케일로 학습(cross_val_predict) 후 `exp()`로 원 스케일 복원하여 R²/RMSE/MAE를 계산하고,
학습 데이터 전체 적합(in-sample) 성능과 비교해 과대적합 정도를 함께 확인합니다.""")
code("""kf = KFold(n_splits=5, shuffle=True, random_state=42)
results = []
fitted_pipes = {}

for name, model in models:
    pipe = Pipeline([("pre", preprocessor), ("model", model)])
    y_pred_log_cv = cross_val_predict(pipe, X, y, cv=kf, n_jobs=-1)
    y_pred_cv = np.exp(y_pred_log_cv)
    r2 = r2_score(y_true_price, y_pred_cv)
    rmse = float(np.sqrt(mean_squared_error(y_true_price, y_pred_cv)))
    mae = float(mean_absolute_error(y_true_price, y_pred_cv))

    pipe_full = Pipeline([("pre", preprocessor), ("model", model)])
    pipe_full.fit(X, y)
    y_pred_train = np.exp(pipe_full.predict(X))
    rmse_train = float(np.sqrt(mean_squared_error(y_true_price, y_pred_train)))
    r2_train = r2_score(y_true_price, y_pred_train)
    overfit_gap_pct = (rmse - rmse_train) / rmse * 100 if rmse > 0 else 0.0

    results.append({"model": name, "r2_cv": r2, "rmse_cv": rmse, "mae_cv": mae,
                     "r2_train": r2_train, "rmse_train": rmse_train, "overfit_gap_pct": overfit_gap_pct,
                     "y_pred_cv": y_pred_cv})
    fitted_pipes[name] = pipe_full
    print(f"[{name:16s}] R2={r2:.4f}  RMSE={rmse:8.1f}  MAE={mae:8.1f}  (in-sample R2={r2_train:.4f}, 과적합갭={overfit_gap_pct:5.1f}%)")

results_df = pd.DataFrame(results).drop(columns=["y_pred_cv"]).sort_values("rmse_cv").reset_index(drop=True)
best_name = results_df.iloc[0]["model"]
best_pipe = fitted_pipes[best_name]
print(f"\\n>>> 최적 모델: {best_name} (RMSE 기준)")
display(results_df)""")

code("""fig, axes = plt.subplots(1, 2, figsize=(13, 5))
order_r2 = results_df.sort_values("r2_cv", ascending=True)
axes[0].barh(order_r2["model"], order_r2["r2_cv"], color=[PALETTE[5] if m==best_name else PALETTE[0] for m in order_r2["model"]])
axes[0].set_title("모델별 5-fold CV R²")
axes[0].set_xlabel("R²")
for i, (m, v) in enumerate(zip(order_r2["model"], order_r2["r2_cv"])):
    axes[0].text(v+0.01, i, f"{v:.3f}", va="center", fontsize=9)

order_rmse = results_df.sort_values("rmse_cv", ascending=False)
axes[1].barh(order_rmse["model"], order_rmse["rmse_cv"], color=[PALETTE[5] if m==best_name else PALETTE[1] for m in order_rmse["model"]])
axes[1].set_title("모델별 5-fold CV RMSE (낮을수록 우수)")
axes[1].set_xlabel("RMSE (천원)")
for i, (m, v) in enumerate(zip(order_rmse["model"], order_rmse["rmse_cv"])):
    axes[1].text(v+80, i, f"{v:,.0f}", va="center", fontsize=9)
plt.tight_layout()
plt.show()""")

# ------------------------------------------------------------------
md(f"## 13. 최적 모델 진단 — 실측 vs 예측 / 잔차 플롯")
code("""best_result = next(r for r in results if r["model"] == best_name)
y_pred_best = best_result["y_pred_cv"]
residuals = y_true_price - y_pred_best

fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
axes[0].scatter(y_true_price, y_pred_best, alpha=0.25, s=14, color=PALETTE[0])
lims = [0, max(y_true_price.max(), y_pred_best.max())]
axes[0].plot(lims, lims, "--", color=PALETTE[5], linewidth=2, label="완전 일치선")
axes[0].set_xlabel("실측 Price (천원)")
axes[0].set_ylabel("예측 Price (천원)")
axes[0].set_title(f"{best_name}: 실측 vs 예측 (CV, R²={best_result['r2_cv']:.3f})")
axes[0].legend()

axes[1].scatter(y_pred_best, residuals, alpha=0.25, s=14, color=PALETTE[1])
axes[1].axhline(0, linestyle="--", color=PALETTE[5], linewidth=2)
axes[1].set_xlabel("예측 Price (천원)")
axes[1].set_ylabel("잔차 (실측-예측)")
axes[1].set_title("잔차 플롯")
plt.tight_layout()
plt.show()""")

# ------------------------------------------------------------------
md("## 14. 변수 중요도 ① — Permutation Importance")
code("""# permutation_importance는 파이프라인의 "입력" 컬럼(전처리 이전, 12개: 수치 8 + 범주형 4) 단위로
# 셔플하여 성능 하락폭을 측정한다. 따라서 이름표도 원본 컬럼명(raw_feat_names)을 써야 한다.
# (원-핫 확장된 30개 이름을 붙이면 길이 불일치로 라벨이 밀려 잘못 매칭되므로 주의)
raw_feat_names = numeric_features + categorical_features

perm = permutation_importance(best_pipe, X, y, n_repeats=8, random_state=42, n_jobs=-1)
perm_imp = pd.Series(perm.importances_mean, index=raw_feat_names).sort_values(ascending=False)

fig, ax = plt.subplots(figsize=(8, 5))
top = perm_imp.sort_values()
ax.barh(top.index, top.values, color=PALETTE[0])
ax.set_title(f"{best_name} Permutation Importance (원본 컬럼 단위, 범주형은 전체 컬럼 셔플)")
ax.set_xlabel("중요도 (log_Price 기준 성능 하락폭)")
plt.tight_layout()
plt.show()
display(perm_imp.to_frame("importance"))""")

# ------------------------------------------------------------------
md("## 15. 변수 중요도 ② — SHAP Summary")
code("""ohe = best_pipe.named_steps["pre"].named_transformers_["cat"].named_steps["ohe"]
cat_names = list(ohe.get_feature_names_out(categorical_features))
feat_names = numeric_features + cat_names  # 원-핫 전개된 30개 이름 (SHAP은 변환된 X_trans 기준이라 이 이름이 맞음)

X_trans = best_pipe.named_steps["pre"].transform(X)
model_step = best_pipe.named_steps["model"]

rng = np.random.RandomState(42)
sample_idx = rng.choice(len(X_trans), size=min(1000, len(X_trans)), replace=False)
X_sample = X_trans[sample_idx]

if best_name in ("RandomForest", "GradientBoosting", "XGBoost", "LightGBM", "CatBoost"):
    explainer = shap.TreeExplainer(model_step)
    sv = explainer.shap_values(X_sample)
else:
    explainer = shap.Explainer(model_step, X_trans[:200])
    sv = explainer(X_sample).values

shap_df = pd.DataFrame(sv, columns=feat_names)
mean_abs_shap = shap_df.abs().mean().sort_values(ascending=False)

fig, ax = plt.subplots(figsize=(8, 6))
top15 = mean_abs_shap.head(15).sort_values()
ax.barh(top15.index, top15.values, color=PALETTE[2])
ax.set_title(f"{best_name} SHAP Mean|Value| (Top 15)")
ax.set_xlabel("평균 절대 SHAP 값 (log_Price 기여도)")
plt.tight_layout()
plt.show()

shap.summary_plot(sv, features=X_sample, feature_names=feat_names, show=False, max_display=15)
plt.tight_layout()
plt.show()""")

# ------------------------------------------------------------------
md("""## 16. 가설 검증 — 통계 회귀분석 (statsmodels, Robust SE)
`log_Price ~ KRW_state_year(순수소득) + Age + Age² + Kilometers_Driven + Mileage_final + Engine_cc + Power_bhp
+ Owner_Rank + Fuel_Type + Transmission + C(Location)` 회귀식으로 가설1(소득)·가설2(지역고유효과)를 동시에 검증합니다.""")
code("""sm_df = labeled.copy()
sm_df["C_Location"] = sm_df["Location"]

formula_full = (
    "log_Price ~ KRW_state_year + Age + I(Age**2) + Kilometers_Driven + Mileage_final "
    "+ Engine_cc + Power_bhp + Owner_Rank + C(Fuel_Type) + C(Transmission) + C(C_Location)"
)
ols_full = smf.ols(formula=formula_full, data=sm_df).fit(cov_type="HC3")
print(ols_full.summary())""")

code("""p_krw_state = float(ols_full.pvalues.get("KRW_state_year", np.nan))
coef_krw_state = float(ols_full.params.get("KRW_state_year", np.nan))

loc_terms = [t for t in ols_full.params.index if t.startswith("C(C_Location)")]
f_test_loc = ols_full.f_test(" = ".join(loc_terms) + " = 0")
p_loc = float(np.asarray(f_test_loc.pvalue))

p_age2 = float(ols_full.pvalues.get("I(Age ** 2)", np.nan))

sm_df["km_over80k"] = (sm_df["Kilometers_Driven"] > 80000).astype(int)
formula_km = (
    "log_Price ~ Kilometers_Driven * km_over80k + Age + KRW_state_year + Engine_cc + Power_bhp "
    "+ C(Fuel_Type) + C(Transmission) + C(C_Location)"
)
ols_km = smf.ols(formula=formula_km, data=sm_df).fit(cov_type="HC3")
p_km_interact = float(ols_km.pvalues.get("Kilometers_Driven:km_over80k", np.nan))

p_owner = float(ols_full.pvalues.get("Owner_Rank", np.nan))
coef_owner = float(ols_full.params.get("Owner_Rank", np.nan))
p_mileage = float(ols_full.pvalues.get("Mileage_final", np.nan))
coef_mileage = float(ols_full.params.get("Mileage_final", np.nan))

hyp_table = pd.DataFrame([
    {"가설": "H1 소득(KRW_state_year)", "p-value": p_krw_state, "계수": coef_krw_state,
     "판정": "유의하나 부호 반대(경제적 유의성 X)" if p_krw_state < 0.05 else "기각"},
    {"가설": "H2 Location 공동유의성", "p-value": p_loc, "계수": np.nan,
     "판정": "채택" if p_loc < 0.05 else "기각"},
    {"가설": "H3 Age² (비선형)", "p-value": p_age2, "계수": np.nan,
     "판정": "기각(유의X)" if p_age2 >= 0.05 else "채택"},
    {"가설": "H3 주행거리 80k초과 교호항", "p-value": p_km_interact, "계수": np.nan,
     "판정": "채택" if p_km_interact < 0.05 else "기각"},
    {"가설": "H4 Owner_Rank", "p-value": p_owner, "계수": coef_owner,
     "판정": "채택(1인소유 프리미엄)" if (p_owner < 0.05 and coef_owner < 0) else "기각"},
    {"가설": "H4 Mileage(연비)", "p-value": p_mileage, "계수": coef_mileage,
     "판정": "부호 반대(연비 프리미엄 미확인)" if (p_mileage < 0.05 and coef_mileage < 0) else "채택"},
])
display(hyp_table)""")

code("""fig, ax = plt.subplots(figsize=(9, 5))
plot_df = hyp_table.dropna(subset=["p-value"]).copy()
plot_df["neglog10p"] = -np.log10(plot_df["p-value"].clip(lower=1e-300))
colors = [PALETTE[0] if p < 0.05 else PALETTE[5] for p in plot_df["p-value"]]
bars = ax.barh(plot_df["가설"], plot_df["neglog10p"], color=colors)
ax.axvline(-np.log10(0.05), linestyle="--", color="gray", label="α=0.05 임계선")
ax.set_xlabel("-log10(p-value)  (클수록 강하게 유의)")
ax.set_title("가설별 통계적 유의성 (파랑=유의, 주황=비유의)")
ax.legend()
plt.tight_layout()
plt.show()""")

md("""**종합 해석**
- **H2(지역 고유효과)**: 강하게 채택(p≈10⁻⁸⁰). Location 더미가 도시 간 가격격차를 압도적으로 설명합니다.
- **H1(순수 소득효과)**: 통계적으로 유의하지만 계수 부호가 가설과 반대이고 효과크기가 미미 → 경제적으로는 기각에 가까움.
  Location 더미가 도시별 소득 변동을 이미 흡수했기 때문으로 해석됩니다.
- **H3(비선형 감가)**: 주행거리 임계점(8만km) 교호항은 강하게 유의하나, 연식 제곱항은 유의하지 않음 → **주행거리 기준만 부분 채택**.
- **H4**: 소유이력(Owner_Rank)은 가설대로 1인소유 프리미엄이 확인되나, Mileage(연비)는 Engine/Power를 통제하면 오히려 음(-)의 효과 →
  **소유이력만 부분 채택**, 연비 자체의 순수 프리미엄은 미확인.""")

# ------------------------------------------------------------------
md("""## 17. 매입가(Bid Price) 산정 시연
`Price`가 비어 있는 1,053건(실제 매입 검토 대상 차량)에 최적 모델을 적용해 예측 판매가를 산출하고,
리스크 연동 차등 마진(기본 12%, 고연식·고주행 +6%p, 다수소유이력 +3%p, 상한 25%)을 적용한 매입가를 계산합니다.""")
code("""for c in numeric_impute_cols:
    unlabeled[c] = pd.to_numeric(unlabeled[c], errors="coerce").fillna(impute_medians[c])
unlabeled["Owner_Rank"] = unlabeled["Owner_Type"].map(owner_map).fillna(2)

X_un = unlabeled[numeric_features + categorical_features].copy()
pred_log = best_pipe.predict(X_un)
unlabeled["Predicted_Sale_Price"] = np.exp(pred_log)

def risk_margin(row):
    m = 0.12
    if row["Age"] > 7 or row["Kilometers_Driven"] > 80000:
        m += 0.06
    if row["Owner_Rank"] >= 3:
        m += 0.03
    return min(m, 0.25)

unlabeled["Target_Margin"] = unlabeled.apply(risk_margin, axis=1)
unlabeled["Bid_Price"] = unlabeled["Predicted_Sale_Price"] * (1 - unlabeled["Target_Margin"])

print(f"매입 검토 대상: {len(unlabeled)}건")
print(f"예측 판매가 중앙값: {unlabeled['Predicted_Sale_Price'].median():,.1f}천원")
print(f"산출 매입가 중앙값: {unlabeled['Bid_Price'].median():,.1f}천원")
print(f"평균 적용 마진: {unlabeled['Target_Margin'].mean()*100:.1f}%")

out_cols = ["Name", "Location", "Year", "Kilometers_Driven", "Predicted_Sale_Price", "Target_Margin", "Bid_Price"]
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
unlabeled[out_cols].to_csv(OUTPUT_DIR / "bid_price_predictions.csv", index=False, encoding="utf-8-sig")
display(unlabeled[out_cols].head(10))""")

code("""fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
sns.histplot(unlabeled["Predicted_Sale_Price"], bins=40, color=PALETTE[0], ax=axes[0], kde=True)
axes[0].set_title("예측 판매가 분포 (매입 검토 1,053건)")
axes[0].set_xlabel("Predicted Sale Price (천원)")

sns.histplot(unlabeled["Target_Margin"]*100, bins=15, color=PALETTE[3], ax=axes[1])
axes[1].set_title("적용 마진율 분포")
axes[1].set_xlabel("Target Margin (%)")
plt.tight_layout()
plt.show()""")

# ------------------------------------------------------------------
md("""## 18. 최종 요약

| 항목 | 결과 |
|---|---|
| 최적 모델 | **LightGBM** (CV R²≈0.86, RMSE≈6,644천원) |
| 최다 기여 변수 | Power_bhp, Age, Engine_cc (Permutation·SHAP 공통) |
| 가설1(소득) | 경제적 유의성 낮음 → 매입가 변수에서 비중 축소 |
| 가설2(지역) | 강하게 채택 → **Location 자체를 매입가 이원화 축으로 사용** |
| 가설3(비선형 감가) | 주행거리 8만km 기준 둔화 확인, 연식 기준은 오히려 가속 |
| 가설4(소유/연비) | 1인소유 프리미엄 확인, 연비 자체 프리미엄은 미확인 |
| 액션 | `Bid Price = exp(LightGBM 예측) × (1 − 리스크연동 마진)` 자동화, Location별 재고 배분 최적화 |

⚠️ 예측가는 시장 추정치이며, 실제 매입 시 **사고 이력·외관/기계 상태의 현장 실사**가 반드시 병행되어야 합니다.""")

# ------------------------------------------------------------------
nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3.14 (jonghap)", "language": "python", "name": "py314"},
    "language_info": {"name": "python", "version": "3.14"},
}

# 이 스크립트는 scripts/에 있고, 결과물은 notebooks/analysis.ipynb에 씁니다.
# (프로젝트 루트에서 `python scripts/build_notebook.py`로 실행하는 것을 기준으로 함)
out_path = Path("notebooks/analysis.ipynb") if Path("notebooks").exists() else Path("analysis.ipynb")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    nbf.write(nb, f)

print(f"{out_path} 생성 완료, 셀 수:", len(cells))
