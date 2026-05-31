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

# Кастомный CSS
st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin-bottom: 30px;
    }
    .stat-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        text-align: center;
        transition: transform 0.3s;
        cursor: pointer;
    }
    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 20px rgba(0,0,0,0.15);
    }
    .metric-value {
        font-size: 36px;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-label {
        font-size: 14px;
        color: #666;
        margin-top: 5px;
    }
    </style>
""", unsafe_allow_html=True)

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

# Определяем доставку: если статус WMS "Доставляется", то доставлено
df['Доставлен'] = df['Статус отображение'].apply(
    lambda x: '✅ Доставлен' if x == '🚚 Доставляется' else '🔄 В процессе'
)

# Факт отгрузки = сегодняшняя дата для доставленных
df['Факт отгрузки'] = datetime.now().date() if 'Доставлен' in df.columns else None

# Заголовок
st.markdown("""
<div class="main-header">
    <h1>📦 WMS Dashboard</h1>
    <p>Статусы заказов и детальная информация | Данные с 25 мая 2026</p>
</div>
""", unsafe_allow_html=True)

# Фильтры в сайдбаре
with st.sidebar:
    st.markdown("## 🔍 Фильтры")
    
    if 'Название магазина' in df.columns and len(df) > 0:
        shops = ['Все магазины'] + sorted(df['Название магазина'].dropna().unique().tolist())
        selected_shop = st.selectbox("🏬 Магазин", shops)
        
        if selected_shop != 'Все магазины':
            df_filtered = df[df['Название магазина'] == selected_shop]
        else:
            df_filtered = df.copy()
    else:
        df_filtered = df.copy()
    
    if len(df_filtered) > 0 and 'Город' in df_filtered.columns:
        cities = ['Все города'] + sorted(df_filtered['Город'].dropna().unique().tolist())
        selected_city = st.selectbox("🏙️ Город", cities)
        if selected_city != 'Все города':
            df_filtered = df_filtered[df_filtered['Город'] == selected_city]

if len(df_filtered) == 0:
    st.warning("⚠️ Нет данных для отображения")
    st.stop()

# Фильтр по дате (сегодня)
today = datetime.now().date()
df_today = df_filtered[df_filtered['План дата'].dt.date == today]

# ==================== СТАТУСЫ ЗАКАЗОВ С ВОЗМОЖНОСТЬЮ ПРОВАЛА ====================
st.markdown("## 📊 Статусы заказов")

status_counts = df_filtered['Статус отображение'].value_counts()

# Инициализируем состояние для выбранного статуса
if 'selected_status' not in st.session_state:
    st.session_state.selected_status = None

# Создаем карточки для каждого статуса
num_statuses = len(status_counts)
if num_statuses > 0:
    cols = st.columns(min(num_statuses, 6))
    for idx, (status, count) in enumerate(status_counts.items()):
        if idx < 6:
            with cols[idx]:
                emoji = status.split()[0] if status else "📦"
                # Делаем карточку кликабельной
                if st.button(
                    f"{emoji}\n\n{count}\n\n{status}", 
                    key=f"status_{status}",
                    use_container_width=True
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
    status_table['Факт отгрузки'] = datetime.now().strftime('%d.%m.%Y') if st.session_state.selected_status == "🚚 Доставляется" else "—"
    
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
    if st.button("✖️ Закрыть детали"):
        st.session_state.selected_status = None
        st.rerun()
    
    st.markdown("---")

# ==================== ОБЩАЯ СТАТИСТИКА ЗА СЕГОДНЯ ====================
st.markdown("## 📈 Общая статистика за сегодня")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("📦 Заказов сегодня", len(df_today))

with col2:
    total_items_today = int(df_today['кол-во штук в заказе'].sum())
    st.metric("📦 Товаров сегодня", f"{total_items_today:,}".replace(',', ' '))

with col3:
    in_delivery_today = len(df_today[df_today['Статус отображение'] == "🚚 Доставляется"])
    st.metric("🚚 В доставке", in_delivery_today)

with col4:
    delivered_today = len(df_today[df_today['Доставлен'] == "✅ Доставлен"])
    st.metric("✅ Доставлено", delivered_today)

with col5:
    picking_today = len(df_today[df_today['Статус отображение'].isin(["⏳ Подбирается", "🔄 Сортируется", "📍 В очереди"])])
    st.metric("⏳ В работе", picking_today)

st.markdown("---")

# ==================== ДЕТАЛЬНАЯ ТАБЛИЦА ЗАКАЗОВ ====================
st.markdown("## 📋 Все заказы")

# Подготовка данных для таблицы
df_table = df_filtered.copy()
df_table['План отгрузки'] = df_table['План дата'].dt.strftime('%d.%m.%Y')
df_table['Факт отгрузки'] = datetime.now().strftime('%d.%m.%Y')
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
    st.caption(f"📅 Период: с 25 мая 2026")
with col_info3:
    if 'Название магазина' in df_filtered.columns:
        st.caption(f"🏪 Магазинов: {df_filtered['Название магазина'].nunique()}")
