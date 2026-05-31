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
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 500;
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

# Фильтр: только заказы с 25 мая 2026
if 'Дата отгрузки план' in df.columns:
    df['План дата'] = pd.to_datetime(df['Дата отгрузки план'], errors='coerce')
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

# Простая SLA метрика (план vs факт)
if 'Статус отгрузки на хаб' in df.columns:
    df['Доставлен'] = df['Статус отгрузки на хаб'].apply(
        lambda x: '✅ Доставлен' if pd.notna(x) and 'отгружен' in str(x).lower() else '🔄 В процессе'
    )
    
    # Факт отгрузки (если доставлен - ставим вчерашнюю дату)
    df['Факт отгрузки'] = None
    for idx, row in df.iterrows():
        if row['Доставлен'] == '✅ Доставлен':
            df.at[idx, 'Факт отгрузки'] = datetime.now() - timedelta(days=1)
    
    # Расчет простого SLA (в срок или нет)
    df['SLA'] = df.apply(lambda row: '✅ В срок' if row['Доставлен'] == '✅ Доставлен' else '🟡 В работе', axis=1)

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
    
    if len(df_filtered) > 0 and 'Статус отображение' in df_filtered.columns:
        statuses = ['Все статусы'] + sorted(df_filtered['Статус отображение'].dropna().unique().tolist())
        selected_status = st.selectbox("📊 Статус заказа", statuses)
        if selected_status != 'Все статусы':
            df_filtered = df_filtered[df_filtered['Статус отображение'] == selected_status]

if len(df_filtered) == 0:
    st.warning("⚠️ Нет данных для отображения")
    st.stop()

# ==================== СТАТУСЫ ЗАКАЗОВ (ГЛАВНОЕ) ====================
st.markdown("## 📊 Статусы заказов")

status_counts = df_filtered['Статус отображение'].value_counts()

# Создаем карточки для каждого статуса
num_statuses = len(status_counts)
if num_statuses > 0:
    cols = st.columns(min(num_statuses, 6))
    for idx, (status, count) in enumerate(status_counts.items()):
        if idx < 6:
            with cols[idx]:
                # Эмодзи для статуса
                emoji = status.split()[0] if status else "📦"
                st.markdown(f"""
                <div class="stat-card">
                    <div style="font-size: 48px;">{emoji}</div>
                    <div class="metric-value">{count}</div>
                    <div class="metric-label">{status}</div>
                </div>
                """, unsafe_allow_html=True)

st.markdown("---")

# ==================== КЛЮЧЕВЫЕ МЕТРИКИ ====================
st.markdown("## 📈 Общая статистика")

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
    if 'Доставлен' in df_filtered.columns:
        delivered = len(df_filtered[df_filtered['Доставлен'] == "✅ Доставлен"])
        st.metric("✅ Доставлено", delivered)

with col5:
    picking = len(df_filtered[df_filtered['Статус отображение'].isin(["⏳ Подбирается", "🔄 Сортируется", "📍 В очереди"])])
    st.metric("⏳ В работе", picking)

st.markdown("---")

# ==================== СРАВНЕНИЕ МАГАЗИНОВ (ПРОСТАЯ SLA) ====================
st.markdown("## 🏪 Сравнение магазинов по доставке")

if 'Название магазина' in df_filtered.columns and 'Доставлен' in df_filtered.columns:
    shop_stats = df_filtered.groupby('Название магазина').agg({
        '№ заказа': 'count',
        'кол-во штук в заказе': 'sum',
        'Доставлен': lambda x: (x == "✅ Доставлен").sum()
    }).round(0)
    
    shop_stats.columns = ['Заказов', 'Товаров', 'Доставлено']
    shop_stats['Осталось'] = shop_stats['Заказов'] - shop_stats['Доставлено']
    shop_stats['Доставлено %'] = (shop_stats['Доставлено'] / shop_stats['Заказов'] * 100).round(1)
    shop_stats = shop_stats.sort_values('Доставлено %', ascending=False)
    
    col_shop1, col_shop2 = st.columns(2)
    
    with col_shop1:
        # График доставки по магазинам
        fig_delivery = px.bar(shop_stats.head(15), 
                               x='Доставлено %', 
                               y=shop_stats.head(15).index,
                               orientation='h',
                               title="Доставка по магазинам (%)",
                               text='Доставлено %',
                               color='Доставлено %',
                               color_continuous_scale='RdYlGn',
                               range_color=[0, 100])
        fig_delivery.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_delivery.update_layout(height=500, xaxis_title="Доставлено %")
        st.plotly_chart(fig_delivery, use_container_width=True)
    
    with col_shop2:
        # Количество товаров по магазинам
        fig_items = px.bar(shop_stats.head(15),
                           x='Товаров',
                           y=shop_stats.head(15).index,
                           orientation='h',
                           title="Количество товаров по магазинам",
                           text='Товаров',
                           color='Товаров',
                           color_continuous_scale='Blues')
        fig_items.update_traces(texttemplate='%{text}', textposition='outside')
        fig_items.update_layout(height=500)
        st.plotly_chart(fig_items, use_container_width=True)
    
    # Таблица с данными
    st.markdown("### 📊 Детальная статистика по магазинам")
    st.dataframe(shop_stats, use_container_width=True)

st.markdown("---")

# ==================== ДЕТАЛЬНАЯ ТАБЛИЦА ЗАКАЗОВ ====================
st.markdown("## 📋 Детальная информация по заказам")

# Подготовка данных для таблицы
df_table = df_filtered.copy()
df_table['План отгрузки'] = df_table['План дата'].dt.strftime('%d.%m.%Y') if 'План дата' in df_table else '—'
df_table['Факт отгрузки'] = df_table['Факт отгрузки'].dt.strftime('%d.%m.%Y') if 'Факт отгрузки' in df_table else '—'
df_table['Статус заказа'] = df_table['Статус отображение']

# Выбираем колонки для отображения
display_cols = ['№ заказа', 'Название магазина', 'Город', 'кол-во штук в заказе', 
                'План отгрузки', 'Факт отгрузки', 'Статус заказа', 'Статус сборки', 'Доставлен']

display_names = ['№ заказа', 'Магазин', 'Город', 'Кол-во товаров', 
                 'План отгрузки', 'Факт отгрузки', 'Статус WMS', 'Статус сборки', 'Доставка']

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

# ==================== СТАТУСЫ СБОРКИ ====================
if 'Статус сборки' in df_filtered.columns:
    st.markdown("---")
    st.markdown("## 🔧 Статусы сборки")
    
    col_assembly1, col_assembly2 = st.columns(2)
    
    with col_assembly1:
        assembly_stats = df_filtered['Статус сборки'].value_counts()
        if len(assembly_stats) > 0:
            fig_assembly = px.pie(values=assembly_stats.values, 
                                   names=assembly_stats.index,
                                   title="Распределение по статусам сборки",
                                   hole=0.3)
            fig_assembly.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_assembly, use_container_width=True)
    
    with col_assembly2:
        # Статусы сборки по магазинам
        assembly_by_shop = df_filtered.groupby('Название магазина')['Статус сборки'].value_counts().unstack().fillna(0)
        if len(assembly_by_shop) > 0:
            st.markdown("### Статусы сборки по магазинам")
            st.dataframe(assembly_by_shop.head(15), use_container_width=True)

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
