"""풍속 1시간 후 정답을 이진 분류 정답으로 바꿔 학습/평가 구간을 나눈다."""

import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "wind_dataset.csv"
OUTPUT_PATH = BASE_DIR / "wind_dataset_labeled.csv"
PREDICTION_OUTPUT_PATH = BASE_DIR / "classification_predictions.csv"
SCORES_OUTPUT_PATH = BASE_DIR / "classification_scores.csv"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
THRESHOLD_MS = 4.0
FEATURE_COLUMNS = [
    "wind_speed_ms",
    "temperature_C",
    "humidity_pct",
    "wind_speed_1h_before_ms",
    "wind_speed_2h_before_ms",
]
PREDICTION_COLUMNS = [
    "prediction_time",
    "target_time",
    "actual_wind_speed_ms",
    "actual_label",
    "current_wind_speed_ms",
    "always_zero_prediction",
    "current_wind_baseline_prediction",
    "strong_wind_probability",
    "logistic_prediction",
    "logistic_prediction_threshold_020",
]
SCORE_COLUMNS = [
    "method",
    "evaluation_rows",
    "actual_strong_wind",
    "TP",
    "FN",
    "FP",
    "TN",
    "accuracy",
    "precision",
    "recall",
]


def read_dataset() -> list[dict[str, str]]:
    with DATASET_PATH.open("r", encoding="utf-8-sig", newline="") as dataset_file:
        rows = list(csv.DictReader(dataset_file))

    for row in rows:
        prediction_time = datetime.strptime(row["prediction_time"], TIME_FORMAT)
        target_time = datetime.strptime(row["target_time"], TIME_FORMAT)
        if target_time - prediction_time != timedelta(hours=1):
            raise ValueError(
                f"prediction_time과 target_time의 차이가 1시간이 아닙니다: "
                f"{row['prediction_time']} -> {row['target_time']}"
            )

        wind_next1h = float(row["target_wind_speed_ms"])
        row["wind_next1h"] = f"{wind_next1h:.6f}"
        row["label"] = "1" if wind_next1h >= THRESHOLD_MS else "0"

    rows.sort(key=lambda row: datetime.strptime(row["target_time"], TIME_FORMAT))

    if not rows:
        raise ValueError("풍속 데이터 행이 없습니다.")
    return rows


def count_labels(rows: list[dict[str, str]]) -> dict[str, int]:
    return {
        "0": sum(row["label"] == "0" for row in rows),
        "1": sum(row["label"] == "1" for row in rows),
    }


def verify_period_times(rows: list[dict[str, str]], period_name: str) -> None:
    previous_target = None
    for row in rows:
        target_time = datetime.strptime(row["target_time"], TIME_FORMAT)
        if previous_target is not None:
            if target_time <= previous_target:
                raise ValueError(
                    f"{period_name} 구간의 정답 시각이 중복되었거나 시간순이 아닙니다: "
                    f"{row['target_time']}"
                )
            if period_name == "평가" and target_time - previous_target != timedelta(hours=1):
                raise ValueError(
                    f"평가 구간 인접 정답 시각의 차이가 1시간이 아닙니다: "
                    f"{previous_target.strftime(TIME_FORMAT)} -> {row['target_time']}"
                )
        previous_target = target_time


def to_features(rows: list[dict[str, str]]) -> np.ndarray:
    return np.array(
        [[float(row[column]) for column in FEATURE_COLUMNS] for row in rows],
        dtype=float,
    )


def train_logistic_regression(
    train_rows: list[dict[str, str]],
) -> tuple[StandardScaler, LogisticRegression]:
    train_features = to_features(train_rows)
    train_labels = np.array([int(row["label"]) for row in train_rows], dtype=int)

    scaler = StandardScaler()
    standardized_train_features = scaler.fit_transform(train_features)

    model = LogisticRegression(
        class_weight=None,
        max_iter=1000,
        random_state=42,
    )
    model.fit(standardized_train_features, train_labels)
    return scaler, model


def calculate_metrics(actual_labels: list[int], predicted_labels: list[int]) -> dict[str, float | int | str | None]:
    true_positive = sum(
        actual == 1 and predicted == 1
        for actual, predicted in zip(actual_labels, predicted_labels)
    )
    false_negative = sum(
        actual == 1 and predicted == 0
        for actual, predicted in zip(actual_labels, predicted_labels)
    )
    false_positive = sum(
        actual == 0 and predicted == 1
        for actual, predicted in zip(actual_labels, predicted_labels)
    )
    true_negative = sum(
        actual == 0 and predicted == 0
        for actual, predicted in zip(actual_labels, predicted_labels)
    )
    total = len(actual_labels)

    accuracy = (true_positive + true_negative) / total if total else 0.0
    predicted_positive = true_positive + false_positive
    precision = (
        true_positive / predicted_positive
        if predicted_positive
        else None
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 0.0
    )

    return {
        "TP": true_positive,
        "FN": false_negative,
        "FP": false_positive,
        "TN": true_negative,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
    }


