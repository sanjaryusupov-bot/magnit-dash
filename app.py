import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# --- Ссылки на Google Sheets (CSV экспорт) ---
ORDERS_URL = "https://docs.google.com/spreadsheets/d/12CxJMCBUHgkaj-_KbOs1aK7hx_jEYMyS3q4Hh0bHTGw/export?format=csv&gid=1369918403"          # Заказы
SHIPMENTS_URL = "https://docs.google.com/spreadsheets/d/12CxJMCBUHgkaj-_KbOs1aK7hx_jEYMyS3q4Hh0bHTGw/export?format=csv&gid=115422827"     # Статус по отгрузкам

st.set_page_config(
    page_title="WMS Dashboard", 
    layout="wide",
    page_icon="📦"
)

# --- Фоновое изображение с прозрачностью ---
background_image = """
<style>
.stApp {
    background-image: url("https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?q=80&w=2070&auto=format&fit=crop");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}
.stApp::before {
    content: "";
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(255, 255, 255, 0.85);
    z-index: 0;
}
.stApp > div {
    position: relative;
    z-index: 1;
}
.main-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
    border-radius: 15px;
    color: white;
    margin-bottom: 30px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}
.stat-card {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(5px);
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    text-align: center;
    transition: all 0.3s ease;
    cursor: pointer;
    border: 2px solid transparent;
}
.stat-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 5px 20px rgba(0,0,0,0.15);
    border-color: #667eea;
    background: white;
}
.metric-value {
    font-size: 36px;
    font-weight: bold;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 10px 0;
}
.metric-label {
    font-size: 14px;
    color: #333;
    margin-top: 5px;
    font-weight: 500;
}
.filter-label {
    font-weight: 600;
    color: #333;
    margin-bottom: 8px;
    font-size: 14px;
}
div[data-testid="stMetricValue"] {
    font-size: 28px;
    font-weight: bold;
    color: #333;
}
div[data-testid="stMetricLabel"] {
    font-weight: 500;
    color: #333;
}
.stDataFrame {
    background: rgba(255, 255, 255, 0.95);
    border-radius: 10px;
    padding: 10px;
}
h1, h2, h3, p, .stMarkdown {
    color: #333 !important;
}
</style>
"""
st.markdown(background_image, unsafe_allow_html=True)

# --- Загрузка данных ---
@st.cache_data(ttl=60)
def load_data():
    # 1. Заказы
    df_orders = pd.read_csv(ORDERS_URL)
    df_orders.columns = df_orders.columns.str.strip()
    
    # 2. Статус по отгрузкам (фактические даты отгрузки)
    try:
        df_ship = pd.read_csv(SHIPMENTS_URL)
        df_ship.columns = df_ship.columns.str.strip()
        # Ожидаем колонки: 'B' = Дата отгрузки, 'C' = Заказ (или по именам)
        # На всякий случай переименуем первые две колонки, если они безымянные
        if len(df_ship.columns) >= 2:
            df_ship = df_ship.iloc[:, :2]  # берём первые две колонки
            df_ship.columns = ['Дата отгрузки', 'Заказ']
        # Приводим дату к datetime (только дата)
        df_ship['Дата отгрузки'] = pd.to_datetime(df_ship['Дата отгрузки'], errors='coerce').dt.date
        # Удаляем строки без номера заказа
        df_ship = df_ship.dropna(subset=['Заказ'])
        df_ship['Заказ'] = df_ship['Заказ'].astype(str).str.strip()
    except Exception as e:
        st.warning(f"Не удалось загрузить данные отгрузок: {e}")
        df_ship = pd.DataFrame(columns=['Заказ', 'Дата отгрузки'])
    
    return df_orders, df_ship

df_orders, df_ship = load_data()

# --- Подготовка основного датафрейма заказов ---
needed_columns = [
    '№ заказа', 'ID магазина', 'Название магазина', 
    'Адрес магазина', 'кол-во штук в заказе', 
    'Дата отгрузки план', 'Город', 'Статус сборки', 
    'Статус WMS', 'Статус отгрузки на хаб'
]
existing_columns = [col for col in needed_columns if col in df_orders.columns]
df = df_orders[existing_columns].copy()

# Дата план
if 'Дата отгрузки план' in df.columns:
    df['План дата'] = pd.to_datetime(df['Дата отгрузки план'], errors='coerce')
    cutoff_date = datetime(2026, 5, 25)
    df = df[df['План дата'] >= cutoff_date]

