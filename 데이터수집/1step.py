import requests
import json
import pandas as pd
import time
import random
from pprint import pprint  # 보기 좋게 출력!

# ✅ URL 정의
ROOM_LIST_URL = "https://apis.zigbang.com/v2/subways/{subway_id}/items/oneroom?radius=1&depositMin=0&rentMin=0&salesTypes%5B0%5D=%EC%A0%84%EC%84%B8&salesTypes%5B1%5D=%EC%9B%94%EC%84%B8&checkAnyItemWithoutFilter=true&domain=zigbang"
ROOM_INFO_URL = "https://apis.zigbang.com/v3/items/{room_id}?version=&domain=zigbang"
SUBWAY_LIST_URL = "https://apis.zigbang.com/property/biglab/subway/all"


# ✅ 지하철 ID 가져오기
def getSubwayId(subway_name):
    req = requests.get(SUBWAY_LIST_URL)
    if req.status_code == 200:
        data = req.json()
        subway_info = [item['id'] for item in data if item['name'] == subway_name]
        return subway_info[0] if subway_info else None
    return None


# ✅ 매물 ID 리스트 가져오기
def getRoomList(subway_id):
    REQUEST_URL = ROOM_LIST_URL.format(subway_id=subway_id)
    req = requests.get(REQUEST_URL)
    if req.status_code == 200:
        data = req.json()
        return [a["itemId"] for a in data.get("items", []) if 'ad_agent' not in a]
    return []


# ✅ 매물 상세정보 가져오기
def getRoomInfo(room_id):
    REQUEST_URL = ROOM_INFO_URL.format(room_id=room_id)
    req = requests.get(REQUEST_URL)
    if req.status_code == 200:
        return req.json()
    return None


# ✅ 매물 상세정보를 파싱하는 함수
def parseRoomInfo(room_info, find_text=None):
    if "item" not in room_info:
        return None

    item = room_info["item"]

    parsed_data = {
        # 기본 정보
        "매물ID": item.get("itemId"),
        "거래유형": item.get("salesType"),
        "방종류": item.get("serviceType"),
        "룸타입": item.get("roomType"),
        "제목": item.get("title"),
        "설명": item.get("description"),

        # 가격 관련 정보
        "보증금(만원)": item.get("price", {}).get("deposit"),
        "월세(만원)": item.get("price", {}).get("rent"),
        "관리비(만원)": item.get("manageCost", {}).get("amount"),

        # 면적과 구조
        "전용면적(m²)": item.get("area", {}).get("전용면적M2"),
        "층수": item.get("floor", {}).get("floor"),
        "총층수": item.get("floor", {}).get("allFloors"),
        "욕실수": item.get("bathroomCount"),
        "방향": item.get("roomDirection"),

        # 입주 정보
        "입주가능일": item.get("moveinDate"),
        "승강기": item.get("elevator"),
        "주차여부": item.get("parkingAvailableText"),

        # 주소 정보
        "주소(법정동)": item.get("addressOrigin", {}).get("fullText"),
        "지번주소": item.get("jibunAddress"),

        # 위치 정보
        "위도": item.get("location", {}).get("lat"),
        "경도": item.get("location", {}).get("lng"),

        # 옵션 리스트 (None 제거 후 문자열 결합)
        "옵션": ', '.join([opt for opt in item.get("options", []) if isinstance(opt, str)]),

        # 상태 정보
        "상태": item.get("status"),
        "조회수": item.get("viewCount"),

        # 기타
        "등록일": item.get("approveDate"),
        "수정일": item.get("updatedAt"),
        "건물유형": item.get("residenceType"),
    }

    # ✅ 설명에서 특정 텍스트 찾는 기능 (선택)
    if find_text and parsed_data["설명"]:
        if find_text in parsed_data["설명"]:
            return parsed_data
        return None

    return parsed_data


# ✅ 지하철역 리스트 정의 (구파발 → 동대입구)
stations = ["충무로역", "동대입구역", "약수역", "금호역", "옥수역"]

# ✅ 각 역별 크롤링
for subway_name in stations:
    subway_id = getSubwayId(subway_name)

    room_info_list = []

    if subway_id:
        room_list = getRoomList(subway_id)
        print(f"\n🚇 {subway_name} ({subway_id}) - 총 {len(room_list)}개 매물 발견!\n")

        for idx, room_id in enumerate(room_list, start=1):
            room_info = getRoomInfo(room_id)

            # 딜레이를 줘서 서버에 무리 주지 않기!
            time.sleep(random.uniform(0.5, 1.5))

            parsed_room_info = parseRoomInfo(room_info, find_text=None)

            if parsed_room_info:
                room_info_list.append(parsed_room_info)

                # 🚀 실시간 출력 부분
                print(f"👉 [{idx}/{len(room_list)}] 매물 수집 완료: {parsed_room_info['매물ID']}")
                print("-" * 80)

        # ✅ 결과 DataFrame 생성 및 CSV 저장
        df = pd.DataFrame(room_info_list)
        df['지하철이동시간_동대입구역(분)'] = ''
        df['지하철이동시간_충무로역(분)'] = ''

        # ✅ 파일명 자동 저장
        df.to_csv(f"ONEROOM/{subway_name}_room_data.csv", index=False, encoding="utf-8-sig")

        print(f"\n✅ {subway_name}: 총 {len(room_info_list)}개 매물 저장 완료!\n")

    else:
        print(f"❌ {subway_name}을 찾을 수 없습니다.")

