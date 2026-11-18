"""12월 첫 주의 실제 풍속과 강풍 분류 판정을 그래프로 표시한다."""

import csv
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "classification_predictions.csv"
OUTPUT_PATH = BASE_DIR / "strong_wind_december.png"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
STRONG_WIND_THRESHOLD_MS = 4.0


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    with INPUT_PATH.open("r", encoding="utf-8-sig", newline="") as input_file:
        rows = list(csv.DictReader(input_file))

    required_columns = {
        "target_time",
        "actual_wind_speed_ms",
        "actual_label",
        "strong_wind_probability",
        "logistic_prediction",
        "logistic_prediction_threshold_020",
    }
    if not rows or required_columns - set(rows[0]):
        raise ValueError("classification_predictions.csv에 필요한 열이 없습니다.")

    for row in rows:
        row["target_datetime"] = datetime.strptime(row["target_time"], TIME_FORMAT)
        row["actual_wind_speed"] = float(row["actual_wind_speed_ms"])
        row["actual_label_int"] = int(row["actual_label"])
        row["probability"] = float(row["strong_wind_probability"])
        row["prediction_050"] = int(row["logistic_prediction"])
        row["prediction_020"] = int(
            row["logistic_prediction_threshold_020"]
        )

    december_rows = [
        row
        for row in rows
        if datetime(2024, 12, 1) <= row["target_datetime"] < datetime(2025, 1, 1)
    ]
    week_rows = [
        row
        for row in december_rows
        if datetime(2024, 12, 1) <= row["target_datetime"] < datetime(2024, 12, 8)
    ]
    if len(december_rows) != 744 or len(week_rows) != 168:
        raise ValueError(
            f"평가 범위가 예상과 다릅니다: 12월 {len(december_rows)}행, "
            f"첫 주 {len(week_rows)}행"
        )

    timestamps = [row["target_datetime"] for row in week_rows]
    actual_speed = [row["actual_wind_speed"] for row in week_rows]

    actual_strong_times = [
        row["target_datetime"]
        for row in week_rows
        if row["actual_label_int"] == 1
    ]
    prediction_050_times = [
        row["target_datetime"]
        for row in week_rows
        if row["prediction_050"] == 1
    ]
    prediction_020_times = [
        row["target_datetime"]
        for row in week_rows
        if row["prediction_020"] == 1
    ]

    figure, (speed_axis, class_axis) = plt.subplots(
        2,
        1,
        figsize=(14, 8),
        sharex=True,
        gridspec_kw={"height_ratios": [2, 1]},
    )

    speed_axis.plot(
        timestamps,
        actual_speed,
        color="black",
        linewidth=1.5,
        marker="o",
        markersize=2,
        label="Actual wind speed",
    )
    speed_axis.axhline(
        STRONG_WIND_THRESHOLD_MS,
        color="red",
        linestyle="--",
        linewidth=1.5,
        label="Strong wind threshold: 4.0 m/s",
    )
    speed_axis.set_title("Strong wind observations and predictions: 2024-12-01 to 2024-12-07")
    speed_axis.set_ylabel("Wind speed (m/s)")
    speed_axis.grid(True, alpha=0.3)
    speed_axis.legend(loc="upper right")

    class_axis.scatter(
        actual_strong_times,
        [1] * len(actual_strong_times),
        color="black",
        marker="o",
        s=35,
        label="Actual strong wind",
    )
    class_axis.scatter(
        prediction_050_times,
        [2] * len(prediction_050_times),
        color="blue",
        marker="^",
        s=35,
        label="0.50 prediction",
    )
    class_axis.scatter(
        prediction_020_times,
        [3] * len(prediction_020_times),
        color="orange",
        marker="s",
        s=35,
        label="0.20 prediction",
    )
    class_axis.set_yticks([1, 2, 3])
    class_axis.set_yticklabels(["Actual", "0.50", "0.20"])
    class_axis.set_ylim(0.5, 3.5)
    class_axis.set_xlabel("Target time (KST)")
    class_axis.grid(True, axis="x", alpha=0.3)
    class_axis.legend(loc="upper right", ncol=3)

    figure.autofmt_xdate()
    figure.tight_layout()
    figure.savefig(OUTPUT_PATH, dpi=150)
    plt.close(figure)

    december_2_mismatches = [
        row
        for row in week_rows
        if row["target_datetime"].date() == datetime(2024, 12, 2).date()
        and (
            row["actual_label_int"] != row["prediction_050"]
            or row["actual_label_int"] != row["prediction_020"]
        )
    ]
    if not december_2_mismatches:
        raise ValueError("12월 2일 틀린 사례를 찾지 못했습니다.")

    example = december_2_mismatches[0]
    print(f"그래프 저장 위치: {OUTPUT_PATH}")
    print(f"12월 전체 평가 행수: {len(december_rows)}")
    print(f"12월 1~7일 그래프 행수: {len(week_rows)}")
    print(
        "12월 2일 틀린 사례:"
        f" 정답 시각={example['target_time']} KST,"
        f" 실제풍속={example['actual_wind_speed']:.1f} m/s,"
        f" 실제강풍={example['actual_label_int']},"
        f" 강풍확률={example['probability']:.6f},"
        f" 0.50예측={example['prediction_050']},"
        f" 0.20예측={example['prediction_020']}"
    )


if __name__ == "__main__":
    main()
