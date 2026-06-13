import sqlite3
import requests
import streamlit as st
import pandas as pd
import plotly.express as px # biêu đồ
import os

def create_table():
    conn = sqlite3.connect('weather.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS favorite_cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_name TEXT NOT NULL UNIQUE,
            added_date TEXT,
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'weather.db')

def get_connection():
    return sqlite3.connect(DB_PATH)

def add_city(city_name):
    try:
        with get_connection() as conn:
            conn.execute(
                'INSERT INTO favorite_cities (city_name) VALUES (?)',
                (city_name,)
            )
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print('DB ERROR:', e)
        return False

def view_all_cities():
    with get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM favorite_cities", conn)

def delete_city(city_name):
    with get_connection() as conn:
        conn.execute('DELETE FROM favorite_cities WHERE city_name=?', (city_name,))

API_KEY = st.secrets['api_key']
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

def get_weather(city_name):
    try:
        url = f"{BASE_URL}?q={city_name}&appid={API_KEY}&units=metric&lang=vi"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            return {
                "city": data["name"],
                "temp": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "description": data["weather"][0]["description"],
                "icon": data["weather"][0]["icon"]
            }
        return None
    except Exception:
        return None

def setup_page():
    st.set_page_config(
        page_title="Dự Báo Thời Tiết",
        page_icon="⛅",
        layout="wide"
    )
    st.markdown("""
        <style>
        .stApp { background: linear-gradient(to right, #e0f7fa, #80deea); }
        .big-font { font-size: 20px !important; }
        </style>
    """, unsafe_allow_html=True)

def show_header():
    st.title("⛅ App Thời Tiết Thông Minh")
    st.markdown("Nhập tên thành phố để xem nhiệt độ hiện tại.")
    st.markdown("---")

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

create_table()
setup_page()
show_header()

st.sidebar.header("❤️ Thành phố yêu thích")
df_cities = view_all_cities()

if not df_cities.empty:
    list_city_names = df_cities['city_name'].tolist()
    st.sidebar.write("Danh sách đã lưu:")
    for city in list_city_names:
        st.sidebar.text(f"- {city}")

    st.sidebar.markdown("---")
    city_to_delete = st.sidebar.selectbox("Chọn thành phố để xóa", list_city_names)
if st.sidebar.button("Xóa khỏi danh sách"):
    delete_city(city_to_delete)
    st.success(f"Đã xóa {city_to_delete}")
    st.rerun()
else:
    st.sidebar.info("Chưa có thành phố nào được lưu.")

tab1, tab2 = st.tabs(["🔍 Tra cứu & Lưu trữ", "📊 Thống kê & So sánh"])

with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        city_input = st.text_input(
            "Nhập tên thành phố",
            placeholder="Hanoi, Hong Kong, New York..."
        )
    with col2:
        st.write("")
        st.write("")
        search_btn = st.button("Xem")

    if search_btn and city_input:
        with st.spinner('Đang tải...'):
            data = get_weather(city_input)

            if data:
                st.session_state.weather_data = data
            else:
                st.session_state.weather_data = None
                st.error("❌ Không tìm thấy thành phố này!")

    if "weather_data" in st.session_state and st.session_state.weather_data:
        data = st.session_state.weather_data

        st.success(f"{data['city']}")
        col_a, col_b = st.columns(2)
        with col_a:
            icon_url = f"http://openweathermap.org/img/wn/{data['icon']}@4x.png"
            st.image(icon_url, width=120)
            st.caption(data['description'].capitalize())
        with col_b:
            st.metric("Nhiệt độ", f"{data['temp']} °C")
            st.metric("Độ ẩm", f"{data['humidity']} %")

        st.markdown("---")
        if st.button(f"❤️ Lưu {data['city']} vào danh sách"):
            saved = add_city(data['city'])
            if saved:
                st.success("Đã lưu thành công!")
                st.rerun()
            else:
                st.warning("Thành phố đã tồn tại hoặc lỗi khi lưu.")

    st.markdown("---")
    st.caption("Tip: dùng 'Ho Chi Minh' hoặc 'Saigon'")

with tab2:
    st.subheader("So sánh thời tiết các thành phố đã lưu")

    if df_cities.empty:
        st.info("Hãy lưu ít nhất 1 thành phố ở Tab Tra cứu để xem biểu đồ.")
    else:
        if st.button("Cập nhật dữ liệu mới nhất"):
            list_names = df_cities['city_name'].tolist()
            report_data = []

            my_bar = st.progress(0)
            for i, name in enumerate(list_names):
                info = get_weather(name)
                if info:
                    report_data.append(info)
                my_bar.progress((i + 1) / len(list_names))

            df_report = pd.DataFrame(report_data)

            st.write("### 🌡️ So sánh Nhiệt độ (°C)")
            fig = px.bar(df_report, x='city', y='temp', color='temp',
                         color_continuous_scale='RdYlBu_r')
            st.plotly_chart(fig, use_container_width=True)

            st.write("### 📋 Bảng dữ liệu chi tiết")
            st.dataframe(df_report)

            csv = convert_df_to_csv(df_report)
            st.download_button(
                label="📥 Tải báo cáo về máy (CSV)",
                data=csv,
                file_name='thoi_tiet_yeu_thich.csv',
                mime='text/csv',
            )
