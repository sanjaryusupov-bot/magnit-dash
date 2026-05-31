import streamlit as st
import pandas as pd
from datetime import datetime

ORDERS_URL = "https://docs.google.com/spreadsheets/d/12CxJMCBUHgkaj-_KbOs1aK7hx_jEYMyS3q4Hh0bHTGw/export?format=csv&gid=1369918403"

st.set_page_config(
    page_title="WMS Dashboard", 
    layout="wide",
    page_icon="📦"
)

# Кастомный CSS
st.markdown("""
    <style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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

# Фильтруем существующие колонки
existing_columns = [col for col in needed_columns if col in df.columns]
df = df[existing_columns]

# Только эти статусы
status_display = {
    "IN_DELIVERY": "🚚 Доставляется",
    "SORTED": "✅ Сортирован",
    "SORTING": "🔄 Сортируется",
    "PICKED": "📦 Подобран",
    "PICKING": "⏳ Подбирается",
    "IN_ASSEMBLY": "📍 В очереди",
}

# Применяем статусы и фильтруем только нужные
if 'Статус WMS' in df.columns:
    # Маппим только нужные статусы, остальные делаем NaN
    df['Статус отображение'] = df['Статус WMS'].map(status_display)
    # Удаляем строки с другими статусами
    df = df[df['Статус отображение'].notna()]

# Заголовок
st.title("📦 WMS Dashboard")
st.markdown("---")

# Фильтры
with st.sidebar:
    st.header("🔍 Фильтры")
    
    if 'Название магазина' in df.columns:
        shops = ['Все магазины'] + sorted(df['Название магазина'].dropna().unique().tolist())
        selected_shop = st.selectbox("🏬 Выберите магазин", shops)
        
        if selected_shop != 'Все магазины':
            df_filtered = df[df['Название магазина'] == selected_shop]
        else:
            df_filtered = df.copy()
    else:
        df_filtered = df.copy()
        selected_shop = 'Все магазины'
    
    if 'Город' in df_filtered.columns:
        cities = ['Все города'] + sorted(df_filtered['Город'].dropna().unique().tolist())
        selected_city = st.selectbox("🏙️ Город", cities)
        
        if selected_city != 'Все города':
            df_filtered = df_filtered[df_filtered['Город'] == selected_city]
    
    if 'Статус отображение' in df_filtered.columns:
        statuses = ['Все статусы'] + sorted(df_filtered['Статус отображение'].dropna().unique().tolist())
        selected_status = st.selectbox("📊 Статус", statuses)
        
        if selected_status != 'Все статусы':
            df_filtered = df_filtered[df_filtered['Статус отображение'] == selected_status]

# Метрики
st.subheader("📈 Ключевые показатели")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📦 Всего заказов", len(df_filtered))

with col2:
    if 'кол-во штук в заказе' in df_filtered.columns:
        total_items = int(df_filtered['кол-во штук в заказе'].sum())
        st.metric("📦 Всего товаров", f"{total_items:,}".replace(',', ' '))

with col3:
    if 'Статус отображение' in df_filtered.columns:
        delivered = len(df_filtered[df_filtered['Статус отображение'] == "🚚 Доставляется"])
        st.metric("🚚 В доставке", delivered)

with col4:
    if 'Город' in df_filtered.columns:
        cities_count = df_filtered['Город'].nunique()
        st.metric("🏙️ Городов", cities_count)

st.markdown("---")

# Статистика по статусам (только 6 статусов)
st.subheader("📊 Статусы заказов")
if 'Статус отображение' in df_filtered.columns:
    status_counts = df_filtered['Статус отображение'].value_counts()
    
    # Отображаем статусы в виде цветных карточек
    cols = st.columns(min(len(status_counts), 6))
    for idx, (status, count) in enumerate(status_counts.items()):
        with cols[idx % 6]:
            st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; text-align: center; margin: 5px;">
                <div style="font-size: 28px; font-weight: bold;">{count}</div>
                <div style="font-size: 14px; color: #666;">{status}</div>
            </div>
            """, unsafe_allow_html=True)

# Статистика по городам
st.markdown("---")
st.subheader("🏙️ Заказы по городам")

if 'Город' in df_filtered.columns:
    city_stats = df_filtered['Город'].value_counts().head(10)
    
    # Создаем таблицу для городов
    city_df = pd.DataFrame({
        'Город': city_stats.index,
        'Количество заказов': city_stats.values,
        '% от общего': (city_stats.values / len(df_filtered) * 100).round(1)
    })
    
    st.dataframe(city_df, use_container_width=True, hide_index=True)

# Таблица с заказами
st.markdown("---")
st.subheader("📋 Список заказов")

# Подготовка данных для отображения
column_names = {
    '№ заказа': '№ заказа',
    'Название магазина': 'Магазин',
    'Город': 'Город',
    'кол-во штук в заказе': 'Кол-во товаров',
    'Дата отгрузки план': 'План отгрузки',
    'Статус отображение': 'Статус'
}

# Создаем датафрейм для отображения
df_display = pd.DataFrame()
for orig_col, display_name in column_names.items():
    if orig_col in df_filtered.columns:
        df_display[display_name] = df_filtered[orig_col]

if 'Статус сборки' in df_filtered.columns:
    df_display['Статус сборки'] = df_filtered['Статус сборки']

# Отображаем таблицу
st.dataframe(df_display, use_container_width=True, height=400)

# Детальная статистика
st.markdown("---")
with st.expander("📊 Детальная статистика"):
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    
    with col_stat1:
        if 'Город' in df_filtered.columns:
            st.write("**🏙️ Топ городов:**")
            for city, count in df_filtered['Город'].value_counts().head(5).items():
                st.write(f"- {city}: {count} заказов")
    
    with col_stat2:
        if 'Статус отображение' in df_filtered.columns:
            st.write("**📊 Распределение по статусам:**")
            for status, count in df_filtered['Статус отображение'].value_counts().items():
                percentage = (count / len(df_filtered)) * 100
                st.write(f"- {status}: {count} ({percentage:.1f}%)")
    
    with col_stat3:
        if 'кол-во штук в заказе' in df_filtered.columns:
            st.write("**📦 Статистика по товарам:**")
            st.write(f"- Среднее: {df_filtered['кол-во штук в заказе'].mean():.0f} шт")
            st.write(f"- Медиана: {df_filtered['кол-во штук в заказе'].median():.0f} шт")
            st.write(f"- Максимум: {df_filtered['кол-во штук в заказе'].max():.0f} шт")
            st.write(f"- Минимум: {df_filtered['кол-во штук в заказе'].min():.0f} шт")

# Информация об обновлении
st.markdown("---")
st.caption(f"🔄 Данные обновлены: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
