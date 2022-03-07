import os
import sys
import time
import streamlit as st
from pathlib import Path
import folium
from streamlit_folium import folium_static
import pandas as pd
import urllib.request as req
import json
import geocoder as ge
import branca
import altair as alt

#気象庁ページから地点情報取得
url = 'https://www.jma.go.jp/bosai/forecast/data/forecast/010000.json'
filename = 'forecast.json'
data = req.urlopen(url).read()

#jsonデータの生成
with open(filename,mode="wb",) as f:
    f.write(data)

with open('forecast.json','r',encoding="utf-8") as f:
    json_data = json.load(f)


#各気象台の地点コードリスト
office_code = [s['officeCode'] for s in json_data]

#地点名のリスト
area_name = [s['name'] for s in json_data]

#地点の座標リスト
place = []

#リロード時に毎回読み込まないように(ここが時間かかる)
@st.cache
def get_coordinate():
    for s in area_name:
        #ヒットしない地点があるので市役所で検索
        place_check = ge.arcgis(s+'市役所')
        place.append(place_check.latlng)
    return place
place = get_coordinate()

#各地点の名前、座標のdataframe
df = pd.DataFrame(
    data=place,
    index=area_name,
    columns=["x","y"]
)
#dfに地点コードを追加
df['code'] = office_code

#データを地図に渡す関数
def AreaMaker(df,map_data):
    for index,r in df.iterrows():
        html=f'<a href=https://www.jma.go.jp/bosai/forecast/#area_type=offices&area_code={r.code} target="_blank"> {index}周辺の天気予報 </a>'
        iframe = branca.element.IFrame(html=html, width=200, height=50)
        popup = folium.Popup(iframe, max_width=200)
        #ピンを置く
        folium.Marker(
            location=[r.x,r.y],
            popup = popup,
        ).add_to(map_data)

#気温のcsv読み込み
df_temp = pd.read_csv('temp.csv',index_col=0)

#画面設計------------------
st.title('**全国天気予報**')
st.write('こちらは、気象庁( https://www.jma.go.jp/ )にて提供されているデータを使用しています')
st.write('ピンをクリックすると、気象庁への詳細天気予報ページに飛びます')
st.write('年間平均気温は、 Weather Spark(https://ja.weatherspark.com/ )のデータを使用しています')

#map挿入
map_data = folium.Map(location=[37.0, 135.0],zoom_start=5)
AreaMaker(df,map_data)
folium_static(map_data)

#気温グラフの表示

areas = st.multiselect(
    '地点を選択してください',
    options=list(df_temp.index),
    default='釧路'
    )
if not areas:
    st.error('少なくとも1つは選んでください')

else:
    graph_data = df_temp.loc[areas]
    st.write('### 年間平均気温', graph_data)
    graph_data = graph_data.T.reset_index()
    graph_data = pd.melt(graph_data, id_vars=['index']).rename(
        columns={'value':'temperature','variable':'Area'}
    )
    graph_data = graph_data.rename(columns={'index':'Month'})
    chart = (
        alt.Chart(graph_data).mark_line(opacity=0.8,clip=True)
        .encode(
            #:T 日付型への変換　:O　時系列型への変換 Q:
            x='Month:Q',
            y=alt.Y('temperature',stack=None,scale=alt.Scale(domain=[-20,35])),
            color='Area:N'
        )
    )
st.altair_chart(chart,use_container_width=True)
