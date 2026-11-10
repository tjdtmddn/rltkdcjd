# 기상 관측자료 수집

기상청 APIHub의 지상 관측자료 조회 API에서 관측소 `108`의
2025년 10월 1일 00시부터 10월 7일 23시까지 1시간 간격의 자료를 요청합니다.
요청에는 도움말(`help=1`)을 포함하며, 출력 데이터는 관측 시각·기온·습도·풍속
열을 대상으로 합니다.
원본 46개 열 중 `TM`(1열), `WS`(4열), `TA`(12열), `HM`(14열)을
공백 기준으로 분리해 추출합니다. 기온의 `-9` 값은 정상적인 관측값일 수 있어
일괄 삭제하지 않습니다.

## 실행

```powershell
python -m pip install requests pandas
python collect_weather.py
```

실행 중 인증키를 입력하면 HTTP 상태가 출력됩니다. 성공하면 원본 응답을
`weather_raw.txt`로 보관하고, 다음 열을 `weather.csv`로 저장합니다.

```text
datetime,temperature_C,humidity_pct,wind_speed_ms
```

자료 행은 `#` 설명 행을 제외하고 공백으로 분리하며, 공식 헤더의 열 번호
`TM(1)`, `WS(4)`, `TA(12)`, `HM(14)`를 사용합니다. 시간순 정렬과 중복 확인을
수행하고 CSV는 인덱스 없이 `utf-8-sig`로 저장합니다. 결측값은 빈 칸으로
저장하며, 정상적인 음수 기온(예: `-9`)은 삭제하지 않습니다.
표 정리에는 pandas의 `to_datetime()`, `to_numeric()`, `sort_values()`,
`isna().sum()`, `to_csv()`를 사용하며 변환 실패와 중복 시각 개수도 출력합니다.

인증키는 파일에 저장하지 않으며 출력에도 포함하지 않습니다. 자료가 없으면
`weather.csv`를 생성하지 않고 원인을 안내합니다.

활용신청이 필요한 API라는 응답이 나오면 기상청 APIHub에서 해당 API의 활용신청을
완료한 뒤 다시 실행합니다. HTTP 401은 인증키를, HTTP 403은 활용신청 상태를
확인합니다.

## 기온·습도·풍속 그래프

API를 다시 호출하지 않고 기존 `weather.csv`를 사용해 그래프를 생성합니다.

```powershell
python -m pip install matplotlib
python plot_weather.py
```

`plot_weather.py`는 `datetime`을 시간으로 변환하고 시간순 정렬 후 1시간 간격으로
누락 시각을 확인합니다. 기온 그래프는 `temperature.png`, 습도와 풍속 그래프는
`humidity_wind.png`로 저장하고 화면에도 표시합니다.

## 제출 확인

- 관측소: `108` (서울)
- 기간: `2025-10-01 00:00` ~ `2025-10-07 23:00` (KST)
- 출처: [기상청 APIHub 지상관측자료](https://apihub.kma.go.kr/api/typ01/url/kma_sfctm3.php)
- 제출 파일: `collect_weather.py`, `plot_weather.py`, `weather.csv`,
  `weather_raw.txt`, `temperature.png`, `humidity_wind.png`, `README.md`

확인 결과 자료는 168행이며 시간 누락과 중복 시각은 각각 0개이고,
`datetime`, `temperature_C`, `humidity_pct`, `wind_speed_ms`의 결측값도 모두 0개입니다.
그래프에서는 2025년 10월 1~7일의 시간별 기온·습도·풍속 변화를 확인할 수 있습니다.

인증키는 코드, CSV/원본 응답, 이미지, README에 저장하지 않았으며 실행 시
`getpass.getpass()`로만 입력합니다.