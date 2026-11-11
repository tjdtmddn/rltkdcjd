"""12월 첫 주의 실제 풍속과 두 예측을 그래프로 저장한다."""

import csv
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "predictions.csv"
OUTPUT_PATH = BASE_DIR / "prediction_week.png"
ZOOM_OUTPUT_PATH = BASE_DIR / "prediction_week_first48.png"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def main() -> None:
    with INPUT_PATH.open("r", encoding="utf-8-sig", newline="") as input_file:
        rows = list(csv.DictReader(input_file))

    required_columns = {
        "prediction_time",
        "target_time",
        "actual_wind_speed_ms",
        "persistence_prediction_ms",
        "linear_regression_prediction_ms",
    }
    if not rows or required_columns - set(rows[0]):
        raise ValueError("predictions.csv에 필요한 열이 없습니다.")

    for row in rows:
        row["target_datetime"] = datetime.strptime(row["target_time"], TIME_FORMAT)
        row["actual"] = float(row["actual_wind_speed_ms"])
        row["persistence"] = float(row["persistence_prediction_ms"])
        row["regression"] = float(row["linear_regression_prediction_ms"])
    rows.sort(key=lambda row: row["target_datetime"])

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

    december_baseline_mae = sum(
        abs(row["actual"] - row["persistence"]) for row in december_rows
    ) / len(december_rows)
    december_regression_mae = sum(
        abs(row["actual"] - row["regression"]) for row in december_rows
    ) / len(december_rows)

    timestamps = [row["target_datetime"] for row in week_rows]
    figure, axis = plt.subplots(figsize=(13, 6))
    axis.plot(
        timestamps,
        [row["actual"] for row in week_rows],
        color="black",
        linewidth=1.5,
        label="Actual",
    )
    axis.plot(
        timestamps,
        [row["persistence"] for row in week_rows],
        color="gray",
        linestyle="--",
        linewidth=1.3,
        label="Persistence",
    )
    axis.plot(
        timestamps,
        [row["regression"] for row in week_rows],
        color="blue",
        linewidth=1.5,
        label="Linear regression",
    )
    axis.set_title("Wind speed prediction: 2024-12-01 to 2024-12-07")
    axis.set_xlabel("Target time (KST)")
    axis.set_ylabel("Wind speed (m/s)")
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure.autofmt_xdate()
    figure.tight_layout()
    figure.savefig(OUTPUT_PATH, dpi=150)
    plt.show()
    plt.close(figure)

    zoom_rows = week_rows[:48]
    zoom_figure, zoom_axis = plt.subplots(figsize=(13, 6))
    zoom_timestamps = [row["target_datetime"] for row in zoom_rows]
    zoom_axis.plot(
        zoom_timestamps,
        [row["actual"] for row in zoom_rows],
        color="black",
        linewidth=1.5,
        label="Actual",
    )
    zoom_axis.plot(
        zoom_timestamps,
        [row["persistence"] for row in zoom_rows],
        color="gray",
        linestyle="--",
        linewidth=1.3,
        label="Persistence",
    )
    zoom_axis.plot(
        zoom_timestamps,
        [row["regression"] for row in zoom_rows],
        color="blue",
        linewidth=1.5,
        label="Linear regression",
    )
    zoom_axis.set_title("Wind speed prediction: first 48 hours")
    zoom_axis.set_xlabel("Target time (KST)")
    zoom_axis.set_ylabel("Wind speed (m/s)")
    zoom_axis.grid(True, alpha=0.3)
    zoom_axis.legend()
    zoom_figure.autofmt_xdate()
    zoom_figure.tight_layout()
    zoom_figure.savefig(ZOOM_OUTPUT_PATH, dpi=150)
    plt.show()
    plt.close(zoom_figure)

    highlighted_row = next(
        row
        for row in week_rows
        if row["target_datetime"] == datetime(2024, 12, 2, 13)
    )
    print(f"그래프 저장 위치: {OUTPUT_PATH}")
    print(f"첫 48시간 확대 그래프 저장 위치: {ZOOM_OUTPUT_PATH}")
    print(f"12월 전체 평가 행수: {len(december_rows)}")
    print(f"12월 1~7일 그래프 행수: {len(week_rows)}")
    print(f"12월 전체 기준 예측 MAE: {december_baseline_mae:.6f} m/s")
    print(f"12월 전체 선형 회귀 MAE: {december_regression_mae:.6f} m/s")
    print(
        "2024-12-02 13:00 결과: "
        f"실제 {highlighted_row['actual']:.6f} m/s, "
        f"선형회귀 {highlighted_row['regression']:.6f} m/s"
    )


if __name__ == "__main__":
    main()
