"""풍속 데이터로 세 예측 방법을 학습하고 2024년 12월을 평가한다."""

import csv
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestRegressor


BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "wind_dataset.csv"
OUTPUT_PATH = BASE_DIR / "predictions.csv"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
FEATURE_COLUMNS = [
    "wind_speed_ms",
    "wind_speed_1h_before_ms",
    "wind_speed_2h_before_ms",
    "temperature_C",
    "humidity_pct",
]
TARGET_COLUMN = "target_wind_speed_ms"
OUTPUT_COLUMNS = [
    "prediction_time",
    "target_time",
    "actual_wind_speed_ms",
    "persistence_prediction_ms",
    "linear_regression_prediction_ms",
    "random_forest_prediction_ms",
]


def read_dataset() -> list[dict[str, str]]:
    """데이터를 시간순으로 읽는다."""
    with DATASET_PATH.open("r", encoding="utf-8-sig", newline="") as dataset_file:
        rows = list(csv.DictReader(dataset_file))
    rows.sort(key=lambda row: datetime.strptime(row["target_time"], TIME_FORMAT))
    return rows


def to_matrix(rows: list[dict[str, str]]) -> tuple[np.ndarray, np.ndarray]:
    """행에서 입력 행렬과 정답 벡터를 만든다."""
    features = np.array(
        [[float(row[column]) for column in FEATURE_COLUMNS] for row in rows],
        dtype=float,
    )
    targets = np.array([float(row[TARGET_COLUMN]) for row in rows], dtype=float)
    return features, targets


def main() -> None:
    rows = read_dataset()
    train_rows = []
    evaluation_rows = []
    for row in rows:
        target_time = datetime.strptime(row["target_time"], TIME_FORMAT)
        if datetime(2023, 1, 1) <= target_time < datetime(2024, 12, 1):
            train_rows.append(row)
        elif datetime(2024, 12, 1) <= target_time < datetime(2025, 1, 1):
            evaluation_rows.append(row)

    if not train_rows or not evaluation_rows:
        raise ValueError("학습 또는 평가 구간에 사용할 행이 없습니다.")

    train_features, train_targets = to_matrix(train_rows)
    evaluation_features, evaluation_targets = to_matrix(evaluation_rows)

    design_matrix = np.column_stack(
        (np.ones(len(train_features)), train_features)
    )
    coefficients, _, _, _ = np.linalg.lstsq(
        design_matrix, train_targets, rcond=None
    )
    evaluation_design = np.column_stack(
        (np.ones(len(evaluation_features)), evaluation_features)
    )
    regression_predictions = evaluation_design @ coefficients
    regression_predictions = np.maximum(regression_predictions, 0)
    random_forest = RandomForestRegressor(
        n_estimators=100,
        max_depth=6,
        min_samples_leaf=5,
        random_state=42,
    )
    random_forest.fit(train_features, train_targets)
    random_forest_predictions = np.maximum(
        random_forest.predict(evaluation_features), 0
    )
    persistence_predictions = evaluation_features[:, 0]

    regression_mae = np.mean(
        np.abs(evaluation_targets - regression_predictions)
    )
    persistence_mae = np.mean(
        np.abs(evaluation_targets - persistence_predictions)
    )
    random_forest_mae = np.mean(
        np.abs(evaluation_targets - random_forest_predictions)
    )

    output_rows = []
    for     row, actual, persistence, regression, random_forest_prediction in zip(
        evaluation_rows,
        evaluation_targets,
        persistence_predictions,
        regression_predictions,
        random_forest_predictions,
    ):
        output_rows.append(
            {
                "prediction_time": row["prediction_time"],
                "target_time": row["target_time"],
                "actual_wind_speed_ms": f"{actual:.6f}",
                "persistence_prediction_ms": f"{persistence:.6f}",
                "linear_regression_prediction_ms": f"{regression:.6f}",
                "random_forest_prediction_ms": f"{random_forest_prediction:.6f}",
            }
        )

    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"학습 행수: {len(train_rows)}")
    print(f"평가 행수: {len(evaluation_rows)}")
    print(f"현재 풍속 유지 MAE: {persistence_mae:.6f} m/s")
    print(f"선형 회귀 MAE: {regression_mae:.6f} m/s")
    print(f"랜덤포레스트 MAE: {random_forest_mae:.6f} m/s")
    print(
        "선형 회귀 대비 랜덤포레스트 MAE 변화: "
        f"{random_forest_mae - regression_mae:+.6f} m/s"
    )
    print(
        "기준 대비 랜덤포레스트 MAE 변화: "
        f"{random_forest_mae - persistence_mae:+.6f} m/s"
    )
    print("첫 평가 결과:")
    print(output_rows[0])


if __name__ == "__main__":
    main()
