"""weather.csv의 시간별 기온·습도·풍속 그래프를 저장하고 표시한다."""

import csv
import math
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "weather.csv"
TEMPERATURE_IMAGE_PATH = BASE_DIR / "temperature.png"
HUMIDITY_WIND_IMAGE_PATH = BASE_DIR / "humidity_wind.png"


def _read_weather_csv() -> list[tuple[datetime, float, float, float]]:
    """CSV를 읽어 시각과 기상값을 Python 자료형으로 변환한다."""
    records: list[tuple[datetime, float, float, float]] = []
    with CSV_PATH.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required_columns = {
            "datetime",
            "temperature_C",
            "humidity_pct",
            "wind_speed_ms",
        }
        if reader.fieldnames is None or required_columns - set(reader.fieldnames):
            raise ValueError(
                "weather.csv에 datetime, temperature_C, humidity_pct 또는 "
                "wind_speed_ms 열이 없습니다."
            )

        for line_number, row in enumerate(reader, start=2):
            try:
                timestamp_value = row["datetime"]
                temperature_value = row["temperature_C"]
                humidity_value = row["humidity_pct"]
                wind_value = row["wind_speed_ms"]
                if None in (
                    timestamp_value,
                    temperature_value,
                    humidity_value,
                    wind_value,
                ):
                    raise ValueError("필수 값이 비어 있습니다.")
                timestamp = datetime.fromisoformat(timestamp_value.strip())
                temperature = (
                    float(temperature_value.strip())
                    if temperature_value.strip()
                    else math.nan
                )
                humidity = (
                    float(humidity_value.strip())
                    if humidity_value.strip()
                    else math.nan
                )
                wind_speed = (
                    float(wind_value.strip()) if wind_value.strip() else math.nan
                )
            except (TypeError, ValueError) as error:
                raise ValueError(f"{line_number}번째 행을 변환할 수 없습니다.") from error
            records.append((timestamp, temperature, humidity, wind_speed))
    return records


def _make_hourly_series(
    records: list[tuple[datetime, float, float, float]],
) -> tuple[
    list[datetime],
    list[float],
    list[float],
    list[float],
    list[datetime],
]:
    """자료를 시간순으로 정렬하고 누락 시각을 NaN으로 채운다."""
    if not records:
        raise ValueError("weather.csv에 그래프로 그릴 자료가 없습니다.")

    records.sort(key=lambda record: record[0])
    if len({timestamp for timestamp, _, _, _ in records}) != len(records):
        raise ValueError("weather.csv에 중복 datetime이 있습니다.")

    values = {
        timestamp: (temperature, humidity, wind_speed)
        for timestamp, temperature, humidity, wind_speed in records
    }
    current = records[0][0]
    end = records[-1][0]
    timestamps: list[datetime] = []
    temperatures: list[float] = []
    humidities: list[float] = []
    wind_speeds: list[float] = []
    missing_timestamps: list[datetime] = []

    while current <= end:
        timestamps.append(current)
        temperature, humidity, wind_speed = values.get(
            current, (math.nan, math.nan, math.nan)
        )
        temperatures.append(temperature)
        humidities.append(humidity)
        wind_speeds.append(wind_speed)
        if current not in values:
            missing_timestamps.append(current)
        current += timedelta(hours=1)

    return timestamps, temperatures, humidities, wind_speeds, missing_timestamps


def _plot_temperature(
    timestamps: list[datetime],
    temperatures: list[float],
) -> None:
    """시간별 기온 그래프를 temperature.png로 저장한다."""
    figure, axis = plt.subplots(figsize=(12, 6))
    axis.plot(timestamps, temperatures, color="tab:red", marker="o", linewidth=1.5)
    axis.set_title("Temperature over time")
    axis.set_xlabel("Time (KST)")
    axis.set_ylabel("Temperature (°C)")
    axis.grid(True, alpha=0.3)
    figure.autofmt_xdate()
    figure.tight_layout()
    figure.savefig(TEMPERATURE_IMAGE_PATH, dpi=150)
    print(f"기온 그래프 저장 위치: {TEMPERATURE_IMAGE_PATH}")
    plt.close(figure)


def _plot_humidity_wind(
    timestamps: list[datetime],
    humidities: list[float],
    wind_speeds: list[float],
) -> None:
    """시간별 습도·풍속 그래프를 humidity_wind.png로 저장한다."""
    figure, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    axes[0].plot(timestamps, humidities, color="tab:blue", marker="o", linewidth=1.5)
    axes[0].set_title("Humidity over time")
    axes[0].set_ylabel("Humidity (%)")
    axes[0].grid(True, alpha=0.3)
    axes[1].plot(timestamps, wind_speeds, color="tab:green", marker="o", linewidth=1.5)
    axes[1].set_title("Wind speed over time")
    axes[1].set_xlabel("Time (KST)")
    axes[1].set_ylabel("Wind speed (m/s)")
    axes[1].grid(True, alpha=0.3)
    figure.autofmt_xdate()
    figure.tight_layout()
    figure.savefig(HUMIDITY_WIND_IMAGE_PATH, dpi=150)
    print(f"습도·풍속 그래프 저장 위치: {HUMIDITY_WIND_IMAGE_PATH}")
    plt.show()


def main() -> None:
    """CSV를 읽고 두 종류의 그래프를 저장한 뒤 화면에 표시한다."""
    if not CSV_PATH.exists():
        print(
            f"{CSV_PATH.name}을(를) 찾을 수 없습니다. "
            "먼저 collect_weather.py를 성공적으로 실행하세요."
        )
        return

    records = _read_weather_csv()
    (
        timestamps,
        temperatures,
        humidities,
        wind_speeds,
        missing_timestamps,
    ) = _make_hourly_series(records)
    print(f"누락 시각 수: {len(missing_timestamps)}")
    if missing_timestamps:
        print(
            "누락 시각: "
            + ", ".join(
                timestamp.isoformat(sep=" ") for timestamp in missing_timestamps
            )
        )
    _plot_temperature(timestamps, temperatures)
    _plot_humidity_wind(timestamps, humidities, wind_speeds)


if __name__ == "__main__":
    main()
