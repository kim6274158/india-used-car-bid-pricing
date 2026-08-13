
# -*- coding: utf-8 -*-
import re
import sys
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

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

# 프로젝트 루트 기준 data/, outputs/ 폴더 사용 (scripts/analysis2.py 위치 기준 상대경로)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
CAR_PATH = DATA_DIR / "Car.csv"
INCOME_PATH = DATA_DIR / "지역별소득수준_krw.csv"

pd.set_option("display.width", 140)

# =====================================================================
# 1. LOAD
# =====================================================================
car = pd.read_csv(CAR_PATH)
inc = pd.read_csv(INCOME_PATH)

n_rows_car, n_cols_car = car.shape
n_rows_inc, n_cols_inc = inc.shape

car_locations = set(car["Location"].unique())
inc_locations = set(inc["Location"].unique())
inc_states = sorted(inc["State"].unique())

# =====================================================================
# 2. NUMERIC PARSING (Mileage / Engine / Power / New_Price)
# =====================================================================
num_re = re.compile(r"([0-9]+\.?[0-9]*)")


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

# CNG/LPG 차량은 km/kg 단위 사용. 발열량 기준 액체연료 환산계수(1kg CNG ~= 1.4L 가솔린 등가) 적용해
# Petrol/Diesel(kmpl)과 동일 척도로 정규화 -> Mileage_final(등가 kmpl)
CNG_LPG_TO_KMPL_FACTOR = 1.4
car["Mileage_final"] = car["Mileage_val"]
mask_kg = car["Mileage_unit"] == "km/kg"
car.loc[mask_kg, "Mileage_final"] = car.loc[mask_kg, "Mileage_val"] * CNG_LPG_TO_KMPL_FACTOR
# 0.0 kmpl (측정 불가/전기차 등 이상치)는 결측으로 처리 후 중앙값 대체
car.loc[car["Mileage_final"] <= 0, "Mileage_final"] = np.nan

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
        return num * 10000.0  # crore -> 천 단위(New_Price 원단위: 만원 x100 = 천원 스케일 맞춤용, Lakh=10만루피 기준)
    if "lakh" in sl:
        return num * 100.0
    return num


car["New_Price_thousand"] = car.get("New_Price", pd.Series(dtype=float)).apply(parse_new_price)

# =====================================================================
# 3. STATE·YEAR 매핑 기반 정밀 병합
#    - Location -> State 매핑 (소득 데이터 기준)
#    - 차량 Year == 소득 Year 정확히 일치하는 시점의 지역소득(KRW) 사용
#    - 소득 데이터 범위(2011~2020) 밖의 차량 연식(<2011)은 State별 "가장 최신"
#      소득 데이터로 폴백하여 결측 방지
# =====================================================================
loc2state = inc[["Location", "State"]].drop_duplicates().set_index("Location")["State"].to_dict()
car["State"] = car["Location"].map(loc2state)

inc_year_min, inc_year_max = int(inc["Year"].min()), int(inc["Year"].max())

# (a) 정확한 Location+Year 매치
exact = inc[["Location", "Year", "KRW"]].rename(columns={"KRW": "KRW_exact"})
merged = car.merge(exact, how="left", on=["Location", "Year"])

# (b) 매치 실패(연식이 소득데이터 범위를 벗어난 경우, 대부분 Year<2011) -> Location별 최신(2020) KRW로 폴백
latest_by_loc = (
    inc.sort_values("Year").groupby("Location", as_index=False).last()[["Location", "KRW", "Year"]]
    .rename(columns={"KRW": "KRW_latest", "Year": "KRW_latest_year"})
)
merged = merged.merge(latest_by_loc, how="left", on="Location")

merged["KRW_source"] = np.where(merged["KRW_exact"].notna(), "exact_year", "fallback_latest")
merged["KRW"] = merged["KRW_exact"].where(merged["KRW_exact"].notna(), merged["KRW_latest"])

