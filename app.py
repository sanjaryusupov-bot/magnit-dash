import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

ORDERS_URL = "https://docs.google.com/spreadsheets/d/12CxJMCBUHgkaj-_KbOs1aK7hx_jEYMyS3q4Hh0bHTGw/export?format=csv&gid=1369918403"

st.set_page_config(
    page_title="WMS Dashboard", 
    layout="wide",
    page_icon="📦"
)

# Кастомный CSS для красивого оформления
st.markdown("""
    <style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 14px;
        color: #666;
    }
    .status-card {
        padding: 10px;
        border-radius: 8px;
        margin: 5px 0;
        background-color: white;
        border-left: 4px solid;
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

# Маппинг статусов для красивого отображения
status_display = {
    "IN_DELIVERY": "🚚 Доставляется",
    "SORTED": "✅ Сортирован",
    "SORTING": "🔄 Сортируется",
    "PICKED": "📦 Подобран",
    "PICKING": "⏳ Подбирается",
    "IN_ASSEMBLY": "📍 В очереди",
    "COMPLETED": "✨ Завершен",
    "CANCELLED": "❌ Отменен",
    "ON_HOLD": "⏸ На удержании"
}

# Преобразуем статусы
if 'Статус WMS' in df.columns:
    df['Статус отображение'] = df['Статус WMS'].map(status_display).fillna(df['Статус WMS'])

# Заголовок
st.title("📦 WMS Dashboard")
st.markdown("---")

# Фильтры в боковой панели
with st.sidebar:
    st.header("🔍 Фильтры")
    
    # Фильтр по магазинам
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
    
    # Фильтр по городу
    if 'Город' in df.columns:
        cities = ['Все города'] + sorted(df_filtered['Город'].dropna().unique().tolist())
        selected_city = st.selectbox("🏙️ Город", cities)
        
        if selected_city != 'Все города':
            df_filtered = df_filtered[df_filtered['Город'] == selected_city]
    
    # Фильтр по статусу
    if 'Статус отображение' in df_filtered.columns:
        statuses = ['Все статусы'] + sorted(df_filtered['Статус отображение'].dropna().unique().tolist())
        selected_status = st.selectbox("📊 Статус", statuses)
        
        if selected_status != 'Все статусы':
            df_filtered = df_filtered[df_filtered['Статус отображение'] == selected_status]

# Основные метрики
st.subheader("📈 Ключевые показатели")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📦 Всего заказов", len(df_filtered))

with col2:
    if 'кол-во штук в заказе' in df_filtered.columns:
        total_items = df_filtered['кол-во штук в заказе'].sum()
        st.metric("📦 Всего товаров", f"{total_items:,}")

with col3:
    if 'Статус отображение' in df_filtered.columns:
        delivered = len(df_filtered[df_filtered['Статус отображение'].str.contains("Доставляется|Завершен", na=False)])
        st.metric("🚚 В доставке/Завершено", delivered)

with col4:
    if 'Город' in df_filtered.columns:
        cities_count = df_filtered['Город'].nunique()
        st.metric("🏙️ Городов", cities_count)

st.markdown("---")

# Графики в два столбца
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("📊 Статусы заказов")
    if 'Статус отображение' in df_filtered.columns:
        status_counts = df_filtered['Статус отображение'].value_counts().reset_index()
        status_counts.columns = ['Статус', 'Количество']
        
        fig = px.pie(status_counts, values='Количество', names='Статус', 
                     title='Распределение заказов по статусам',
                     color_discrete_sequence=px.colors.qualitative.Set3,
                     hole=0.3)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

with col_chart2:
    st.subheader("🏙️ Заказы по городам")
    if 'Город' in df_filtered.columns:
        city_counts = df_filtered['Город'].value_counts().head(10).reset_index()
        city_counts.columns = ['Город', 'Количество']
        
        fig = px.bar(city_counts, x='Город', y='Количество', 
                     title='Топ-10 городов по количеству заказов',
                     color='Количество',
                     color_continuous_scale='Blues')
        fig.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

# Таблица с заказами
st.markdown("---")
st.subheader("📋 Список заказов")

# Подготовка данных для отображения
display_columns = []
column_names = {
    '№ заказа': '№ заказа',
    'Название магазина': 'Магазин',
    'Город': 'Город',
    'кол-во штук в заказе': 'Кол-во товаров',
    'Дата отгрузки план': 'План отгрузки',
    'Статус отображение': 'Статус'
}

for col, display_name in column_names.items():
    if col in df_filtered.columns:
        display_columns.append(display_name)

# Создаем датафрейм для отображения
df_display = pd.DataFrame()
for orig_col, display_name in column_names.items():
    if orig_col in df_filtered.columns:
        df_display[display_name] = df_filtered[orig_col]

# Добавляем статус сборки если есть
if 'Статус сборки' in df_filtered.columns:
    df_display['Статус сборки'] = df_filtered['Статус сборки']

# Форматируем даты
if 'План отгрузки' in df_display.columns:
    df_display['План отгрузки'] = pd.to_datetime(df_display['План отгрузки'], errors='coerce').dt.strftime('%d.%m.%Y')

# Отображаем таблицу с кастомным форматированием
st.dataframe(
    df_display,
    use_container_width=True,
    height=400,
    column_config={
        "Статус": st.column_config.TextColumn(
            "Статус",
            help="Текущий статус заказа",
        ),
        "Кол-во товаров": st.column_config.NumberColumn(
            "Кол-во товаров",
            format="%d шт",
        ),
    }
)

# Дополнительная статистика
st.markdown("---")
with st.expander("📊 Детальная статистика"):
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    
    with col_stat1:
        if 'Город' in df_filtered.columns:
            st.write("**Заказы по городам:**")
            city_stats = df_filtered['Город'].value_counts()
            for city, count in city_stats.head(5).items():
                st.write(f"- {city}: {count} заказов")
    
    with col_stat2:
        if 'Статус отображение' in df_filtered.columns:
            st.write("**Статусы заказов:**")
            status_stats = df_filtered['Статус отображение'].value_counts()
            for status, count in status_stats.items():
                st.write(f"- {status}: {count} заказов")
    
    with col_stat3:
        if 'кол-во штук в заказе' in df_filtered.columns:
            st.write("**Статистика по товарам:**")
            st.write(f"- Среднее: {df_filtered['кол-во штук в заказе'].mean():.0f} шт")
            st.write(f"- Максимум: {df_filtered['кол-во штук в заказе'].max():.0f} шт")
            st.write(f"- Минимум: {df_filtered['кол-во штук в заказе'].min():.0f} шт")

# Информация об обновлении
st.markdown("---")
st.caption(f"🔄 Данные обновлены: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