# Маппинг статусов WMS
status_display = {
    "IN_DELIVERY": "🚚 Доставляется",
    "SORTED": "✅ Сортирован",
    "SORTING": "🔄 Сортируется",
    "PICKED": "📦 Подобран",
    "PICKING": "⏳ Подбирается",
    "IN_ASSEMBLY": "📍 В очереди",
}
if 'Статус WMS' in df.columns:
    df['Статус отображение'] = df['Статус WMS'].map(status_display).fillna(df['Статус WMS'])
    df = df[df['Статус отображение'].notna()]

# Количество товаров
if 'кол-во штук в заказе' in df.columns:
    df['кол-во штук в заказе'] = pd.to_numeric(df['кол-во штук в заказе'], errors='coerce').fillna(0)

# --- Добавляем фактические даты отгрузки из второго листа ---
df['Заказ_ключ'] = df['№ заказа'].astype(str).str.strip()
df_ship['Заказ_ключ'] = df_ship['Заказ'].astype(str).str.strip()

# Объединяем с данными отгрузок
df = df.merge(df_ship[['Заказ_ключ', 'Дата отгрузки']], on='Заказ_ключ', how='left')
df.rename(columns={'Дата отгрузки': 'Дата факт отгрузки'}, inplace=True)

# Статус доставки: Доставлен = есть дата факт, иначе В процессе
df['Доставлен'] = df['Дата факт отгрузки'].apply(lambda x: '✅ Доставлен' if pd.notna(x) else '🔄 В процессе')

# Для заказов со статусом WMS "Доставляется" – тоже считаем доставленными, если есть дата
# (логика остаётся: если есть дата из второго листа – доставлен)
# Ничего дополнительно не меняем.

# --- Заголовок ---
st.markdown("""
<div class="main-header">
    <h1>📦 WMS Dashboard</h1>
    <p>Статусы заказов и детальная информация | Данные с 25 мая 2026</p>
</div>
""", unsafe_allow_html=True)

# --- ФИЛЬТРЫ ---
st.markdown("## 🔍 Фильтры")

selected_city = 'Все города'
selected_shop = 'Все магазины'

with st.container():
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        st.markdown('<div class="filter-label">📅 Диапазон дат план отгрузки</div>', unsafe_allow_html=True)
        min_date = df['План дата'].min().date() if not df.empty else datetime(2026, 5, 25).date()
        max_date = df['План дата'].max().date() if not df.empty else datetime.now().date()
        date_range = st.date_input("Выберите период", value=(min_date, max_date), min_value=min_date, max_value=max_date, label_visibility="collapsed")
        if len(date_range) == 2:
            start_date, end_date = date_range
            df_filtered = df[(df['План дата'].dt.date >= start_date) & (df['План дата'].dt.date <= end_date)]
        else:
            df_filtered = df.copy()
    
    with col_filter2:
        st.markdown('<div class="filter-label">🏙️ Город</div>', unsafe_allow_html=True)
        if 'Город' in df.columns and len(df_filtered) > 0:
            cities = ['Все города'] + sorted(df_filtered['Город'].dropna().unique().tolist())
            selected_city = st.selectbox("Выберите город", options=cities, index=0, label_visibility="collapsed")
            if selected_city != 'Все города':
                df_filtered = df_filtered[df_filtered['Город'] == selected_city]
    
    with col_filter3:
        st.markdown('<div class="filter-label">🏬 Магазин</div>', unsafe_allow_html=True)
        if 'Название магазина' in df.columns and len(df_filtered) > 0:
            shops = ['Все магазины'] + sorted(df_filtered['Название магазина'].dropna().unique().tolist())
            selected_shop = st.selectbox("Выберите магазин", options=shops, index=0, label_visibility="collapsed")
            if selected_shop != 'Все магазины':
                df_filtered = df_filtered[df_filtered['Название магазина'] == selected_shop]

if len(date_range) == 2:
    st.caption(f"📅 Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")
if selected_city != 'Все города':
    st.caption(f"🏙️ Город: {selected_city}")
if selected_shop != 'Все магазины':
    st.caption(f"🏬 Магазин: {selected_shop}")
st.markdown("---")

if df_filtered.empty:
    st.warning("⚠️ Нет данных для отображения")
    st.stop()

# --- СТАТУСЫ ЗАКАЗОВ (ПРОВАЛ) ---
st.markdown("## 📊 Статусы заказов")

status_order = ["📍 В очереди", "⏳ Подбирается", "📦 Подобран", "🔄 Сортируется", "✅ Сортирован", "🚚 Доставляется", "✅ Доставлен"]
status_counts = {}
for status in status_order:
    cnt = len(df_filtered[df_filtered['Статус отображение'] == status])
    if cnt > 0:
        status_counts[status] = cnt

