import streamlit as st
import pandas as pd

ORDERS_URL = "https://docs.google.com/spreadsheets/d/12CxJMCBUHgkaj-_KbOs1aK7hx_jEYMyS3q4Hh0bHTGw/export?format=csv&gid=1369918403"

st.set_page_config(page_title="WMS Dashboard", layout="wide")

@st.cache_data(ttl=60)
def load_data():
    df = pd.read_csv(ORDERS_URL)

    # 🔥 чистим названия колонок
    df.columns = df.columns.str.strip()

    return df

df = load_data()

# 👇 ПОСМОТРИ КАК НАЗЫВАЮТСЯ КОЛОНКИ
st.write("Колонки в таблице:", df.columns.tolist())

# --- ищем статус колонку автоматически ---
status_col = None

for col in df.columns:
    if "статус" in col.lower():
        status_col = col
        break

if not status_col:
    st.error("❌ Колонка 'Статус' не найдена")
    st.stop()

# --- фильтр заказов ---
order_col = None
for col in df.columns:
    if "заказ" in col.lower():
        order_col = col
        break

df = df[df[order_col].astype(str).str.startswith("1M")]

# --- статус мап ---
status_map = {
    "IN_DELIVERY": "🚚 Доставляется",
    "SORTED": "✅ Сортирован",
    "SORTING": "🔄 Сортируется",
    "PICKED": "📦 Подобран",
    "PICKING": "⏳ Подбирается",
    "IN_ASSEMBLY": "📍 В очереди"
}

df["Статус норм"] = df[status_col].map(status_map)

# --- магазин ---
shop_col = None
for col in df.columns:
    if "магазин" in col.lower():
        shop_col = col
        break

shops = df[shop_col].dropna().unique()
shop = st.selectbox("🏬 Магазин", shops)

df = df[df[shop_col] == shop]

# --- UI ---
st.title("📦 WMS Dashboard")

col1, col2 = st.columns(2)
col1.metric("📦 Заказы", len(df))
col2.metric("🚚 В доставке", len(df[df["Статус норм"] == "🚚 Доставляется"]))

st.dataframe(df, use_container_width=True)