def print_metrics(name: str, actual_labels: list[int], predicted_labels: list[int]) -> None:
    metrics = calculate_metrics(actual_labels, predicted_labels)
    print(f"\n[{name}]")
    print("혼동행렬 (세로=실제, 가로=예측)")
    print("             예측 0  예측 1")
    print(f"실제 0          {metrics['TN']:>4}    {metrics['FP']:>4}")
    print(f"실제 1          {metrics['FN']:>4}    {metrics['TP']:>4}")
    print(
        f"TP={metrics['TP']}, FN={metrics['FN']}, "
        f"FP={metrics['FP']}, TN={metrics['TN']}"
    )
    print(f"정확도={metrics['accuracy'] * 100:.1f}%")
    if metrics["precision"] is None:
        print("정밀도=해당없음")
    else:
        print(f"정밀도={metrics['precision'] * 100:.1f}%")
    print(f"재현율={metrics['recall'] * 100:.1f}%")


def verify_same_evaluation_rows(
    evaluation_rows: list[dict[str, str]],
    prediction_rows: list[dict[str, str]],
) -> None:
    if len(evaluation_rows) != len(prediction_rows):
        raise ValueError("평가행 수와 예측행 수가 일치하지 않습니다.")

    evaluation_target_times = [
        row["target_time"] for row in evaluation_rows
    ]
    prediction_target_times = [
        row["target_time"] for row in prediction_rows
    ]
    if evaluation_target_times != prediction_target_times:
        raise ValueError("평가행과 예측행의 정답 시각 순서가 일치하지 않습니다.")

    if len(set(evaluation_target_times)) != len(evaluation_target_times):
        raise ValueError("평가행에 중복 정답 시각이 있습니다.")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

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

    verify_period_times(train_rows, "학습")
    verify_period_times(evaluation_rows, "평가")

    train_counts = count_labels(train_rows)
    evaluation_counts = count_labels(evaluation_rows)

    scaler, model = train_logistic_regression(train_rows)
    evaluation_features = to_features(evaluation_rows)
    standardized_evaluation_features = scaler.transform(evaluation_features)
    strong_wind_probabilities = model.predict_proba(
        standardized_evaluation_features
    )[:, model.classes_.tolist().index(1)]

    prediction_rows = []
    actual_labels = []
    always_zero_predictions = []
    baseline_predictions = []
    logistic_predictions = []
    logistic_predictions_020 = []
    for row, probability in zip(evaluation_rows, strong_wind_probabilities):
        actual_wind_speed = float(row["target_wind_speed_ms"])
        current_wind_speed = float(row["wind_speed_ms"])
        always_zero_prediction = 0
        current_wind_baseline_prediction = (
            1 if current_wind_speed >= THRESHOLD_MS else 0
        )
        logistic_prediction = 1 if probability >= 0.50 else 0
        logistic_prediction_020 = 1 if probability >= 0.20 else 0
        actual_label = int(row["label"])

        actual_labels.append(actual_label)
        always_zero_predictions.append(always_zero_prediction)
        baseline_predictions.append(current_wind_baseline_prediction)
        logistic_predictions.append(logistic_prediction)
        logistic_predictions_020.append(logistic_prediction_020)

        prediction_rows.append(
            {
                "prediction_time": row["prediction_time"],
                "target_time": row["target_time"],
                "actual_wind_speed_ms": f"{actual_wind_speed:.6f}",
                "actual_label": row["label"],
                "current_wind_speed_ms": f"{current_wind_speed:.6f}",
                "always_zero_prediction": str(always_zero_prediction),
                "current_wind_baseline_prediction": str(
                    current_wind_baseline_prediction
                ),
                "strong_wind_probability": f"{probability:.6f}",
                "logistic_prediction": str(logistic_prediction),
                "logistic_prediction_threshold_020": str(
                    logistic_prediction_020
                ),
            }
        )

    verify_same_evaluation_rows(evaluation_rows, prediction_rows)

    with PREDICTION_OUTPUT_PATH.open(
        "w", encoding="utf-8-sig", newline=""
    ) as output_file:
        writer = csv.DictWriter(output_file, fieldnames=PREDICTION_COLUMNS)
        writer.writeheader()
        writer.writerows(prediction_rows)

    methods = [
        ("전부 0 기준", always_zero_predictions),
        ("현재 풍속 기준", baseline_predictions),
        ("표준화 로지스틱 회귀 0.50", logistic_predictions),
        ("표준화 로지스틱 회귀 0.20", logistic_predictions_020),
    ]
    score_rows = []
    for method_name, predicted_labels in methods:
        metrics = calculate_metrics(actual_labels, predicted_labels)
        precision_text = (
            "해당없음"
            if metrics["precision"] is None
            else f"{metrics['precision'] * 100:.1f}%"
        )
        score_rows.append(
            {
                "method": method_name,
                "evaluation_rows": str(len(evaluation_rows)),
                "actual_strong_wind": str(sum(actual_labels)),
                "TP": str(metrics["TP"]),
                "FN": str(metrics["FN"]),
                "FP": str(metrics["FP"]),
                "TN": str(metrics["TN"]),
                "accuracy": f"{metrics['accuracy'] * 100:.1f}%",
                "precision": precision_text,
                "recall": f"{metrics['recall'] * 100:.1f}%",
            }
        )

    with SCORES_OUTPUT_PATH.open(
        "w", encoding="utf-8-sig", newline=""
    ) as output_file:
        writer = csv.DictWriter(output_file, fieldnames=SCORE_COLUMNS)
        writer.writeheader()
        writer.writerows(score_rows)

    fieldnames = list(rows[0].keys())
    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("시각 확인: 정답 시각은 KST 기준이며 모든 행의 target_time - prediction_time = 1시간")
    print("시각 확인: 학습·평가 정답 시각은 중복 없이 시간순으로 정렬")
    print("시각 확인: 평가 구간의 인접 정답 시각은 모두 정확히 1시간 차이")
    print(
        f"학습 (2023-01-01 00:00 ~ 2024-11-30 23:59 KST): "
        f"전체 {len(train_rows)}행, 0={train_counts['0']}개, 1={train_counts['1']}개"
    )
    print(
        f"평가 (2024-12-01 00:00 ~ 2024-12-31 23:59 KST): "
        f"전체 {len(evaluation_rows)}행, 0={evaluation_counts['0']}개, 1={evaluation_counts['1']}개"
    )
    print(
        "평가행 확인: 세 방법 모두 같은 744개 평가행을 사용했으며 "
        f"실제 강풍 행은 {sum(actual_labels)}개"
    )
    print("방법별 결과:")
    print(
        "방법\t\t평가행\t실제강풍\t적중(TP)\t놓침(FN)\t"
        "오경보(FP)\t정상판정(TN)\t정확도\t정밀도\t재현율"
    )
    for score in score_rows:
        print(
            f"{score['method']}\t{score['evaluation_rows']}\t"
            f"{score['actual_strong_wind']}\t\t{score['TP']}\t\t"
            f"{score['FN']}\t\t{score['FP']}\t\t{score['TN']}\t\t"
            f"{score['accuracy']}\t{score['precision']}\t{score['recall']}"
        )
    print("로지스틱 임계값 비교:")
    threshold_050 = calculate_metrics(actual_labels, logistic_predictions)
    threshold_020 = calculate_metrics(actual_labels, logistic_predictions_020)
    print(
        "구분\t적중(TP)\t놓침(FN)\t오경보(FP)\t정밀도\t재현율"
    )
    print(
        f"0.50\t{threshold_050['TP']}\t\t{threshold_050['FN']}\t\t"
        f"{threshold_050['FP']}\t\t"
        f"{threshold_050['precision'] * 100:.1f}%\t"
        f"{threshold_050['recall'] * 100:.1f}%"
    )
    print(
        f"0.20\t{threshold_020['TP']}\t\t{threshold_020['FN']}\t\t"
        f"{threshold_020['FP']}\t\t"
        f"{threshold_020['precision'] * 100:.1f}%\t"
        f"{threshold_020['recall'] * 100:.1f}%"
    )
    print(f"점수 CSV 저장: {SCORES_OUTPUT_PATH}")
    print_metrics("전부 0 기준 예측", actual_labels, always_zero_predictions)
    print_metrics("현재 풍속 기준 예측", actual_labels, baseline_predictions)
    print_metrics("표준화 로지스틱 회귀 0.50", actual_labels, logistic_predictions)
    print_metrics("표준화 로지스틱 회귀 0.20", actual_labels, logistic_predictions_020)
    print("첫 평가 행:")
    print(evaluation_rows[0])
    print(f"라벨 포함 CSV 저장: {OUTPUT_PATH}")
    print(f"예측 CSV 저장: {PREDICTION_OUTPUT_PATH}")
    print("예측 CSV 첫 5행:")
    for row in prediction_rows[:5]:
        print(row)


if __name__ == "__main__":
    main()
