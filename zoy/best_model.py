"""최종 모델: RF + ExtraTrees + XGBoost 확률 평균 + 클래스별 결정 가중치.

8개 모델 비교(5-fold × 시드 3개, macro F1)에서 가장 높았던 조합이다.
  1) 5-fold 로 train OOF 확률을 만든다 → 검증 macro F1 출력
  2) OOF 확률로 클래스별 가중치를 찾는다 (소수 불량을 더 과감하게 예측하도록)
  3) train 전체로 다시 학습 → public+private 예측 → 제출 CSV 저장

실행 (어느 폴더에서든):
    python best_model.py      → zoy/제출_4조.csv
"""
import random
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier  # requirements.txt 에 xgboost 추가 필요

SEED = 42
N_FOLDS = 5
DATA_DIR = Path(__file__).resolve().parent.parent / "학생배포"
OUT_PATH = Path(__file__).resolve().parent / "제출_4조.csv"

ID_COLS = ["shot_id", "id", "Shot"]          # 특징으로 쓰면 실격 — 정렬용으로만
FACTORY_COLS = ["Factory_Temp", "Factory_Humidity"]


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)


# ---------------------------------------------------------------- 전처리
def load_data():
    df = pd.read_csv(DATA_DIR / "data" / "주조공정_입력.csv", header=1)  # 머리글 2줄
    df.columns = df.columns.str.strip()                                  # 'Biscuit_Thickness ' 등 공백
    df = (df.merge(pd.read_csv(DATA_DIR / "분할표.csv"), on="shot_id")
            .merge(pd.read_csv(DATA_DIR / "정답_train.csv"), on="shot_id", how="left"))
    return df.sort_values("shot_id").reset_index(drop=True)


def preprocess(df):
    # 값이 하나뿐인 관리범위 열 8개 (Air/Coolant/Factory *_Min/Max) — 정보 없음
    const = [c for c in df.columns if c not in ID_COLS and df[c].nunique() == 1]
    df = df.drop(columns=const)

    # 공장 온·습도 결측 90행(train 63 · test 27)은 연속 구간 → 센서 정지.
    # 테스트에도 있어 행을 버릴 수 없으므로 생산 순서상 앞 값으로 채우고 결측 표시를 남긴다
    df["factory_missing"] = df[FACTORY_COLS].isna().any(axis=1).astype(int)
    df[FACTORY_COLS] = df[FACTORY_COLS].ffill().bfill()

    # 중복 행·이상값(0, 긴 사이클)은 그대로 둔다:
    #  - test 2,261샷 중 1,305샷이 train 에 값이 똑같은 행이 있다 (같은 샷이 두 번 기록)
    #  - 트리 모델은 이상값에 둔감하고, 같은 유형의 이상 샷이 test 에도 있다
    feats = [c for c in df.columns if c not in ID_COLS + ["split", "label"]]
    return df, feats


# ---------------------------------------------------------------- 모델
def make_models(seed):
    return {
        "RF": RandomForestClassifier(
            n_estimators=500, max_features=0.5, class_weight="balanced_subsample",
            n_jobs=-1, random_state=seed),
        "ExtraTrees": ExtraTreesClassifier(
            n_estimators=500, class_weight="balanced", n_jobs=-1, random_state=seed),
        "XGBoost": XGBClassifier(
            n_estimators=600, learning_rate=0.05, max_depth=8, subsample=0.8,
            colsample_bytree=0.8, tree_method="hist", n_jobs=-1, random_state=seed),
    }


def fit_predict_proba(X_tr, y_tr, X_te, seed):
    """세 모델 확률의 평균. XGBoost 는 class_weight 가 없어 sample_weight 로 균형을 맞춘다."""
    probs = []
    for name, model in make_models(seed).items():
        if name == "XGBoost":
            model.fit(X_tr, y_tr, sample_weight=compute_sample_weight("balanced", y_tr))
        else:
            model.fit(X_tr, y_tr)
        probs.append(model.predict_proba(X_te))
    return np.mean(probs, axis=0)


def tune_class_weights(P, y, n_rounds=3):
    """클래스별로 확률에 곱할 가중치를 좌표 탐색 → macro F1 최대.
    정상이 77% 라 argmax 만 쓰면 소수 불량을 덜 찍는다."""
    w = np.ones(P.shape[1])
    grid = np.exp(np.linspace(-2, 2, 41))
    for _ in range(n_rounds):
        for k in range(len(w)):
            scores = []
            for v in grid:
                w[k] = v
                scores.append(f1_score(y, (P * w).argmax(1), average="macro"))
            w[k] = grid[int(np.argmax(scores))]
    return w


# ---------------------------------------------------------------- 실행
def main():
    set_seed(SEED)
    df, feats = preprocess(load_data())
    is_train = df["split"] == "train"
    X = df.loc[is_train, feats].values
    X_test = df.loc[~is_train, feats].values

    le = LabelEncoder().fit(df.loc[is_train, "label"])
    y = le.transform(df.loc[is_train, "label"])
    print(f"train {X.shape} · test {X_test.shape} · 특징 {len(feats)}개")

    # 1) OOF 확률
    oof = np.zeros((len(y), len(le.classes_)))
    for tr_idx, va_idx in StratifiedKFold(N_FOLDS, shuffle=True, random_state=SEED).split(X, y):
        oof[va_idx] = fit_predict_proba(X[tr_idx], y[tr_idx], X[va_idx], SEED)

    # 2) 클래스별 가중치 — 가중치 자체도 OOF 에 맞춘 것이라 아래 '가중치 적용' 점수는 약간 낙관적
    w = tune_class_weights(oof, y)
    pred = (oof * w).argmax(1)
    print(f"\n[{N_FOLDS}-fold 검증] macro F1  argmax {f1_score(y, oof.argmax(1), average='macro'):.4f}"
          f"  →  가중치 적용 {f1_score(y, pred, average='macro'):.4f}")
    print("클래스 가중치:", dict(zip(le.classes_, np.round(w, 2))))
    print(classification_report(y, pred, target_names=le.classes_, digits=3, zero_division=0))
    print("혼동행렬 (행=실제, 열=예측):")
    print(pd.DataFrame(confusion_matrix(y, pred), index=le.classes_, columns=le.classes_))

    # 3) 전체 학습 → 제출
    P_test = fit_predict_proba(X, y, X_test, SEED)
    sub = pd.DataFrame({"shot_id": df.loc[~is_train, "shot_id"].values,
                        "label": le.inverse_transform((P_test * w).argmax(1))})
    sub.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n저장: {OUT_PATH} ({len(sub)}행)")
    print("예측 분포:", sub["label"].value_counts().to_dict())


if __name__ == "__main__":
    main()