n_fallback = int((merged["KRW_source"] == "fallback_latest").sum())
n_exact = int((merged["KRW_source"] == "exact_year").sum())

# State 단위(도시 간 평균) 소득 지표: 동일 State 내 여러 도시가 있을 때 "순수 소득수준" 통제용
state_year_income = inc.groupby(["State", "Year"], as_index=False)["KRW"].mean().rename(columns={"KRW": "KRW_state_year"})
merged = merged.merge(state_year_income, how="left", left_on=["State", "Year"], right_on=["State", "Year"])
# State-Year 폴백도 동일 로직(연식이 범위 밖이면 State 최신 연도 평균으로 대체)
state_latest = (
    inc.groupby(["State", "Year"], as_index=False)["KRW"].mean()
    .sort_values("Year").groupby("State", as_index=False).last()[["State", "KRW"]]
    .rename(columns={"KRW": "KRW_state_latest"})
)
merged = merged.merge(state_latest, how="left", on="State")
merged["KRW_state_year"] = merged["KRW_state_year"].where(merged["KRW_state_year"].notna(), merged["KRW_state_latest"])

merge_unmatched = int(merged["KRW"].isna().sum())  # State 매핑조차 안 되는 완전 미매치 건수

# =====================================================================
# 4. 결측치 처리 / 파생변수 / 타깃 로그변환
# =====================================================================
TRANSACTION_YEAR = inc_year_max  # 소득데이터 최신연도(2020)를 사실상 거래(관측) 기준연도로 사용
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

# 학습/평가용: Price가 존재하는 행만 (원본 6200건)
labeled = merged[merged["Price"].notna() & (merged["Price"] > 0)].copy()
labeled["log_Price"] = np.log(labeled["Price"])

# 매입 대상(Price 미기재, 1053건) - 최종 모델로 적정 매입가 산정 시연에 사용
unlabeled = merged[merged["Price"].isna()].copy()

merged_shape = merged.shape

# =====================================================================
# 5. EDA 통계
# =====================================================================
eda = {}
eda["krw_price_ratio_median"] = float(labeled["Price"].median() / labeled["KRW"].median())
eda["loc_price_median"] = labeled.groupby("Location")["Price"].median().sort_values(ascending=False)
eda["loc_krw_median"] = labeled.groupby("Location")["KRW"].median().sort_values(ascending=False)
loc_corr = eda["loc_price_median"].corr(eda["loc_krw_median"])
eda["location_level_income_price_corr"] = float(loc_corr)

labeled["km_bin"] = pd.cut(
    labeled["Kilometers_Driven"], bins=[-1, 20000, 50000, 80000, 120000, 10_000_000],
    labels=["<20k", "20-50k", "50-80k", "80-120k", "120k+"]
)
eda["km_bin_median_price"] = labeled.groupby("km_bin", observed=True)["Price"].median()
km_bins_pct_change = eda["km_bin_median_price"].pct_change() * 100

labeled["age_bin"] = pd.cut(
    labeled["Age"], bins=[-1, 3, 5, 7, 10, 100],
    labels=["0-3y", "4-5y", "6-7y", "8-10y", "10y+"]
)
eda["age_bin_median_price"] = labeled.groupby("age_bin", observed=True)["Price"].median()
age_bins_pct_change = eda["age_bin_median_price"].pct_change() * 100

eda["owner_median_price"] = labeled.groupby("Owner_Type")["Price"].median().reindex(
    ["First", "Second", "Third", "Fourth & Above"]
)
eda["fuel_mileage_price"] = labeled.groupby("Fuel_Type").agg(
    median_price=("Price", "median"), median_mileage=("Mileage_final", "median"), n=("Price", "size")
)

