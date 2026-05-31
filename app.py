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
    .status-badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
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

# Применяем статусы
if 'Статус WMS' in df.columns:
    df['Статус отображение'] = df['Статус WMS'].map(status_display).fillna(df['Статус WMS'])
    df = df[df['Статус отображение'].notna()]

# Конвертируем количество товаров
if 'кол-во штук в заказе' in df.columns:
    df['кол-во штук в заказе'] = pd.to_numeric(df['кол-во штук в заказе'], errors='coerce').fillna(0)

# Расчет SLA для магазинов (сравнение доставки)
if 'Статус отгрузки на хаб' in df.columns:
    df['Доставлен'] = df['Статус отгрузки на хаб'].apply(
        lambda x: '✅ Доставлен' if pd.notna(x) and 'отгружен' in str(x).lower() else '🔄 В процессе'
    )

# Заголовок
st.markdown("""
<div class="main-header">
    <h1>📦 WMS Dashboard</h1>
    <p>Детальная информация по статусам заказов | Данные с 25 мая 2026</p>
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

# ==================== СТАТИСТИКА ПО СТАТУСАМ ====================
st.markdown("## 📊 Статусы заказов")

status_counts = df_filtered['Статус отображение'].value_counts()

# Создаем колонки для статусов
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

# ==================== КЛЮЧЕВЫЕ МЕТРИКИ ====================
st.markdown("## 📈 Общая статистика")

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
    if 'Доставлен' in df_filtered.columns:
        delivered = len(df_filtered[df_filtered['Доставлен'] == "✅ Доставлен"])
        st.metric("✅ Доставлено", delivered)

st.markdown("---")

# ==================== СРАВНЕНИЕ МАГАЗИНОВ ПО ДОСТАВКЕ ====================
st.markdown("## 🏪 Сравнение магазинов по доставке")

if 'Название магазина' in df_filtered.columns and 'Доставлен' in df_filtered.columns:
    # Агрегируем данные по магазинам
    shop_comparison = df_filtered.groupby('Название магазина').agg({
        '№ заказа': 'count',
        'кол-во штук в заказе': 'sum',
        'Доставлен': lambda x: (x == "✅ Доставлен").sum(),
        'Статус отображение': lambda x: (x == "🚚 Доставляется").sum()
    }).round(0)
    
    shop_comparison.columns = ['Заказов', 'Товаров', 'Доставлено', 'В доставке']
    shop_comparison['Доставлено %'] = (shop_comparison['Доставлено'] / shop_comparison['Заказов'] * 100).round(1)
    shop_comparison['Осталось'] = shop_comparison['Заказов'] - shop_comparison['Доставлено']
    
    # Сортируем по доставке
    shop_comparison = shop_comparison.sort_values('Доставлено %', ascending=False)
    
    # График сравнения
    col_comp1, col_comp2 = st.columns(2)
    
    with col_comp1:
        fig_shop_delivery = px.bar(shop_comparison.head(15), 
                                    x='Доставлено %', 
                                    y=shop_comparison.head(15).index,
                                    orientation='h',
                                    title="Топ магазинов по доставке (%)",
                                    text='Доставлено %',
                                    color='Доставлено %',
                                    color_continuous_scale='RdYlGn',
                                    range_color=[0, 100])
        fig_shop_delivery.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_shop_delivery.update_layout(height=500, xaxis_title="Доставлено %", xaxis_range=[0, 100])
        st.plotly_chart(fig_shop_delivery, use_container_width=True)
    
    with col_comp2:
        # Сравнение товаров
        fig_items = px.bar(shop_comparison.head(15),
                           x='Товаров',
                           y=shop_comparison.head(15).index,
                           orientation='h',
                           title="Количество товаров по магазинам",
                           text='Товаров',
                           color='Товаров',
                           color_continuous_scale='Blues')
        fig_items.update_traces(texttemplate='%{text}', textposition='outside')
        fig_items.update_layout(height=500)
        st.plotly_chart(fig_items, use_container_width=True)
    
    # Таблица сравнения
    st.markdown("### 📊 Детальное сравнение магазинов")
    st.dataframe(shop_comparison, use_container_width=True)

st.markdown("---")

# ==================== ДИНАМИКА ПО НЕДЕЛЯМ ====================
st.markdown("## 📅 Динамика по неделям")

if 'План дата' in df_filtered.columns:
    df_filtered['Неделя'] = df_filtered['План дата'].dt.isocalendar().week
    df_filtered['Неделя строка'] = df_filtered['План дата'].dt.strftime('%d.%m') + ' (нед ' + df_filtered['Неделя'].astype(str) + ')'
    
    # Группируем по неделям
    weekly_data = df_filtered.groupby('Неделя строка').agg({
        '№ заказа': 'count',
        'кол-во штук в заказе': 'sum',
        'Статус отображение': lambda x: (x == "🚚 Доставляется").sum(),
    }).reset_index()
    
    weekly_data.columns = ['Неделя', 'Заказов', 'Товаров', 'В доставке']
    weekly_data = weekly_data.sort_values('Неделя')
    
    # График динамики
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Bar(name='Заказов', x=weekly_data['Неделя'], y=weekly_data['Заказов'], 
                                marker_color='#667eea'))
    fig_trend.add_trace(go.Scatter(name='Товаров', x=weekly_data['Неделя'], y=weekly_data['Товаров'],
                                    mode='lines+marker', line=dict(color='#764ba2', width=3),
                                    yaxis='y2'))
    
    fig_trend.update_layout(
        title="Динамика заказов и товаров по неделям",
        xaxis_title="Неделя",
        yaxis_title="Количество заказов",
        yaxis2=dict(title="Количество товаров", overlaying='y', side='right'),
        height=450,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_trend, use_container_width=True)
    
    # Таблица по неделям
    st.markdown("### 📊 Недельная статистика")
    st.dataframe(weekly_data, use_container_width=True, hide_index=True)

st.markdown("---")

# ==================== ДЕТАЛЬНАЯ ТАБЛИЦА ЗАКАЗОВ ====================
st.markdown("## 📋 Детальная информация по заказам")

# Подготовка данных для таблицы
df_table = df_filtered.copy()
df_table['План отгрузки'] = df_table['План дата'].dt.strftime('%d.%m.%Y')
df_table['Статус'] = df_table['Статус отображение']

# Выбираем колонки для отображения
display_cols = ['№ заказа', 'Название магазина', 'Город', 'кол-во штук в заказе', 
                'План отгрузки', 'Статус', 'Статус сборки', 'Статус отгрузки на хаб']

display_names = ['№ заказа', 'Магазин', 'Город', 'Кол-во товаров', 
                 'План отгрузки', 'Статус WMS', 'Статус сборки', 'Доставка на хаб']

df_display = pd.DataFrame()
for col, name in zip(display_cols, display_names):
    if col in df_table.columns:
        df_display[name] = df_table[col]

# Добавляем поиск по заказам
search = st.text_input("🔍 Поиск по номеру заказа", placeholder="Введите номер заказа...")
if search:
    df_display = df_display[df_display['№ заказа'].astype(str).str.contains(search, case=False)]

st.dataframe(df_display, use_container_width=True, height=500)

# ==================== СТАТИСТИКА ПО СТАТУСАМ СБОРКИ ====================
if 'Статус сборки' in df_filtered.columns:
    st.markdown("---")
    st.markdown("## 🔧 Статусы сборки")
    
    col_status1, col_status2 = st.columns(2)
    
    with col_status1:
        assembly_status = df_filtered['Статус сборки'].value_counts()
        if len(assembly_status) > 0:
            fig_assembly = px.pie(values=assembly_status.values, names=assembly_status.index,
                                   title="Распределение по статусам сборки",
                                   hole=0.3)
            fig_assembly.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_assembly, use_container_width=True)
    
    with col_status2:
        # Сборка по магазинам
        assembly_by_shop = df_filtered.groupby('Название магазина')['Статус сборки'].value_counts().unstack().fillna(0)
        if len(assembly_by_shop) > 0:
            st.dataframe(assembly_by_shop.head(15), use_container_width=True)

# ==================== ЭКСПОРТ ДАННЫХ ====================
with st.expander("📥 Экспорт данных"):
    col_export1, col_export2 = st.columns(2)
    
    with col_export1:
        # Экспорт текущего датафрейма
        csv_current = df_filtered[display_cols].to_csv(index=False)
        st.download_button(
            label="📥 Скачать текущие данные (CSV)",
            data=csv_current,
            file_name=f"wms_orders_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    
    with col_export2:
        if 'Название магазина' in df_filtered.columns and 'Доставлен' in df_filtered.columns:
            csv_shops = shop_comparison.to_csv()
            st.download_button(
                label="📥 Скачать статистику по магазинам (CSV)",
                data=csv_shops,
                file_name=f"wms_shops_stats_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
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
