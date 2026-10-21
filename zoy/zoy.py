"""주조공정 데이터 전처리.

학생배포/ 폴더에서 실행한다고 가정 (상대경로). 원본 CSV 는 읽기만 하고 수정·저장하지 않는다.
    cd 학생배포 && python ../zoy/zoy.py
"""
import numpy as np
import pandas as pd

INPUT_PATH = "data/주조공정_입력.csv"
SPLIT_PATH = "분할표.csv"
LABEL_PATH = "정답_train.csv"

# 식별 열 — 특징으로 쓰면 실격. 정렬·그룹용으로만 쓴다
ID_COLS = ["shot_id", "id", "Shot"]

# 문제 2: 모든 행에서 값이 하나뿐인 관리범위 열 (정보 없음)
CONST_COLS = [
    "Air_Pressure_Min", "Air_Pressure_Max",
    "Coolant_Temp_Min", "Coolant_Temp_Max",
    "Factory_Temp_Min", "Factory_Temp_Max",
    "Factory_Humidity_Min", "Factory_Humidity_Max",
]

# 문제 3: 같은 90행에서 함께 비는 공장 환경 센서
FACTORY_COLS = ["Factory_Temp", "Factory_Humidity"]

# 문제 4 판단 기준: 정상 가동이면 0 이 나올 수 없는 열, 사이클 시간 상한(정상 약 22초)
ZERO_INVALID_COLS = ["High_Velocity", "Rapid_Rise_Time", "Pressure_Rise_Time", "Biscuit_Thickness"]
CYCLE_TIME_MAX = 40
CLIP_Q = (0.005, 0.995)


def load_raw():
    """문제 1: 머리글 2줄(Process/Sensor 묶음 + 열 이름), 열 이름 앞뒤 공백."""
    df = pd.read_csv(INPUT_PATH, header=1)
    df.columns = df.columns.str.strip()
    split = pd.read_csv(SPLIT_PATH)
    label = pd.read_csv(LABEL_PATH)
    df = df.merge(split, on="shot_id", how="left").merge(label, on="shot_id", how="left")
    return df.sort_values("shot_id").reset_index(drop=True)


def add_pair_group(df):
    """문제 6: 같은 Shot 번호가 연속된 두 행은 공정·센서값이 완전히 같다 (2,918쌍).
    무작위 분할 시 짝이 train/valid 로 갈라지면 점수가 부풀려지므로 그룹 번호를 붙인다.
    (짝의 정답을 특징으로 끌어다 쓰는 용도로는 절대 쓰지 않는다)"""
    new_group = df["Shot"] != df["Shot"].shift()
    df["group"] = new_group.cumsum()
    return df


def fill_factory(df):
    """문제 3: 결측은 shot_id 6914~7067 구간에 몰려 있다 → 센서 정지로 판단.
    테스트에도 있으므로 행을 버리지 않고, 생산 순서상 앞 값으로 채운 뒤 결측 표시를 남긴다."""
    df["factory_missing"] = df[FACTORY_COLS].isna().any(axis=1).astype(int)
    df[FACTORY_COLS] = df[FACTORY_COLS].ffill().bfill()
    return df


def flag_abnormal(df):
    """문제 4: 설비 정지·시운전으로 보이는 샷 표시."""
    zero = (df[ZERO_INVALID_COLS] == 0).any(axis=1)
    long_cycle = df["Cycle_Time"] > CYCLE_TIME_MAX
    df["abnormal_shot"] = (zero | long_cycle).astype(int)
    return df


def feature_columns(df):
    drop = set(ID_COLS + CONST_COLS + ["split", "label", "group"])
    return [c for c in df.columns if c not in drop]


def fit_clip_bounds(X_train):
    """극단값 상·하한은 train 에서만 계산한다 (테스트 정보 누설 방지)."""
    return X_train.quantile(CLIP_Q[0]), X_train.quantile(CLIP_Q[1])


def preprocess():
    df = load_raw()
    df = add_pair_group(df)
    df = df.drop(columns=CONST_COLS)
    df = fill_factory(df)
    df = flag_abnormal(df)

    feats = feature_columns(df)
    is_train = df["split"] == "train"
    train, test = df[is_train], df[~is_train]

    # 문제 4: 이상 샷은 train 에서만 뺀다. 테스트는 예측해야 하므로 clip 으로 처리
    train = train[train["abnormal_shot"] == 0]

    lo, hi = fit_clip_bounds(train[feats])
    flag_cols = ["factory_missing", "abnormal_shot", "Product_Type"]
    clip_cols = [c for c in feats if c not in flag_cols]
    X_train = train[feats].copy()
    X_test = test[feats].copy()
    X_train[clip_cols] = X_train[clip_cols].clip(lo[clip_cols], hi[clip_cols], axis=1)
    X_test[clip_cols] = X_test[clip_cols].clip(lo[clip_cols], hi[clip_cols], axis=1)

    return {
        "X_train": X_train.reset_index(drop=True),
        "y_train": train["label"].reset_index(drop=True),
        "groups": train["group"].reset_index(drop=True),        # GroupKFold 용
        "train_shot_id": train["shot_id"].reset_index(drop=True),  # 시간순 분할용
        "X_test": X_test.reset_index(drop=True),
        "test_shot_id": test["shot_id"].reset_index(drop=True),
        "test_split": test["split"].reset_index(drop=True),
    }


if __name__ == "__main__":
    d = preprocess()
    print("X_train", d["X_train"].shape, "| X_test", d["X_test"].shape)
    print("특징", len(d["X_train"].columns), "개:", list(d["X_train"].columns))
    print("결측 남음 — train", int(d["X_train"].isna().sum().sum()), "/ test", int(d["X_test"].isna().sum().sum()))
    print("라벨 분포:", d["y_train"].value_counts().to_dict())
    print("그룹 수:", d["groups"].nunique(), "(행", len(d["groups"]), ")")
    print("테스트 이상샷:", int(d["X_test"]["abnormal_shot"].sum()), "| 테스트 결측 채움:", int(d["X_test"]["factory_missing"].sum()))
