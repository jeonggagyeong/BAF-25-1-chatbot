import pandas as pd
import os
import glob

# 1. 현재 작업 디렉토리 출력
print("현재 작업 디렉토리:", os.getcwd())

# 2. 특정 폴더 내 모든 CSV 파일을 하나의 데이터프레임으로 불러오기
folder_path = './데이터셋'  # 여기에 폴더 경로 입력
csv_files = glob.glob(os.path.join(folder_path, '*.csv'))

# 모든 CSV 파일을 읽어와 리스트에 저장 (인코딩 예외 처리)
df_list = []
for file in csv_files:
    try:
        df = pd.read_csv(file, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file, encoding='cp949')
    df_list.append(df)

# 리스트의 데이터프레임을 하나로 합치기
combined_df = pd.concat(df_list, ignore_index=True)

## 중복 제거 전 행 개수 출력
print(f"중복 제거 전 행 개수: {len(combined_df)}")

# 3. '매물ID'가 중복될 경우, '매물_충무로' 값이 더 작은 행만 남기기
filtered_df = combined_df.loc[combined_df.groupby('매물ID')['매물_충무로'].idxmin()].reset_index(drop=True)

##  중복 제거 후 행 개수 출력
print(f"중복 제거 후 행 개수: {len(filtered_df)}")

# 4. filtered_df를 CSV로 저장
filtered_df.to_csv('직방데이터셋.csv', index=False)
print("filtered_df가 '직방데이터셋.csv' 파일로 저장되었습니다.")