# =====================================================================
# 6. 모델링
# =====================================================================
numeric_features = ["KRW", "Age", "Kilometers_Driven", "Mileage_final", "Engine_cc", "Power_bhp", "Seats", "Owner_Rank"]
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
    ("RandomForest", RandomForestRegressor(n_estimators=300, max_depth=None, min_samples_leaf=2, random_state=42, n_jobs=-1)),
    ("GradientBoosting", GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, random_state=42)),
    ("XGBoost", xgb.XGBRegressor(n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.8,
                                  colsample_bytree=0.8, random_state=42, verbosity=0)),
    ("LightGBM", lgb.LGBMRegressor(n_estimators=400, max_depth=-1, learning_rate=0.05, num_leaves=31,
                                    random_state=42, verbosity=-1)),
    ("CatBoost", cb.CatBoostRegressor(n_estimators=400, depth=6, learning_rate=0.05, verbose=0, random_state=42)),
]

kf = KFold(n_splits=5, shuffle=True, random_state=42)
results = []
fitted_pipes = {}

for name, model in models:
    pipe = Pipeline([("pre", preprocessor), ("model", model)])
    y_pred_log_cv = cross_val_predict(pipe, X, y, cv=kf, n_jobs=-1)
    y_pred_cv = np.exp(y_pred_log_cv)
    r2 = r2_score(y_true_price, y_pred_cv)
    rmse = float(np.sqrt(mean_squared_error(y_true_price, y_pred_cv)))
    mae = float(mean_absolute_error(y_true_price, y_pred_cv))

    # in-sample(전체 적합) 성능도 같이 측정해 과적합 갭 확인
    pipe_full = Pipeline([("pre", preprocessor), ("model", model)])
    pipe_full.fit(X, y)
    y_pred_train = np.exp(pipe_full.predict(X))
    r2_train = r2_score(y_true_price, y_pred_train)
    rmse_train = float(np.sqrt(mean_squared_error(y_true_price, y_pred_train)))

    overfit_gap_rmse_pct = (rmse - rmse_train) / rmse * 100 if rmse > 0 else 0.0

    results.append({
        "model": name, "r2_cv": float(r2), "rmse_cv": rmse, "mae_cv": mae,
        "r2_train": float(r2_train), "rmse_train": rmse_train,
        "overfit_gap_pct": float(overfit_gap_rmse_pct),
    })
    fitted_pipes[name] = pipe_full

results_sorted = sorted(results, key=lambda x: x["rmse_cv"])
best = results_sorted[0]
best_name = best["model"]
best_pipe = fitted_pipes[best_name]

# =====================================================================
# 7. 변수 중요도 (Permutation + Native + SHAP)
# =====================================================================
ohe = best_pipe.named_steps["pre"].named_transformers_["cat"].named_steps["ohe"]
cat_names = list(ohe.get_feature_names_out(categorical_features))
feat_names = numeric_features + cat_names

perm = permutation_importance(best_pipe, X, y, n_repeats=8, random_state=42, n_jobs=-1)
perm_imp = sorted(zip(feat_names, perm.importances_mean), key=lambda t: t[1], reverse=True)

# SHAP (베스트 모델이 트리기반일 때 TreeExplainer, 아니면 샘플 기반 Explainer)
shap_imp = []
try:
    X_trans = best_pipe.named_steps["pre"].transform(X)
    model_step = best_pipe.named_steps["model"]
    sample_idx = np.random.RandomState(42).choice(len(X_trans), size=min(1000, len(X_trans)), replace=False)
    X_sample = X_trans[sample_idx]
    if best_name in ("RandomForest", "GradientBoosting", "XGBoost", "LightGBM", "CatBoost"):
        explainer = shap.TreeExplainer(model_step)
        sv = explainer.shap_values(X_sample)
    else:
        explainer = shap.Explainer(model_step, X_trans[:200])
        sv = explainer(X_sample).values
    mean_abs_shap = np.abs(sv).mean(axis=0)
    shap_imp = sorted(zip(feat_names, mean_abs_shap), key=lambda t: t[1], reverse=True)
except Exception as e:
    shap_imp = [("SHAP 계산 실패", str(e))]

