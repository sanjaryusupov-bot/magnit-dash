import streamlit as st
import pandas as pd

# --- CONFIG ---
ORDERS_URL = "https://docs.google.com/spreadsheets/d/12CxJMCBUHgkaj-_KbOs1aK7hx_jEYMyS3q4Hh0bHTGw/export?format=csv&gid=1369918403"

st.set_page_config(page_title="WMS Dashboard", layout="wide")

# --- LOAD DATA ---
@st.cache_data(ttl=60)
def load_data():
    df = pd.read_csv(ORDERS_URL)
    df = df[df["№ заказа"].astype(str).str.startswith("1M")]
    return df

df = load_data()

# --- STATUS MAP ---
status_map = {
    "IN_DELIVERY": "🚚 Доставляется",
    "SORTED": "✅ Сортирован",
    "SORTING": "🔄 Сортируется",
    "PICKED": "📦 Подобран",
    "PICKING": "⏳ Подбирается",
    "IN_ASSEMBLY": "📍 В очереди"
}

df["Статус"] = df["Статус"].map(status_map)

# --- QUERY PARAM ---
params = st.query_params
shop_param = params.get("shop")

# --- FILTER ---
shops = df["Название магазина"].dropna().unique()

if shop_param:
    shop = shop_param
else:
    shop = st.selectbox("🏬 Магазин", shops)

df = df[df["Название магазина"] == shop]

# --- METRICS ---
col1, col2, col3, col4 = st.columns(4)

col1.metric("📦 Всего заказов", len(df))
col2.metric("🚚 В доставке", len(df[df["Статус"] == "🚚 Доставляется"]))
col3.metric("⏳ В работе", len(df[df["Статус"].isin(["⏳ Подбирается","🔄 Сортируется"])]))
col4.metric("✅ Готово", len(df[df["Статус"] == "✅ Сортирован"]))

st.divider()

# --- GROUP ---
grouped = df.groupby("Статус").agg({
    "№ заказа": "count",
    "кол-во штук в заказе": "sum"
}).reset_index()

grouped.columns = ["Статус", "Кол-во заказов", "Товаров"]

st.subheader("📊 Статусы")
st.dataframe(grouped, use_container_width=True)

st.divider()

# --- TABLE ---
st.subheader("📋 Заказы")
st.dataframe(df, use_container_width=True)

st.divider()

# --- CARDS ---
st.subheader("📦 Карточки")

for _, row in df.iterrows():
    st.markdown(f"""
    <div style="padding:15px;border-radius:15px;background:#1e293b;margin-bottom:10px">
        <h4>{row['№ заказа']} — {row['Статус']}</h4>
        <p>🏬 {row['Название магазина']}</p>
        <p>📦 {row['кол-во штук в заказе']} шт</p>
        <p>📅 {row['Дата отгрузки план']}</p>
    </div>
    """, unsafe_allow_html=True)