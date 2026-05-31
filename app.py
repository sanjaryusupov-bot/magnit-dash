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
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        transition: transform 0.3s;
    }
    .stat-card:hover {
        transform: translateY(-5px);
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
    # Создаем колонку с датой факт отгрузки как строку
    df['Дата факт отгрузки'] = None
    df['Статус доставки'] = '🔄 В процессе'
    
    for idx, row in df.iterrows():
        if pd.notna(row['Статус отгрузки на хаб']) and 'отгружен' in str(row['Статус отгрузки на хаб']).lower():
            df.at[idx, 'Дата факт отгрузки'] = (datetime.now() - timedelta(days=1)).date()
            df.at[idx, 'Статус доставки'] = '✅ Доставлен'
    
    # Конвертируем в datetime
    df['Дата факт отгрузки'] = pd.to_datetime(df['Дата факт отгрузки'], errors='coerce')

# Применяем статусы WMS
if 'Статус WMS' in df.columns:
    df['Статус отображение'] = df['Статус WMS'].map(status_display).fillna(df['Статус WMS'])
    df = df[df['Статус отображение'].notna()]

# Конвертируем количество товаров
if 'кол-во штук в заказе' in df.columns:
    df['кол-во штук в заказе'] = pd.to_numeric(df['кол-во штук в заказе'], errors='coerce').fillna(0)

# Расчет SLA
def calculate_sla(row):
    try:
        plan_date = row['План дата'] if pd.notna(row['План дата']) else None
        fact_date = row['Дата факт отгрузки'].date() if pd.notna(row['Дата факт отгрузки']) else None
        
        if plan_date and fact_date:
            days_diff = (fact_date - plan_date).days
            
            if days_diff <= 0:
                return "✅ В срок", days_diff
            elif days_diff <= 3:
                return "⚠️ Просрочка до 3 дней", days_diff
            else:
                return "❌ Сильная просрочка", days_diff
        elif plan_date:
            today = datetime.now().date()
            days_to_plan = (plan_date - today).days
            if days_to_plan < 0:
                return "🔴 Просрочен", days_to_plan
            else:
                return "🟡 В работе", days_to_plan
        else:
            return "Нет данных", 0
    except:
        return "Нет данных", 0

sla_results = df.apply(calculate_sla, axis=1, result_type='expand')
df['SLA статус'] = sla_results[0]
df['SLA дни'] = sla_results[1]

# Заголовок
st.markdown("""
<div class="main-header">
    <h1>📦 WMS Dashboard</h1>
    <p>Аналитика по заказам, SLA и статусам доставки</p>
</div>
""", unsafe_allow_html=True)

# Фильтры
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
    
    if len(df_filtered) > 0 and 'Статус отображение' in df_filtered.columns:
        statuses = ['Все статусы'] + sorted(df_filtered['Статус отображение'].dropna().unique().tolist())
        selected_status = st.selectbox("📊 Статус WMS", statuses)
        if selected_status != 'Все статусы':
            df_filtered = df_filtered[df_filtered['Статус отображение'] == selected_status]

if len(df_filtered) == 0:
    st.warning("⚠️ Нет данных для отображения")
    st.stop()

# Статистика по статусам
st.markdown("## 📊 Текущие статусы заказов")
status_counts = df_filtered['Статус отображение'].value_counts()

# Создаем колонки динамически
num_statuses = len(status_counts)
if num_statuses > 0:
    cols = st.columns(min(num_statuses, 6))
    for idx, (status, count) in enumerate(status_counts.items()):
        if idx < 6:
            with cols[idx]:
                st.markdown(f"""
                <div class="stat-card" style="text-align: center;">
                    <div class="metric-value">{count}</div>
                    <div class="metric-label">{status}</div>
                </div>
                """, unsafe_allow_html=True)

st.markdown("---")

# Ключевые метрики
st.markdown("## 📈 Ключевые показатели")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📦 Всего заказов", len(df_filtered))

with col2:
    total_items = int(df_filtered['кол-во штук в заказе'].sum())
    st.metric("📦 Всего товаров", f"{total_items:,}".replace(',', ' '))

with col3:
    in_delivery = len(df_filtered[df_filtered['Статус отображение'] == "🚚 Доставляется"])
    st.metric("🚚 В доставке", in_delivery)

with col4:
    on_time = len(df_filtered[df_filtered['SLA статус'] == "✅ В срок"])
    st.metric("✅ В срок", on_time)

st.markdown("---")

# SLA Аналитика
st.markdown("## 🎯 SLA Аналитика")

col_sla1, col_sla2 = st.columns(2)

with col_sla1:
    sla_counts = df_filtered['SLA статус'].value_counts()
    if len(sla_counts) > 0:
        fig_sla = px.pie(values=sla_counts.values, names=sla_counts.index, 
                         title="Распределение по SLA",
                         color_discrete_sequence=['#28a745', '#ffc107', '#dc3545', '#17a2b8'])
        fig_sla.update_traces(textposition='inside', textinfo='percent+label')
        fig_sla.update_layout(height=400)
        st.plotly_chart(fig_sla, use_container_width=True)

with col_sla2:
    if 'Название магазина' in df_filtered.columns and len(df_filtered['Название магазина'].unique()) > 0:
        sla_by_shop = df_filtered.groupby('Название магазина')['SLA статус'].apply(
            lambda x: (x == "✅ В срок").sum() / len(x) * 100 if len(x) > 0 else 0
        ).sort_values(ascending=False).head(10)
        
        if len(sla_by_shop) > 0:
            fig_shop_sla = px.bar(x=sla_by_shop.values, y=sla_by_shop.index, 
                                  orientation='h', title="Топ магазинов по SLA (%)",
                                  color=sla_by_shop.values,
                                  color_continuous_scale='RdYlGn')
            fig_shop_sla.update_layout(height=400, xaxis_title="SLA %")
            st.plotly_chart(fig_shop_sla, use_container_width=True)

st.markdown("---")

# География заказов
st.markdown("## 📍 География заказов")

col_geo1, col_geo2 = st.columns(2)

with col_geo1:
    if 'Город' in df_filtered.columns:
        city_stats = df_filtered['Город'].value_counts().head(10)
        if len(city_stats) > 0:
            fig_city = px.bar(x=city_stats.values, y=city_stats.index, 
                              orientation='h', title="Топ-10 городов по заказам",
                              color=city_stats.values,
                              color_continuous_scale='Blues')
            fig_city.update_layout(height=400)
            st.plotly_chart(fig_city, use_container_width=True)

with col_geo2:
    overdue_by_city = df_filtered[df_filtered['SLA статус'].isin(["⚠️ Просрочка до 3 дней", "❌ Сильная просрочка", "🔴 Просрочен"])]
    if len(overdue_by_city) > 0 and 'Город' in overdue_by_city.columns:
        city_overdue = overdue_by_city['Город'].value_counts().head(10)
        if len(city_overdue) > 0:
            fig_overdue = px.bar(x=city_overdue.values, y=city_overdue.index,
                                 orientation='h', title="Города с просрочками",
                                 color=city_overdue.values,
                                 color_continuous_scale='Reds')
            fig_overdue.update_layout(height=400)
            st.plotly_chart(fig_overdue, use_container_width=True)
        else:
            st.info("Нет просроченных заказов")
    else:
        st.info("Нет просроченных заказов")

st.markdown("---")

# Таблица заказов
st.markdown("## 📋 Детальная таблица заказов")

df_table = df_filtered.copy()
df_table['Статус'] = df_table['Статус отображение']
df_table['SLA'] = df_table['SLA статус']

# Выбираем колонки для отображения
display_cols = ['№ заказа', 'Название магазина', 'Город', 'кол-во штук в заказе', 
                'План дата', 'Статус', 'SLA', 'Статус доставки']

display_names = ['№ заказа', 'Магазин', 'Город', 'Товаров', 'План отгрузки', 
                 'Статус WMS', 'SLA', 'Доставка']

df_display = pd.DataFrame()
for col, name in zip(display_cols, display_names):
    if col in df_table.columns:
        df_display[name] = df_table[col]

if 'План отгрузки' in df_display.columns:
    df_display['План отгрузки'] = pd.to_datetime(df_display['План отгрузки'], errors='coerce').dt.strftime('%d.%m.%Y')

st.dataframe(df_display, use_container_width=True, height=400)

# Расширенная аналитика
with st.expander("📊 Расширенная аналитика"):
    if 'Название магазина' in df_filtered.columns:
        shop_analytics = df_filtered.groupby('Название магазина').agg({
            '№ заказа': 'count',
            'кол-во штук в заказе': 'sum',
            'SLA статус': lambda x: (x == "✅ В срок").sum() / len(x) * 100 if len(x) > 0 else 0
        }).round(2)
        shop_analytics.columns = ['Заказов', 'Товаров', 'SLA %']
        shop_analytics = shop_analytics.sort_values('SLA %', ascending=False)
        st.dataframe(shop_analytics, use_container_width=True)
    
    # Статистика просрочек
    overdue_orders = df_filtered[df_filtered['SLA статус'].isin(["⚠️ Просрочка до 3 дней", "❌ Сильная просрочка", "🔴 Просрочен"])]
    if len(overdue_orders) > 0:
        st.warning(f"⚠️ Найдено {len(overdue_orders)} просроченных заказов")
        overdue_display = overdue_orders[['№ заказа', 'Название магазина', 'Город', 'SLA статус', 'SLA дни']]
        st.dataframe(overdue_display, use_container_width=True)
    else:
        st.success("✅ Нет просроченных заказов!")

# Информация об обновлении
st.markdown("---")
st.caption(f"🔄 Данные обновлены: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} | Всего заказов: {len(df_filtered)}")