# =====================================================================
# 8. 가설 검증 (statsmodels OLS, robust SE)
# =====================================================================
sm_df = labeled.copy()
sm_df["C_Location"] = sm_df["Location"]

# H1+H2: log_Price ~ KRW_state_year(순수 소득) + Age + Age^2 + Kilometers_Driven + Mileage_final
#         + Engine_cc + Power_bhp + Owner_Rank + Fuel/Transmission + C(Location)  [Location은 도시고유효과]
formula_full = (
    "log_Price ~ KRW_state_year + Age + I(Age**2) + Kilometers_Driven + Mileage_final "
    "+ Engine_cc + Power_bhp + Owner_Rank + C(Fuel_Type) + C(Transmission) + C(C_Location)"
)
ols_full = smf.ols(formula=formula_full, data=sm_df).fit(cov_type="HC3")

p_krw_state = float(ols_full.pvalues.get("KRW_state_year", np.nan))
coef_krw_state = float(ols_full.params.get("KRW_state_year", np.nan))

loc_terms = [t for t in ols_full.params.index if t.startswith("C(C_Location)")]
if loc_terms:
    hyp_str = " = ".join(loc_terms) + " = 0"
    f_test_loc = ols_full.f_test(hyp_str)
    p_loc = float(np.asarray(f_test_loc.pvalue))
else:
    p_loc = np.nan

p_age2 = float(ols_full.pvalues.get("I(Age ** 2)", np.nan))
coef_age = float(ols_full.params.get("Age", np.nan))
coef_age2 = float(ols_full.params.get("I(Age ** 2)", np.nan))

p_owner = float(ols_full.pvalues.get("Owner_Rank", np.nan))
coef_owner = float(ols_full.params.get("Owner_Rank", np.nan))

# 주행거리 구간 비선형성: piecewise dummy (80k km 초과 여부) 상호작용 유의성
sm_df["km_over80k"] = (sm_df["Kilometers_Driven"] > 80000).astype(int)
formula_km = (
    "log_Price ~ Kilometers_Driven * km_over80k + Age + KRW_state_year + Engine_cc + Power_bhp "
    "+ C(Fuel_Type) + C(Transmission) + C(C_Location)"
)
ols_km = smf.ols(formula=formula_km, data=sm_df).fit(cov_type="HC3")
p_km_interact = float(ols_km.pvalues.get("Kilometers_Driven:km_over80k", np.nan))

# Mileage(연비) 유의성
p_mileage = float(ols_full.pvalues.get("Mileage_final", np.nan))
coef_mileage = float(ols_full.params.get("Mileage_final", np.nan))

ALPHA = 0.05
h1_accept = (not np.isnan(p_krw_state)) and (p_krw_state < ALPHA)
h2_accept = (not np.isnan(p_loc)) and (p_loc < ALPHA)
h3_accept = (not np.isnan(p_age2) and p_age2 < ALPHA) or (not np.isnan(p_km_interact) and p_km_interact < ALPHA)
h4_accept = (not np.isnan(p_owner) and p_owner < ALPHA and coef_owner < 0)

# =====================================================================
# 9. 매입가 산정 시연: unlabeled(1053건) 예측 + Bid Price
# =====================================================================
bid_report = {}
if len(unlabeled) > 0:
    for c in numeric_impute_cols:
        unlabeled[c] = pd.to_numeric(unlabeled[c], errors="coerce").fillna(impute_medians[c])
    unlabeled["Owner_Rank"] = unlabeled["Owner_Type"].map(owner_map).fillna(2)
    X_un = unlabeled[numeric_features + categorical_features].copy()
    pred_log = best_pipe.predict(X_un)
    unlabeled["Predicted_Sale_Price"] = np.exp(pred_log)

    def risk_margin(row):
        # 감가 급락 구간(고연식/고주행)일수록 보수적(고마진) 매입가 적용
        m = 0.12
        if row["Age"] > 7 or row["Kilometers_Driven"] > 80000:
            m += 0.06
        if row["Owner_Rank"] >= 3:
            m += 0.03
        return min(m, 0.25)

    unlabeled["Target_Margin"] = unlabeled.apply(risk_margin, axis=1)
    unlabeled["Bid_Price"] = unlabeled["Predicted_Sale_Price"] * (1 - unlabeled["Target_Margin"])

    bid_report["n"] = int(len(unlabeled))
    bid_report["predicted_sale_price_median"] = float(unlabeled["Predicted_Sale_Price"].median())
    bid_report["bid_price_median"] = float(unlabeled["Bid_Price"].median())
    bid_report["margin_mean"] = float(unlabeled["Target_Margin"].mean())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    unlabeled[["Name", "Location", "Year", "Kilometers_Driven", "Predicted_Sale_Price", "Target_Margin", "Bid_Price"]].to_csv(
        OUTPUT_DIR / "bid_price_predictions.csv", index=False, encoding="utf-8-sig"
    )

