import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

ORDERS_URL = "https://docs.google.com/spreadsheets/d/12CxJMCBUHgkaj-_KbOs1aK7hx_jEYMyS3q4Hh0bHTGw/export?format=csv&gid=1369918403"

st.set_page_config(
    page_title="WMS Dashboard", 
    layout="wide",
    page_icon="📦"
)

# Фоновое изображение с прозрачностью
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
.filter-container {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(5px);
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    margin-bottom: 20px;
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

@st.cache_data(ttl=60)
def load_data():
    df = pd.read_csv(ORDERS_URL)
    df.columns = df.columns.str.strip()
    return df

df = load_data()

# Отображаем только нужные колонки
needed_columns = [
    '№ заказа', 'ID магазина', 'Название магазина', 
    'Адрес магазина', 'кол-во штук в заказе', 
    'Дата отгрузки план', 'Город', 'Статус сборки', 
    'Статус WMS', 'Статус отгрузки на хаб'
]

existing_columns = [col for col in needed_columns if col in df.columns]
df = df[existing_columns]

# Конвертируем даты
if 'Дата отгрузки план' in df.columns:
    df['План дата'] = pd.to_datetime(df['Дата отгрузки план'], errors='coerce')

# Фильтр: только заказы с 25 мая 2026
cutoff_date = datetime(2026, 5, 25)
df = df[df['План дата'] >= cutoff_date]

# Маппинг статусов
status_display = {
    "IN_DELIVERY": "🚚 Доставляется",
    "SORTED": "✅ Сортирован",
    "SORTING": "🔄 Сортируется",
    "PICKED": "📦 Подобран",
    "PICKING": "⏳ Подбирается",
    "IN_ASSEMBLY": "📍 В очереди",
}

# Применяем статусы WMS
if 'Статус WMS' in df.columns:
    df['Статус отображение'] = df['Статус WMS'].map(status_display).fillna(df['Статус WMS'])
    df = df[df['Статус отображение'].notna()]

# Конвертируем количество товаров
if 'кол-во штук в заказе' in df.columns:
    df['кол-во штук в заказе'] = pd.to_numeric(df['кол-во штук в заказе'], errors='coerce').fillna(0)

# Определяем доставку и дату факта отгрузки
df['Дата факт отгрузки'] = pd.NaT
df['Доставлен'] = '🔄 В процессе'

for idx, row in df.iterrows():
    if row['Статус отображение'] == "🚚 Доставляется":
        df.at[idx, 'Доставлен'] = '✅ Доставлен'
        df.at[idx, 'Дата факт отгрузки'] = datetime.now()

# Заголовок
st.markdown("""
<div class="main-header">
    <h1>📦 WMS Dashboard</h1>
    <p>Статусы заказов и детальная информация | Данные с 25 мая 2026</p>
</div>
""", unsafe_allow_html=True)

# ==================== ФИЛЬТРЫ ====================
st.markdown("## 🔍 Фильтры")

# Инициализируем переменные для фильтров
selected_city = 'Все города'
selected_shop = 'Все магазины'

# Создаем контейнер для фильтров
with st.container():
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        st.markdown('<div class="filter-label">📅 Диапазон дат план отгрузки</div>', unsafe_allow_html=True)
        # Диапазон дат за весь период
        min_date = df['План дата'].min().date() if not df.empty else datetime(2026, 5, 25).date()
        max_date = df['План дата'].max().date() if not df.empty else datetime.now().date()
        
        date_range = st.date_input(
            "Выберите период",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            label_visibility="collapsed"
        )
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            df_filtered = df[(df['План дата'].dt.date >= start_date) & (df['План дата'].dt.date <= end_date)]
        else:
            df_filtered = df.copy()
    
    with col_filter2:
        st.markdown('<div class="filter-label">🏙️ Город</div>', unsafe_allow_html=True)
        if 'Город' in df.columns and len(df_filtered) > 0:
            cities = ['Все города'] + sorted(df_filtered['Город'].dropna().unique().tolist())
            selected_city = st.selectbox(
                "Выберите город",
                options=cities,
                index=0,
                label_visibility="collapsed"
            )
            if selected_city != 'Все города':
                df_filtered = df_filtered[df_filtered['Город'] == selected_city]
    
    with col_filter3:
        st.markdown('<div class="filter-label">🏬 Магазин</div>', unsafe_allow_html=True)
        if 'Название магазина' in df.columns and len(df_filtered) > 0:
            shops = ['Все магазины'] + sorted(df_filtered['Название магазина'].dropna().unique().tolist())
            selected_shop = st.selectbox(
                "Выберите магазин",
                options=shops,
                index=0,
                label_visibility="collapsed"
            )
            if selected_shop != 'Все магазины':
                df_filtered = df_filtered[df_filtered['Название магазина'] == selected_shop]

# Показываем активные фильтры
if len(date_range) == 2:
    st.caption(f"📅 Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")
if 'selected_city' in locals() and selected_city != 'Все города':
    st.caption(f"🏙️ Город: {selected_city}")
if 'selected_shop' in locals() and selected_shop != 'Все магазины':
    st.caption(f"🏬 Магазин: {selected_shop}")

st.markdown("---")

if len(df_filtered) == 0:
    st.warning("⚠️ Нет данных для отображения")
    st.stop()

# ==================== СТАТУСЫ ЗАКАЗОВ С ВОЗМОЖНОСТЬЮ ПРОВАЛА ====================
st.markdown("## 📊 Статусы заказов")

# Правильный порядок статусов
status_order = [
    "📍 В очереди",
    "⏳ Подбирается", 
    "📦 Подобран",
    "🔄 Сортируется",
    "✅ Сортирован",
    "🚚 Доставляется",
    "✅ Доставлен"
]

# Получаем counts в правильном порядке
status_counts = {}
for status in status_order:
    count = len(df_filtered[df_filtered['Статус отображение'] == status])
    if count > 0:
        status_counts[status] = count

# Инициализируем состояние для выбранного статуса
if 'selected_status' not in st.session_state:
    st.session_state.selected_status = None

# Создаем карточки в правильном порядке
if len(status_counts) > 0:
    cols = st.columns(min(len(status_counts), 7))
    for idx, (status, count) in enumerate(status_counts.items()):
        if idx < 7:
            with cols[idx]:
                emoji = status.split()[0] if status else "📦"
                
                # Делаем карточку кликабельной с красивым стилем
                if st.button(
                    f"{emoji}\n\n{count}\n\n{status}", 
                    key=f"status_{status}",
                    use_container_width=True,
                    type="primary" if status in ["✅ Доставлен", "🚚 Доставляется"] else "secondary"
                ):
                    st.session_state.selected_status = status
                    st.rerun()

# Отображаем детали выбранного статуса
if st.session_state.selected_status:
    st.markdown(f"### 📋 Заказы со статусом: {st.session_state.selected_status}")
    
    # Фильтруем заказы по выбранному статусу
    status_orders = df_filtered[df_filtered['Статус отображение'] == st.session_state.selected_status]
    
    # Подготовка таблицы
    status_table = status_orders.copy()
    status_table['План отгрузки'] = status_table['План дата'].dt.strftime('%d.%m.%Y')
    status_table['Факт отгрузки'] = status_table['Дата факт отгрузки'].dt.strftime('%d.%m.%Y') if 'Дата факт отгрузки' in status_table else "—"
    status_table['Факт отгрузки'] = status_table['Факт отгрузки'].fillna("—")
    
    # Выбираем колонки
    detail_cols = ['№ заказа', 'Название магазина', 'Город', 'кол-во штук в заказе', 
                   'План отгрузки', 'Факт отгрузки', 'Доставлен']
    detail_names = ['№ заказа', 'Магазин', 'Город', 'Кол-во товаров', 
                    'План отгрузки', 'Факт отгрузки', 'Доставка']
    
    detail_display = pd.DataFrame()
    for col, name in zip(detail_cols, detail_names):
        if col in status_table.columns:
            detail_display[name] = status_table[col]
    
    st.dataframe(detail_display, use_container_width=True, height=400)
    
    # Кнопка закрытия
    if st.button("✖️ Закрыть детали", use_container_width=True):
        st.session_state.selected_status = None
        st.rerun()
    
    st.markdown("---")

# ==================== ОБЩАЯ СТАТИСТИКА ЗА ПЕРИОД ====================
st.markdown(f"## 📈 Общая статистика за выбранный период")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("📦 Всего заказов", len(df_filtered))

with col2:
    total_items = int(df_filtered['кол-во штук в заказе'].sum())
    st.metric("📦 Всего товаров", f"{total_items:,}".replace(',', ' '))

with col3:
    in_delivery = len(df_filtered[df_filtered['Статус отображение'] == "🚚 Доставляется"])
    st.metric("🚚 В доставке", in_delivery)

with col4:
    delivered = len(df_filtered[df_filtered['Доставлен'] == "✅ Доставлен"])
    st.metric("✅ Доставлено", delivered)

with col5:
    picking = len(df_filtered[df_filtered['Статус отображение'].isin(["⏳ Подбирается", "🔄 Сортируется", "📍 В очереди"])])
    st.metric("⏳ В работе", picking)

st.markdown("---")

# ==================== ДЕТАЛЬНАЯ ТАБЛИЦА ЗАКАЗОВ ====================
st.markdown("## 📋 Все заказы")

# Подготовка данных для таблицы
df_table = df_filtered.copy()
df_table['План отгрузки'] = df_table['План дата'].dt.strftime('%d.%m.%Y')
df_table['Факт отгрузки'] = df_table['Дата факт отгрузки'].dt.strftime('%d.%m.%Y %H:%M') if 'Дата факт отгрузки' in df_table else "—"
df_table['Факт отгрузки'] = df_table['Факт отгрузки'].fillna("—")
df_table['Статус заказа'] = df_table['Статус отображение']

# Выбираем колонки для отображения
display_cols = ['№ заказа', 'Название магазина', 'Город', 'кол-во штук в заказе', 
                'План отгрузки', 'Факт отгрузки', 'Статус заказа', 'Доставлен']

display_names = ['№ заказа', 'Магазин', 'Город', 'Кол-во товаров', 
                 'План отгрузки', 'Факт отгрузки', 'Статус WMS', 'Доставка']

df_display = pd.DataFrame()
for col, name in zip(display_cols, display_names):
    if col in df_table.columns:
        df_display[name] = df_table[col]

# Поиск по заказам
search = st.text_input("🔍 Поиск по номеру заказа", placeholder="Введите номер заказа...")
if search:
    df_display = df_display[df_display['№ заказа'].astype(str).str.contains(search, case=False)]

# Отображаем таблицу
st.dataframe(df_display, use_container_width=True, height=500)

# ==================== ЭКСПОРТ ДАННЫХ ====================
with st.expander("📥 Экспорт данных"):
    csv_data = df_display.to_csv(index=False)
    st.download_button(
        label="📥 Скачать данные в CSV",
        data=csv_data,
        file_name=f"wms_orders_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

# Информация об обновлении
st.markdown("---")
col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    st.caption(f"🔄 Данные обновлены: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
with col_info2:
    st.caption(f"📅 Данные с 25 мая 2026")
with col_info3:
    if 'Название магазина' in df_filtered.columns:
        st.caption(f"🏪 Магазинов: {df_filtered['Название магазина'].nunique()}")
