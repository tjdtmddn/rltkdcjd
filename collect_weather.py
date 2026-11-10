"""KMA 지상관측자료를 조회하고 필요한 열만 weather.csv로 저장한다."""

import csv
import getpass
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


API_URL = "https://apihub.kma.go.kr/api/typ01/url/kma_sfctm3.php"
REQUEST_PARAMS = {
    "tm1": "202510010000",
    "tm2": "202510072300",
    "stn": "108",
    "help": "1",
}
REQUEST_TIMEOUT_SECONDS = 30
BASE_DIR = Path(__file__).resolve().parent
RAW_RESPONSE_PATH = BASE_DIR / "weather_raw.txt"
CSV_PATH = BASE_DIR / "weather.csv"
REQUIRED_COLUMNS = {"TM": 1, "WS": 4, "TA": 12, "HM": 14}
OUTPUT_COLUMNS = ["datetime", "temperature_C", "humidity_pct", "wind_speed_ms"]
MISSING_VALUES = {
    "",
    "-",
    "-9",
    "-9.0",
    "-99",
    "-99.0",
    "-999",
    "-999.0",
    "-9999",
    "-9999.0",
    "999",
    "999.0",
    "9999",
}
HEADER_COLUMN_PATTERN = re.compile(
    r"(?<!\d)(\d{1,3})\s*[.:]?\s*([A-Z][A-Z0-9_]*)"
)
DATA_ROW_PATTERN = re.compile(r"^\s*\d{12}(?:\s+|$)")


def _message_from_body(body: str) -> str:
    """실패 응답 본문에서 API의 message 값을 추출한다."""
    try:
        payload: Any = json.loads(body)
    except json.JSONDecodeError:
        payload = None

    if isinstance(payload, dict):
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()

    match = re.search(r'"?message"?\s*[:=]\s*"?([^"\r\n]+)', body, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "API 응답에 실패 원인(message)이 없습니다."


def _decode_response(response: requests.Response) -> str:
    """응답 헤더의 charset을 우선 사용해 본문을 디코딩한다."""
    if response.encoding is None:
        response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def _split_response(body: str) -> tuple[list[str], list[str]]:
    """# 설명줄과 공백으로 분리할 자료행을 나눈다."""
    explanation_lines = []
    data_lines = []
    for line in body.splitlines():
        if line.lstrip("\ufeff ").startswith("#"):
            explanation_lines.append(line)
        elif DATA_ROW_PATTERN.match(line):
            data_lines.append(line)
    return explanation_lines, data_lines


def _find_column_positions(explanation_lines: list[str]) -> dict[str, int]:
    """설명줄의 번호-열 이름 헤더에서 필요한 열 위치를 확인한다."""
    positions: dict[str, int] = {}
    for line in explanation_lines:
        for number, name in HEADER_COLUMN_PATTERN.findall(line.upper()):
            if name in REQUIRED_COLUMNS:
                positions[name] = int(number)

    if positions != REQUIRED_COLUMNS:
        raise ValueError(
            "필수 헤더 위치를 확인할 수 없습니다. "
            f"확인 결과={positions}, 기대값={REQUIRED_COLUMNS}"
        )
    return positions


def _has_observation_rows(data_lines: list[str]) -> bool:
    """자료 행이 있으면 공식 열 번호를 사용할 수 있는지 확인한다."""
    return any(len(line.split()) >= 46 for line in data_lines)


def _is_missing(value: str) -> bool:
    """KMA 결측 표기를 식별한다."""
    return value.strip() in MISSING_VALUES


def _parse_rows(
    data_lines: list[str], positions: dict[str, int]
) -> list[dict[str, Any]]:
    """자료행을 공백으로 분리하고 시간·수치 열을 표 형식으로 변환한다."""
    rows = []
    for line_number, line in enumerate(data_lines, start=1):
        fields = line.split()
        try:
            timestamp = datetime.strptime(
                fields[positions["TM"] - 1], "%Y%m%d%H%M"
            )
        except (IndexError, ValueError) as error:
            raise ValueError(
                f"{line_number}번째 자료행의 TM을 읽을 수 없습니다."
            ) from error

        row: dict[str, Any] = {"datetime": timestamp}
        for source, target in (
            ("TA", "temperature_C"),
            ("HM", "humidity_pct"),
            ("WS", "wind_speed_ms"),
        ):
            try:
                value = fields[positions[source] - 1]
            except IndexError as error:
                raise ValueError(
                    f"{line_number}번째 자료행의 {source}를 읽을 수 없습니다."
                ) from error
            row[target] = "" if _is_missing(value) else float(value)
        rows.append(row)
    return rows


def _save_csv(rows: list[dict[str, Any]]) -> None:
    """변환·정렬된 표를 인덱스 없이 UTF-8-SIG CSV로 저장한다."""
    with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "datetime": row["datetime"].isoformat(sep=" "),
                }
            )


def _print_summary(rows: list[dict[str, Any]], duplicate_count: int) -> None:
    """저장 결과와 결측·시간 요약을 출력한다."""
    missing_counts = {
        column: sum(row[column] == "" for row in rows)
        for column in OUTPUT_COLUMNS
    }
    print(f"행수: {len(rows)}")
    print(f"중복 시각 수: {duplicate_count}")
    print(f"열별 결측수: {missing_counts}")
    if rows:
        print(f"첫 시각: {rows[0]['datetime'].isoformat(sep=' ')}")
        print(f"마지막 시각: {rows[-1]['datetime'].isoformat(sep=' ')}")
    print(f"저장 위치: {CSV_PATH.resolve()}")
    print(f"원본 응답 저장 위치: {RAW_RESPONSE_PATH.resolve()}")


def main() -> None:
    auth_key = getpass.getpass("KMA API 인증키: ")
    params = {**REQUEST_PARAMS, "authKey": auth_key}

    try:
        response = requests.get(
            API_URL,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        print("API 요청에 실패했습니다. 네트워크 상태와 인증키를 확인하세요.")
        return

    print(f"HTTP 상태: {response.status_code}")
    body = _decode_response(response)
    RAW_RESPONSE_PATH.write_bytes(response.content)

    if not response.ok:
        print(f"요청 실패: {_message_from_body(body)}")
        return

    try:
        explanation_lines, data_lines = _split_response(body)
        try:
            positions = _find_column_positions(explanation_lines)
        except ValueError:
            if not _has_observation_rows(data_lines):
                raise
            positions = REQUIRED_COLUMNS.copy()
            print(
                "헤더 번호를 읽지 못해 공식 열 위치"
                "(TM 1, WS 4, TA 12, HM 14)를 사용합니다."
            )
        rows = _parse_rows(data_lines, positions)
    except ValueError as error:
        print(f"응답 처리에 실패했습니다: {error}")
        return

    print(
        "헤더 위치 확인: "
        + ", ".join(
            f"{name}({positions[name]})" for name in ("TM", "WS", "TA", "HM")
        )
    )
    rows.sort(key=lambda row: row["datetime"])
    duplicate_count = len(rows) - len({row["datetime"] for row in rows})
    if duplicate_count:
        print(f"중복 시각이 {duplicate_count}개 발견되어 저장을 중단합니다.")
        return

    if not rows:
        print("자료 행이 없어 CSV 저장을 중단합니다.")
        return

    _save_csv(rows)
    _print_summary(rows, duplicate_count)


if __name__ == "__main__":
    main()