if 'selected_status' not in st.session_state:
    st.session_state.selected_status = None

if status_counts:
    cols = st.columns(min(len(status_counts), 7))
    for idx, (status, count) in enumerate(status_counts.items()):
        with cols[idx]:
            emoji = status.split()[0]
            if st.button(f"{emoji}\n\n{count}\n\n{status}", key=f"status_{status}", use_container_width=True,
                         type="primary" if status in ["✅ Доставлен", "🚚 Доставляется"] else "secondary"):
                st.session_state.selected_status = status
                st.rerun()

if st.session_state.selected_status:
    st.markdown(f"### 📋 Заказы со статусом: {st.session_state.selected_status}")
    status_orders = df_filtered[df_filtered['Статус отображение'] == st.session_state.selected_status]
    status_table = status_orders.copy()
    status_table['План отгрузки'] = status_table['План дата'].dt.strftime('%d.%m.%Y')
    status_table['Факт отгрузки'] = status_table['Дата факт отгрузки'].apply(lambda x: x.strftime('%d.%m.%Y') if pd.notna(x) else "—")
    detail_cols = ['№ заказа', 'Название магазина', 'Город', 'кол-во штук в заказе', 'План отгрузки', 'Факт отгрузки', 'Доставлен']
    detail_names = ['№ заказа', 'Магазин', 'Город', 'Кол-во товаров', 'План отгрузки', 'Факт отгрузки', 'Доставка']
    detail_display = pd.DataFrame({name: status_table[col] for col, name in zip(detail_cols, detail_names) if col in status_table})
    st.dataframe(detail_display, use_container_width=True, height=400)
    if st.button("✖️ Закрыть детали", use_container_width=True):
        st.session_state.selected_status = None
        st.rerun()
    st.markdown("---")

# --- ОБЩАЯ СТАТИСТИКА ЗА ПЕРИОД ---
st.markdown("## 📈 Общая статистика за выбранный период")
col1, col2, col3, col4, col5 = st.columns(5)
with col1: st.metric("📦 Всего заказов", len(df_filtered))
with col2: st.metric("📦 Всего товаров", f"{int(df_filtered['кол-во штук в заказе'].sum()):,}".replace(',', ' '))
with col3: st.metric("🚚 В доставке", len(df_filtered[df_filtered['Статус отображение'] == "🚚 Доставляется"]))
with col4: st.metric("✅ Доставлено", len(df_filtered[df_filtered['Доставлен'] == "✅ Доставлен"]))
with col5: st.metric("⏳ В работе", len(df_filtered[df_filtered['Статус отображение'].isin(["⏳ Подбирается", "🔄 Сортируется", "📍 В очереди"])]))
st.markdown("---")

# --- ДЕТАЛЬНАЯ ТАБЛИЦА ВСЕХ ЗАКАЗОВ ---
st.markdown("## 📋 Все заказы")
df_table = df_filtered.copy()
df_table['План отгрузки'] = df_table['План дата'].dt.strftime('%d.%m.%Y')
df_table['Факт отгрузки'] = df_table['Дата факт отгрузки'].apply(lambda x: x.strftime('%d.%m.%Y') if pd.notna(x) else "—")
df_table['Статус заказа'] = df_table['Статус отображение']
display_cols = ['№ заказа', 'Название магазина', 'Город', 'кол-во штук в заказе', 'План отгрузки', 'Факт отгрузки', 'Статус заказа', 'Доставлен']
display_names = ['№ заказа', 'Магазин', 'Город', 'Кол-во товаров', 'План отгрузки', 'Факт отгрузки', 'Статус WMS', 'Доставка']
df_display = pd.DataFrame({name: df_table[col] for col, name in zip(display_cols, display_names) if col in df_table})

search = st.text_input("🔍 Поиск по номеру заказа", placeholder="Введите номер заказа...")
if search:
    df_display = df_display[df_display['№ заказа'].astype(str).str.contains(search, case=False)]
st.dataframe(df_display, use_container_width=True, height=500)

# --- ЭКСПОРТ ---
with st.expander("📥 Экспорт данных"):
    st.download_button("📥 Скачать данные в CSV", df_display.to_csv(index=False), f"wms_orders_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", "text/csv")

# --- ИНФОРМАЦИЯ ОБ ОБНОВЛЕНИИ ---
st.markdown("---")
col_info1, col_info2, col_info3 = st.columns(3)
with col_info1: st.caption(f"🔄 Данные обновлены: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
with col_info2: st.caption(f"📅 Данные с 25 мая 2026")
with col_info3: st.caption(f"🏪 Магазинов: {df_filtered['Название магазина'].nunique()}")
