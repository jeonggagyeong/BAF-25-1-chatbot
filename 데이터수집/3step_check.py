import pandas as pd


pd.set_option('display.max_columns', None)
data = pd.read_csv('ONEROOM/옥수역_room_data_with_walk.csv')
print(data)

data['지하철이동시간_동대입구역(분)'] = 5
data['지하철이동시간_충무로역(분)'] = 8
data['매물_동입'] = data['지하철이동시간_동대입구역(분)'] + data['도보시간_분']
data['매물_충무로'] = data['지하철이동시간_충무로역(분)'] + data['도보시간_분']
print(data)

data.to_csv('ONEROOM/옥수역_room_data_with_walk.csv', index=False, encoding="utf-8-sig")


