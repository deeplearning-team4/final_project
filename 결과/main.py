import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.impute import SimpleImputer
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_predict
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler

SEED = 42
TEAM_NAME = "3조"

ID_COLS = ["shot_id", "id", "Shot"]

LABELS = [
    "정상",
    "불량_Short_Shot",
    "불량_Blow_Hole",
    "불량_Exfoliation",
    "불량_Stain",
    "불량_Deformation",
    "기타불량",
]

random.seed(SEED)
np.random.seed(SEED)


def find_base_path():
    here = Path(__file__).resolve().parent

    for path in [here, here.parent / "학생배포"]:
        if (path / "data" / "주조공정_입력.csv").exists():
            return path

    raise FileNotFoundError(
        "data/주조공정_입력.csv 를 찾을 수 없습니다. 학생배포/ 폴더 안에서 실행하세요."
    )


def load_data(base_path):
    raw = pd.read_csv(
        base_path / "data" / "주조공정_입력.csv",
        header=1,
        encoding="utf-8-sig",
    )
    raw.columns = raw.columns.str.strip()

    split = pd.read_csv(base_path / "분할표.csv", encoding="utf-8-sig")
    labels = pd.read_csv(base_path / "정답_train.csv", encoding="utf-8-sig")
    labels["label"] = labels["label"].str.strip()

    train = raw.merge(labels, on="shot_id", how="inner", validate="one_to_one")

    target_ids = split.loc[split["split"].isin(["public", "private"]), ["shot_id"]]
    target = target_ids.merge(raw, on="shot_id", how="left", validate="one_to_one")

    if len(train) != 5274:
        raise ValueError(f"train 이 5,274샷이 아닙니다: {len(train)}샷")

    if len(target) != 2261:
        raise ValueError(f"제출 대상이 2,261샷이 아닙니다: {len(target)}샷")

    return train, target


def select_features(train):
    candidate_cols = [col for col in train.columns if col not in ID_COLS + ["label"]]

    # 값이 하나뿐인 열(Min/Max 8개)은 정보가 없어서 뺀다
    constant_cols = [
        col for col in candidate_cols if train[col].nunique(dropna=True) <= 1
    ]

    feature_cols = [col for col in candidate_cols if col not in constant_cols]

    return feature_cols, constant_cols


def make_model():
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", MinMaxScaler()),
            (
                "knn",
                KNeighborsClassifier(
                    n_neighbors=15,
                    weights="distance",
                    p=1,
                ),
            ),
        ]
    )


def report_cv(X, y):
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=SEED)
    scores = []

    for repeat, (train_idx, valid_idx) in enumerate(cv.split(X, y)):
        model = make_model().fit(X.iloc[train_idx], y.iloc[train_idx])
        pred = model.predict(X.iloc[valid_idx])
        scores.append(
            f1_score(
                y.iloc[valid_idx],
                pred,
                labels=LABELS,
                average="macro",
                zero_division=0,
            )
        )

    print(
        f"랜덤 5-fold x 3회 Macro F1: {np.mean(scores):.4f} ± {np.std(scores):.4f} "
        f"(최소 {np.min(scores):.4f} / 최대 {np.max(scores):.4f})"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--skip-cv", action="store_true")
    args = parser.parse_args()

    base_path = find_base_path()
    train, target = load_data(base_path)
    feature_cols, constant_cols = select_features(train)

    X = train[feature_cols]
    y = train["label"]

    print(f"train: {len(train)}샷 / 제출 대상: {len(target)}샷")
    print(f"삭제한 상수 열 {len(constant_cols)}개: {constant_cols}")
    print(f"사용한 변수 {len(feature_cols)}개")

    if not args.skip_cv:
        report_cv(X, y)

    model = make_model().fit(X, y)

    submission = pd.DataFrame(
        {
            "shot_id": target["shot_id"].astype("int64"),
            "label": model.predict(target[feature_cols]),
        }
    )

    if submission["shot_id"].duplicated().any():
        raise ValueError("shot_id 가 중복되어 있습니다.")

    if not submission["label"].isin(LABELS).all():
        raise ValueError("허용되지 않은 라벨이 있습니다.")

    output_path = args.output or base_path / f"제출_{TEAM_NAME}.csv"
    submission.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("\n[예측 라벨 분포]")
    print(submission["label"].value_counts().to_string())
    print(f"\n저장 위치: {output_path}")


if __name__ == "__main__":
    main()
