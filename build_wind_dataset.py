"""시간별 풍속 예측용 입력·정답 데이터셋을 만든다."""

import csv
from datetime import datetime, timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SOURCE_PATH = BASE_DIR / "asos_108_2023_2024.csv"
OUTPUT_PATH = BASE_DIR / "wind_dataset.csv"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def read_source() -> dict[datetime, dict[str, str]]:
    """원본 관측행을 읽어 시각별로 반환한다."""
    with SOURCE_PATH.open("r", encoding="utf-8-sig", newline="") as source_file:
        rows = csv.DictReader(source_file)
        observations: dict[datetime, dict[str, str]] = {}
        for row in rows:
            observation_time = datetime.strptime(row["datetime"], TIME_FORMAT)
            if observation_time in observations:
                raise ValueError(f"중복 관측 시각: {row['datetime']}")
            observations[observation_time] = row
    if not observations:
        raise ValueError("원본 관측행이 없습니다.")
    return observations


def build_dataset(
    observations: dict[datetime, dict[str, str]],
) -> list[dict[str, str]]:
    """1시간 시간축을 만든 뒤 필요한 시프트값이 있는 행만 구성한다."""
    first_time = min(observations)
    last_time = max(observations)
    hourly_rows: dict[datetime, dict[str, str]] = {}
    current_time = first_time
    while current_time <= last_time:
        hourly_rows[current_time] = observations.get(current_time, {})
        current_time += timedelta(hours=1)

    dataset = []
    for prediction_time, current_row in hourly_rows.items():
        one_hour_before = hourly_rows.get(prediction_time - timedelta(hours=1), {})
        two_hours_before = hourly_rows.get(prediction_time - timedelta(hours=2), {})
        target_time = prediction_time + timedelta(hours=1)
        target_row = hourly_rows.get(target_time, {})

        values = {
            "prediction_time": prediction_time.strftime(TIME_FORMAT),
            "target_time": target_time.strftime(TIME_FORMAT),
            "wind_speed_ms": current_row.get("wind_speed_ms", ""),
            "temperature_C": current_row.get("temperature_C", ""),
            "humidity_pct": current_row.get("humidity_pct", ""),
            "wind_speed_1h_before_ms": one_hour_before.get("wind_speed_ms", ""),
            "wind_speed_2h_before_ms": two_hours_before.get("wind_speed_ms", ""),
            "target_wind_speed_ms": target_row.get("wind_speed_ms", ""),
        }
        required_values = (
            values["wind_speed_ms"],
            values["temperature_C"],
            values["humidity_pct"],
            values["wind_speed_1h_before_ms"],
            values["wind_speed_2h_before_ms"],
            values["target_wind_speed_ms"],
        )
        if all(value.strip() for value in required_values):
            dataset.append(values)
    return dataset


def main() -> None:
    observations = read_source()
    dataset = build_dataset(observations)
    fieldnames = [
        "prediction_time",
        "target_time",
        "wind_speed_ms",
        "temperature_C",
        "humidity_pct",
        "wind_speed_1h_before_ms",
        "wind_speed_2h_before_ms",
        "target_wind_speed_ms",
    ]
    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dataset)

    print(f"시간축 행수: {len(observations)}개 관측행을 {len(hourly_rows(observations))}개 시각으로 정렬")
    print(f"저장 행수: {len(dataset)}")
    print("첫 4행:")
    for row in dataset[:4]:
        print(row)


def hourly_rows(observations: dict[datetime, dict[str, str]]) -> list[datetime]:
    """첫 시각부터 마지막 시각까지의 1시간 간격 시각을 반환한다."""
    current_time = min(observations)
    last_time = max(observations)
    times = []
    while current_time <= last_time:
        times.append(current_time)
        current_time += timedelta(hours=1)
    return times


if __name__ == "__main__":
    main()
