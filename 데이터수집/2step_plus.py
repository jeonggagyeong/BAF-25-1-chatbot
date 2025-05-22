import pandas as pd
import requests
import time

# ✅ 1. 지하철역 데이터 불러오기
file = pd.read_csv('ONEROOM/seoul_subwaystation.csv', encoding='CP949')

# ✅ 2. 사용할 역 리스트 정의
stations = ["구파발역", "연신내역", "불광역", "녹번역", "홍제역", "무악재역", "독립문역",
            "경복궁역", "안국역", "종로3가역", "을지로3가역", "충무로역", "동대입구역", "약수역", "금호역", "옥수역"]

# ✅ 3. Tmap API 키 입력
app_key = "-"

# ✅ 4. 모든 역별로 실행
for station in stations:
    # ✅ 해당 역의 X, Y 좌표 가져오기
    station_data = file[file["SubST_NM"] == station.replace("역", "")]

    if station_data.empty:
        print(f"❌ {station} 좌표 정보 없음!")
        continue

    endX = station_data["X좌표"].values[0]
    endY = station_data["Y좌표"].values[0]

    # ✅ 매물 데이터 불러오기
    try:
        df = pd.read_csv(f"ONEROOM/{station}_room_data.csv")
    except FileNotFoundError:
        print(f"❌ {station} 관련 매물 데이터 없음! 건너뜀.")
        continue

    # ✅ 결과 저장용 컬럼 추가
    df["도보거리_m"] = None
    df["도보시간_분"] = None

    # ✅ 5. 행별로 API 호출하여 도보 거리 및 시간 계산
    for idx, row in df.iterrows():
        startY = str(round(row["위도"], 4))
        startX = str(round(row["경도"], 4))

        if pd.isna(row["위도"]) or pd.isna(row["경도"]):
            print(f"[{idx}] 위도 또는 경도 값이 없음! {row['위도']}, {row['경도']}")
            continue

        if startX == endX and startY == endY:
            print(f"[{idx}] 출발지와 도착지가 동일하여 경로 계산 불가!")
            df.at[idx, "도보거리_m"] = 0
            df.at[idx, "도보시간_분"] = 0
            continue

        data = {
            "startX": startX,
            "startY": startY,
            "endX": str(endX),
            "endY": str(endY),
            "reqCoordType": "WGS84GEO",
            "resCoordType": "WGS84GEO",
            "startName": "출발지",
            "endName": "도착지"
        }

        try:
            response = requests.post(
                "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1&format=json",
                headers={"Content-Type": "application/x-www-form-urlencoded", "appKey": app_key},
                data=data
            )

            if response.status_code != 200:
                print(f"[{idx}] API 요청 실패! 상태 코드: {response.status_code}")
                print(response.text)
                continue

            result = response.json()

            if "features" in result:
                total_dist = result["features"][0]["properties"]["totalDistance"]
                total_time = result["features"][0]["properties"]["totalTime"]
                df.at[idx, "도보거리_m"] = round(total_dist)
                df.at[idx, "도보시간_분"] = round(total_time / 60)
            else:
                print(f"[{idx}] 응답에 features 없음")
                print(response.text)  # 응답을 출력해서 문제 확인
                df.at[idx, "도보거리_m"] = -1
                df.at[idx, "도보시간_분"] = -1

        except Exception as e:
            print(f"[{idx}] 오류 발생: {e}")
            df.at[idx, "도보거리_m"] = -1
            df.at[idx, "도보시간_분"] = -1

        time.sleep(1)  # 요청 속도 제한

    # ✅ 6. 이동 시간 계산
    df["도보시간_분"] = pd.to_numeric(df["도보시간_분"], errors="coerce")
    df["지하철이동시간_동대입구역(분)"] = pd.to_numeric(df["지하철이동시간_동대입구역(분)"], errors="coerce")
    df["지하철이동시간_충무로역(분)"] = pd.to_numeric(df["지하철이동시간_충무로역(분)"], errors="coerce")

    df["매물_동입"] = df["지하철이동시간_동대입구역(분)"] + df["도보시간_분"]
    df["매물_충무로"] = df["지하철이동시간_충무로역(분)"] + df["도보시간_분"]

    # ✅ 7. 결과 저장
    df.to_csv(f"ONEROOM/{station}_room_data_with_walk.csv", index=False, encoding="utf-8-sig")
    print(f"✅ {station} 도보 거리/시간 계산 완료! 저장됨.")