# =====================================================================
# 10. 리포트 출력
# =====================================================================
out = {
    "shapes": {
        "car_raw": [n_rows_car, n_cols_car],
        "income_raw": [n_rows_inc, n_cols_inc],
        "merged": list(merged_shape),
        "labeled_for_modeling": list(labeled.shape),
        "unlabeled_for_bidding": list(unlabeled.shape),
    },
    "locations": {
        "car_locations": sorted(car_locations),
        "income_locations": sorted(inc_locations),
        "income_states": inc_states,
        "n_car_locations": len(car_locations),
        "n_income_locations": len(inc_locations),
        "n_income_states": len(inc_states),
    },
    "merge_quality": {
        "n_exact_year_match": n_exact,
        "n_fallback_latest": n_fallback,
        "n_fully_unmatched": merge_unmatched,
    },
    "results": results_sorted,
    "best_model": best,
    "permutation_importance_top10": [(f, float(v)) for f, v in perm_imp[:10]],
    "shap_importance_top10": [(f, float(v) if isinstance(v, (int, float, np.floating)) else v) for f, v in shap_imp[:10]],
    "hypothesis": {
        "h1_krw_state_pvalue": p_krw_state, "h1_krw_state_coef": coef_krw_state, "h1_accept": bool(h1_accept),
        "h2_location_joint_pvalue": p_loc, "h2_accept": bool(h2_accept),
        "h3_age2_pvalue": p_age2, "h3_age_coef": coef_age, "h3_age2_coef": coef_age2,
        "h3_km_interact_pvalue": p_km_interact, "h3_accept": bool(h3_accept),
        "h4_owner_pvalue": p_owner, "h4_owner_coef": coef_owner,
        "h4_mileage_pvalue": p_mileage, "h4_mileage_coef": coef_mileage, "h4_accept": bool(h4_accept),
    },
    "eda": {
        "krw_price_ratio_median": eda["krw_price_ratio_median"],
        "location_level_income_price_corr": eda["location_level_income_price_corr"],
        "loc_price_median": eda["loc_price_median"].to_dict(),
        "loc_krw_median": eda["loc_krw_median"].to_dict(),
        "km_bin_median_price": {str(k): float(v) for k, v in eda["km_bin_median_price"].items()},
        "km_bin_pct_change": {str(k): (float(v) if pd.notna(v) else None) for k, v in km_bins_pct_change.items()},
        "age_bin_median_price": {str(k): float(v) for k, v in eda["age_bin_median_price"].items()},
        "age_bin_pct_change": {str(k): (float(v) if pd.notna(v) else None) for k, v in age_bins_pct_change.items()},
        "owner_median_price": {str(k): (float(v) if pd.notna(v) else None) for k, v in eda["owner_median_price"].items()},
    },
    "bid_report": bid_report,
    "impute_medians": impute_medians,
}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_DIR / "analysis_summary.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(json.dumps(out, ensure_ascii=False, indent=2))
print("\nSAVED:", OUTPUT_DIR / "analysis_summary.json")
