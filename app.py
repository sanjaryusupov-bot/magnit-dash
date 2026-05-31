import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

ORDERS_URL = "https://docs.google.com/spreadsheets/d/12CxJMCBUHgkaj-_KbOs1aK7hx_jEYMyS3q4Hh0bHTGw/export?format=csv&gid=1369918403"

st.set_page_config(
    page_title="WMS Dashboard", 
    layout="wide",
    page_icon="📦"
)

# Кастомный CSS для красивого дизайна
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
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        transition: transform 0.3s;
    }
    .stat-card:hover {
        transform: translateY(-5px);
    }
    .status-badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
    }
    .delivery {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 14px;
        color: #666;
        margin-top: 5px;
    }
    .sla-good {
        background-color: #d4edda;
        color: #155724;
        padding: 5px 10px;
        border-radius: 10px;
        font-weight: bold;
    }
    .sla-bad {
        background-color: #f8d7da;
        color: #721c24;
        padding: 5px 10px;
        border-radius: 10px;
        font-weight: bold;
    }
    .sla-warning {
        background-color: #fff3cd;
        color: #856404;
        padding: 5px 10px;
        border-radius: 10px;
        font-weight: bold;
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

# Маппинг статусов
status_display = {
    "IN_DELIVERY": "🚚 Доставляется",
    "SORTED": "✅ Сортирован",
    "SORTING": "🔄 Сортируется",
    "PICKED": "📦 Подобран",
    "PICKING": "⏳ Подбирается",
    "IN_ASSEMBLY": "📍 В очереди",
}

# Обработка дат
if 'Дата отгрузки план' in df.columns:
    df['Дата отгрузки план'] = pd.to_datetime(df['Дата отгрузки план'], errors='coerce')
    df['План дата'] = df['Дата отгрузки план'].dt.date

# Определяем статус отгрузки на хаб
if 'Статус отгрузки на хаб' in df.columns:
    # Если статус "отгружен", то считаем, что заказ доставлен на следующий день
    df['Дата факт отгрузки'] = pd.NaT
    df.loc[df['Статус отгрузки на хаб'].str.contains('отгружен', case=False, na=False), 'Дата факт отгрузки'] = datetime.now().date() - timedelta(days=1)
    df['Статус доставки'] = df['Статус отгрузки на хаб'].apply(
        lambda x: '✅ Доставлен' if pd.notna(x) and 'отгружен' in str(x).lower() else '🔄 В процессе'
    )

# Применяем статусы WMS
if 'Статус WMS' in df.columns:
    df['Статус отображение'] = df['Статус WMS'].map(status_display).fillna(df['Статус WMS'])
    df = df[df['Статус отображение'].notna()]

# Конвертируем количество товаров
if 'кол-во штук в заказе' in df.columns:
    df['кол-во штук в заказе'] = pd.to_numeric(df['кол-во штук в заказе'], errors='coerce').fillna(0)

# Расчет SLA
def calculate_sla(row):
    if pd.notna(row['План дата']) and pd.notna(row['Дата факт отгрузки']):
        plan_date = pd.to_datetime(row['План дата'])
        fact_date = pd.to_datetime(row['Дата факт отгрузки'])
        days_diff = (fact_date - plan_date).days
        
        if days_diff <= 0:
            return "✅ В срок", days_diff, "sla-good"
        elif days_diff <= 3:
            return "⚠️ Просрочка до 3 дней", days_diff, "sla-warning"
        else:
            return "❌ Сильная просрочка", days_diff, "sla-bad"
    elif pd.notna(row['План дата']):
        today = datetime.now().date()
        days_to_plan = (pd.to_datetime(row['План дата']).date() - today).days
        if days_to_plan < 0:
            return "🔴 Просрочен", days_to_plan, "sla-bad"
        else:
            return "🟡 В работе", days_to_plan, "sla-warning"
    else:
        return "Нет данных", 0, ""

df['SLA статус'], df['SLA дни'], df['SLA класс'] = zip(*df.apply(calculate_sla, axis=1))

# Заголовок
st.markdown("""
<div class="main-header">
    <h1>📦 WMS Dashboard</h1>
    <p>Аналитика по заказам, SLA и статусам доставки</p>
</div>
""", unsafe_allow_html=True)

# Фильтры в боковой панели
with st.sidebar:
    st.markdown("## 🔍 Фильтры")
    
    if 'Название магазина' in df.columns:
        shops = ['Все магазины'] + sorted(df['Название магазина'].dropna().unique().tolist())
        selected_shop = st.selectbox("🏬 Магазин", shops)
        
        if selected_shop != 'Все магазины':
            df_filtered = df[df['Название магазина'] == selected_shop]
        else:
            df_filtered = df.copy()
    else:
        df_filtered = df.copy()
    
    if 'Город' in df_filtered.columns:
        cities = ['Все города'] + sorted(df_filtered['Город'].dropna().unique().tolist())
        selected_city = st.selectbox("🏙️ Город", cities)
        if selected_city != 'Все города':
            df_filtered = df_filtered[df_filtered['Город'] == selected_city]
    
    if 'Статус отображение' in df_filtered.columns:
        statuses = ['Все статусы'] + sorted(df_filtered['Статус отображение'].dropna().unique().tolist())
        selected_status = st.selectbox("📊 Статус WMS", statuses)
        if selected_status != 'Все статусы':
            df_filtered = df_filtered[df_filtered['Статус отображение'] == selected_status]

if len(df_filtered) == 0:
    st.warning("⚠️ Нет данных для отображения")
    st.stop()

# Статистика по статусам WMS
st.markdown("## 📊 Текущие статусы заказов")
col1, col2, col3, col4, col5, col6 = st.columns(6)

status_counts = df_filtered['Статус отображение'].value_counts()
status_icons = {
    "🚚 Доставляется": "🚚",
    "✅ Сортирован": "✅",
    "🔄 Сортируется": "🔄",
    "📦 Подобран": "📦",
    "⏳ Подбирается": "⏳",
    "📍 В очереди": "📍"
}

cols = [col1, col2, col3, col4, col5, col6]
for idx, (status, count) in enumerate(status_counts.items()):
    if idx < 6:
        icon = status_icons.get(status, "📦")
        with cols[idx]:
            st.markdown(f"""
            <div class="stat-card" style="text-align: center;">
                <div style="font-size: 48px;">{icon}</div>
                <div class="metric-value">{count}</div>
                <div class="metric-label">{status}</div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# Ключевые метрики
st.markdown("## 📈 Ключевые показатели")
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_orders = len(df_filtered)
    st.markdown(f"""
    <div class="stat-card">
        <div style="font-size: 24px;">📦</div>
        <div class="metric-value">{total_orders}</div>
        <div class="metric-label">Всего заказов</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    total_items = int(df_filtered['кол-во штук в заказе'].sum())
    st.markdown(f"""
    <div class="stat-card">
        <div style="font-size: 24px;">📦</div>
        <div class="metric-value">{total_items:,}</div>
        <div class="metric-label">Всего товаров</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    in_delivery = len(df_filtered[df_filtered['Статус отображение'] == "🚚 Доставляется"])
    st.markdown(f"""
    <div class="stat-card">
        <div style="font-size: 24px;">🚚</div>
        <div class="metric-value">{in_delivery}</div>
        <div class="metric-label">В доставке</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    on_time = len(df_filtered[df_filtered['SLA статус'] == "✅ В срок"])
    st.markdown(f"""
    <div class="stat-card">
        <div style="font-size: 24px;">✅</div>
        <div class="metric-value">{on_time}</div>
        <div class="metric-label">Выполнено в срок</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# SLA Аналитика
st.markdown("## 🎯 SLA Аналитика")

col_sla1, col_sla2 = st.columns(2)

with col_sla1:
    sla_counts = df_filtered['SLA статус'].value_counts()
    fig_sla = px.pie(values=sla_counts.values, names=sla_counts.index, 
                     title="Распределение по SLA",
                     color_discrete_sequence=['#28a745', '#ffc107', '#dc3545', '#17a2b8'])
    fig_sla.update_traces(textposition='inside', textinfo='percent+label')
    fig_sla.update_layout(height=400)
    st.plotly_chart(fig_sla, use_container_width=True)

with col_sla2:
    # SLA по магазинам
    if 'Название магазина' in df_filtered.columns:
        sla_by_shop = df_filtered.groupby('Название магазина')['SLA статус'].apply(
            lambda x: (x == "✅ В срок").sum() / len(x) * 100
        ).sort_values(ascending=False).head(10)
        
        fig_shop_sla = px.bar(x=sla_by_shop.values, y=sla_by_shop.index, 
                              orientation='h', title="Топ магазинов по SLA (%)",
                              color=sla_by_shop.values,
                              color_continuous_scale='RdYlGn')
        fig_shop_sla.update_layout(height=400, xaxis_title="SLA %")
        st.plotly_chart(fig_shop_sla, use_container_width=True)

st.markdown("---")

# Аналитика по городам и просрочкам
st.markdown("## 📍 География заказов")

col_geo1, col_geo2 = st.columns(2)

with col_geo1:
    if 'Город' in df_filtered.columns:
        city_stats = df_filtered['Город'].value_counts().head(10)
        fig_city = px.bar(x=city_stats.values, y=city_stats.index, 
                          orientation='h', title="Топ-10 городов по заказам",
                          color=city_stats.values,
                          color_continuous_scale='Blues')
        fig_city.update_layout(height=400)
        st.plotly_chart(fig_city, use_container_width=True)

with col_geo2:
    # Просрочки по городам
    overdue_by_city = df_filtered[df_filtered['SLA статус'].isin(["⚠️ Просрочка до 3 дней", "❌ Сильная просрочка"])]
    if len(overdue_by_city) > 0:
        city_overdue = overdue_by_city['Город'].value_counts().head(10)
        fig_overdue = px.bar(x=city_overdue.values, y=city_overdue.index,
                             orientation='h', title="Города с просрочками",
                             color=city_overdue.values,
                             color_continuous_scale='Reds')
        fig_overdue.update_layout(height=400)
        st.plotly_chart(fig_overdue, use_container_width=True)
    else:
        st.info("Нет просроченных заказов")

st.markdown("---")

# Таблица заказов с SLA
st.markdown("## 📋 Детальная таблица заказов")

# Подготовка данных для таблицы
df_table = df_filtered.copy()
df_table['Статус'] = df_table['Статус отображение']
df_table['SLA'] = df_table['SLA статус']
df_table['Отклонение'] = df_table['SLA дни'].apply(lambda x: f"{x} дн" if x != 0 else "0")

display_columns = ['№ заказа', 'Название магазина', 'Город', 'кол-во штук в заказе', 
                   'План дата', 'Дата факт отгрузки', 'Статус', 'SLA', 'Отклонение']

display_names = ['№ заказа', 'Магазин', 'Город', 'Товаров', 'План отгрузки', 
                 'Факт отгрузки', 'Статус WMS', 'SLA статус', 'Отклонение']

df_display = pd.DataFrame()
for col, name in zip(display_columns, display_names):
    if col in df_table.columns:
        df_display[name] = df_table[col]

# Форматирование дат
if 'План отгрузки' in df_display.columns:
    df_display['План отгрузки'] = pd.to_datetime(df_display['План отгрузки']).dt.strftime('%d.%m.%Y')
if 'Факт отгрузки' in df_display.columns:
    df_display['Факт отгрузки'] = pd.to_datetime(df_display['Факт отгрузки'], errors='coerce').dt.strftime('%d.%m.%Y')

st.dataframe(df_display, use_container_width=True, height=500)

# Дополнительная аналитика в экспандере
with st.expander("📊 Расширенная аналитика"):
    tab1, tab2, tab3 = st.tabs(["Аналитика по магазинам", "Динамика заказов", "Статистика просрочек"])
    
    with tab1:
        shop_analytics = df_filtered.groupby('Название магазина').agg({
            '№ заказа': 'count',
            'кол-во штук в заказе': 'sum',
            'SLA статус': lambda x: (x == "✅ В срок").sum() / len(x) * 100
        }).round(2)
        shop_analytics.columns = ['Заказов', 'Товаров', 'SLA %']
        shop_analytics = shop_analytics.sort_values('SLA %', ascending=False)
        st.dataframe(shop_analytics, use_container_width=True)
    
    with tab2:
        st.info("📈 Здесь будет динамика заказов по дням (требуется дополнительная настройка данных)")
    
    with tab3:
        overdue_orders = df_filtered[df_filtered['SLA статус'].isin(["⚠️ Просрочка до 3 дней", "❌ Сильная просрочка"])]
        if len(overdue_orders) > 0:
            st.warning(f"⚠️ Найдено {len(overdue_orders)} просроченных заказов")
            st.dataframe(overdue_orders[['№ заказа', 'Название магазина', 'Город', 'SLA статус', 'SLA дни']])
        else:
            st.success("✅ Нет просроченных заказов!")

# Информация об обновлении
st.markdown("---")
st.caption(f"🔄 Данные обновлены: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
