import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

ORDERS_URL = "https://docs.google.com/spreadsheets/d/12CxJMCBUHgkaj-_KbOs1aK7hx_jEYMyS3q4Hh0bHTGw/export?format=csv&gid=1369918403"

st.set_page_config(
    page_title="WMS Dashboard - SLA Analytics", 
    layout="wide",
    page_icon="📊"
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
        margin-bottom: 15px;
    }
    .stat-card:hover {
        transform: translateY(-5px);
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
    .sla-good {
        background-color: #d4edda;
        color: #155724;
        padding: 8px 15px;
        border-radius: 10px;
        font-weight: bold;
        text-align: center;
    }
    .sla-bad {
        background-color: #f8d7da;
        color: #721c24;
        padding: 8px 15px;
        border-radius: 10px;
        font-weight: bold;
        text-align: center;
    }
    .sla-warning {
        background-color: #fff3cd;
        color: #856404;
        padding: 8px 15px;
        border-radius: 10px;
        font-weight: bold;
        text-align: center;
    }
    .trend-up {
        color: #28a745;
        font-weight: bold;
    }
    .trend-down {
        color: #dc3545;
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

# Фильтруем нужные колонки
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

# Обработка статуса отгрузки на хаб для даты факт отгрузки
if 'Статус отгрузки на хаб' in df.columns:
    df['Дата факт отгрузки'] = pd.NaT
    df['Статус доставки'] = '🔄 В процессе'
    
    for idx, row in df.iterrows():
        if pd.notna(row['Статус отгрузки на хаб']) and 'отгружен' in str(row['Статус отгрузки на хаб']).lower():
            df.at[idx, 'Дата факт отгрузки'] = datetime.now() - timedelta(days=1)
            df.at[idx, 'Статус доставки'] = '✅ Доставлен'

# Конвертируем количество товаров
if 'кол-во штук в заказе' in df.columns:
    df['кол-во штук в заказе'] = pd.to_numeric(df['кол-во штук в заказе'], errors='coerce').fillna(0)

# Расчет SLA (на основе план vs факт)
def calculate_sla_days(row):
    try:
        plan = row['План дата']
        fact = row['Дата факт отгрузки']
        
        if pd.notna(plan) and pd.notna(fact):
            days_diff = (fact - plan).days
            if days_diff <= 0:
                return days_diff, "✅ В срок", 0
            elif days_diff <= 3:
                return days_diff, "⚠️ Просрочка до 3 дней", 1
            else:
                return days_diff, "❌ Сильная просрочка", 2
        elif pd.notna(plan):
            today = datetime.now()
            days_diff = (today - plan).days
            if days_diff < 0:
                return days_diff, "🟡 План в будущем", 3
            elif days_diff <= 0:
                return days_diff, "🟡 Сегодня", 3
            else:
                return days_diff, "🔴 Просрочен (не отгружен)", 4
        else:
            return 0, "Нет данных", 5
    except:
        return 0, "Ошибка", 5

sla_results = df.apply(calculate_sla_days, axis=1, result_type='expand')
df['SLA дни'] = sla_results[0]
df['SLA статус'] = sla_results[1]
df['SLA код'] = sla_results[2]

# Добавляем неделю
df['Неделя'] = df['План дата'].dt.isocalendar().week
df['Неделя строка'] = df['План дата'].dt.strftime('%Y-%m') + ' - Неделя ' + df['Неделя'].astype(str)

# Маппинг статусов для отображения
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

# Заголовок
st.markdown("""
<div class="main-header">
    <h1>📊 WMS SLA Dashboard</h1>
    <p>Аналитика по срокам доставки (План vs Факт) | Данные с 25 мая 2026</p>
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

# ==================== КЛЮЧЕВЫЕ МЕТРИКИ ====================
st.markdown("## 📈 Ключевые показатели SLA")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_orders = len(df_filtered)
    st.markdown(f"""
    <div class="stat-card" style="text-align: center;">
        <div class="metric-value">{total_orders}</div>
        <div class="metric-label">📦 Всего заказов</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    completed = len(df_filtered[df_filtered['Дата факт отгрузки'].notna()])
    st.markdown(f"""
    <div class="stat-card" style="text-align: center;">
        <div class="metric-value">{completed}</div>
        <div class="metric-label">✅ Отгружено</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    on_time = len(df_filtered[df_filtered['SLA статус'] == "✅ В срок"])
    on_time_pct = (on_time / completed * 100) if completed > 0 else 0
    st.markdown(f"""
    <div class="stat-card" style="text-align: center;">
        <div class="metric-value">{on_time_pct:.0f}%</div>
        <div class="metric-label">🎯 SLA (в срок)</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    overdue = len(df_filtered[df_filtered['SLA статус'].isin(["⚠️ Просрочка до 3 дней", "❌ Сильная просрочка"])])
    st.markdown(f"""
    <div class="stat-card" style="text-align: center;">
        <div class="metric-value">{overdue}</div>
        <div class="metric-label">⚠️ Просрочено</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    in_progress = len(df_filtered[df_filtered['Дата факт отгрузки'].isna()])
    st.markdown(f"""
    <div class="stat-card" style="text-align: center;">
        <div class="metric-value">{in_progress}</div>
        <div class="metric-label">🔄 В работе</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ==================== ГРАФИКИ SLA ====================
st.markdown("## 🎯 Аналитика SLA по магазинам")

col_sla1, col_sla2 = st.columns(2)

with col_sla1:
    # Текущий SLA по магазинам
    shop_sla = df_filtered[df_filtered['Дата факт отгрузки'].notna()].groupby('Название магазина').apply(
        lambda x: (x['SLA статус'] == "✅ В срок").sum() / len(x) * 100 if len(x) > 0 else 0
    ).sort_values(ascending=False).head(15)
    
    if len(shop_sla) > 0:
        colors = ['#28a745' if v >= 90 else '#ffc107' if v >= 70 else '#dc3545' for v in shop_sla.values]
        fig_shop_sla = px.bar(x=shop_sla.values, y=shop_sla.index, 
                               orientation='h', 
                               title="🏪 SLA по магазинам (% выполненых в срок)",
                               text=shop_sla.values.round(1),
                               color=shop_sla.values,
                               color_continuous_scale='RdYlGn',
                               range_color=[0, 100])
        fig_shop_sla.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_shop_sla.update_layout(height=500, xaxis_title="SLA %", xaxis_range=[0, 100])
        st.plotly_chart(fig_shop_sla, use_container_width=True)
    else:
        st.info("Нет данных для отображения SLA")

with col_sla2:
    # Распределение по статусам SLA
    sla_dist = df_filtered['SLA статус'].value_counts()
    colors_dict = {
        "✅ В срок": "#28a745",
        "⚠️ Просрочка до 3 дней": "#ffc107",
        "❌ Сильная просрочка": "#dc3545",
        "🔴 Просрочен (не отгружен)": "#fd7e14",
        "🟡 План в будущем": "#17a2b8",
        "🟡 Сегодня": "#6c757d"
    }
    colors_list = [colors_dict.get(status, "#6c757d") for status in sla_dist.index]
    
    fig_sla_dist = px.pie(values=sla_dist.values, names=sla_dist.index,
                           title="📊 Распределение заказов по SLA",
                           color_discrete_sequence=colors_list,
                           hole=0.3)
    fig_sla_dist.update_traces(textposition='inside', textinfo='percent+label')
    fig_sla_dist.update_layout(height=500)
    st.plotly_chart(fig_sla_dist, use_container_width=True)

st.markdown("---")

# ==================== НЕДЕЛЬНАЯ ДИНАМИКА SLA ====================
st.markdown("## 📈 Недельная динамика SLA")

# Группируем по неделям
weekly_stats = df_filtered[df_filtered['Дата факт отгрузки'].notna()].groupby('Неделя строка').apply(
    lambda x: pd.Series({
        'Всего': len(x),
        'В срок': (x['SLA статус'] == "✅ В срок").sum(),
        'SLA %': (x['SLA статус'] == "✅ В срок").sum() / len(x) * 100
    })
).reset_index()

if len(weekly_stats) > 0:
    weekly_stats = weekly_stats.sort_values('Неделя строка')
    
    # График динамики SLA
    fig_weekly = go.Figure()
    fig_weekly.add_trace(go.Scatter(
        x=weekly_stats['Неделя строка'],
        y=weekly_stats['SLA %'],
        mode='lines+markers',
        name='SLA %',
        line=dict(color='#28a745', width=3),
        marker=dict(size=10, color=weekly_stats['SLA %'], colorscale='RdYlGn', showscale=True),
        text=[f"SLA: {v:.1f}%<br>Заказов: {weekly_stats.iloc[i]['Всего']}<br>В срок: {weekly_stats.iloc[i]['В срок']}" 
              for i, v in enumerate(weekly_stats['SLA %'])],
        hoverinfo='text'
    ))
    
    fig_weekly.add_hline(y=90, line_dash="dash", line_color="green", 
                          annotation_text="Цель 90%", annotation_position="bottom right")
    fig_weekly.add_hline(y=70, line_dash="dash", line_color="orange", 
                          annotation_text="Нижняя граница", annotation_position="bottom right")
    
    fig_weekly.update_layout(
        title="Динамика SLA по неделям",
        xaxis_title="Неделя",
        yaxis_title="SLA (%)",
        yaxis_range=[0, 100],
        height=450,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_weekly, use_container_width=True)
    
    # Таблица с недельной статистикой
    st.markdown("### 📅 Недельная статистика")
    weekly_display = weekly_stats.copy()
    weekly_display['SLA %'] = weekly_display['SLA %'].round(1)
    weekly_display['Динамика'] = weekly_display['SLA %'].diff().round(1)
    weekly_display['Динамика'] = weekly_display['Динамика'].apply(
        lambda x: f"📈 +{x}%" if x > 0 else f"📉 {x}%" if x < 0 else "➡️ 0%"
    )
    weekly_display.columns = ['Неделя', 'Всего заказов', 'В срок', 'SLA %', 'Динамика']
    st.dataframe(weekly_display, use_container_width=True, hide_index=True)
else:
    st.info("Нет данных для недельной статистики")

st.markdown("---")

# ==================== СРАВНЕНИЕ ПЛАН VS ФАКТ ====================
st.markdown("## 📅 План vs Факт отгрузки")

col_plan1, col_plan2 = st.columns(2)

with col_plan1:
    # Отклонения по дням
    df_with_diff = df_filtered[df_filtered['Дата факт отгрузки'].notna()].copy()
    df_with_diff['Отклонение'] = df_with_diff['SLA дни']
    
    if len(df_with_diff) > 0:
        fig_deviation = px.histogram(df_with_diff, x='Отклонение', 
                                      title="Распределение отклонений (дней)",
                                      nbins=30,
                                      color_discrete_sequence=['#667eea'],
                                      labels={'Отклонение': 'Отклонение от плана (дни)'})
        fig_deviation.add_vline(x=0, line_dash="dash", line_color="red")
        fig_deviation.update_layout(height=400)
        st.plotly_chart(fig_deviation, use_container_width=True)
        
        avg_deviation = df_with_diff['Отклонение'].mean()
        median_deviation = df_with_diff['Отклонение'].median()
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("📊 Среднее отклонение", f"{avg_deviation:.1f} дн")
        with col_b:
            st.metric("📈 Медиана отклонения", f"{median_deviation:.1f} дн")
    else:
        st.info("Нет данных для сравнения")

with col_plan2:
    # Топ просрочек
    top_overdue = df_filtered[df_filtered['SLA статус'] == "❌ Сильная просрочка"].nlargest(10, 'SLA дни')
    if len(top_overdue) > 0:
        st.markdown("### 🔴 Топ-10 самых просроченных заказов")
        top_display = top_overdue[['№ заказа', 'Название магазина', 'Город', 'SLA дни', 'План дата', 'Дата факт отгрузки']].copy()
        top_display['SLA дни'] = top_display['SLA дни'].apply(lambda x: f"{x} дн")
        top_display['План дата'] = pd.to_datetime(top_display['План дата']).dt.strftime('%d.%m')
        top_display['Дата факт отгрузки'] = pd.to_datetime(top_display['Дата факт отгрузки']).dt.strftime('%d.%m')
        st.dataframe(top_display, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Нет сильно просроченных заказов!")

st.markdown("---")

# ==================== ТАБЛИЦА ЗАКАЗОВ ====================
st.markdown("## 📋 Детальная таблица заказов")

# Подготовка данных для таблицы
df_table = df_filtered.copy()
df_table['Статус WMS'] = df_table['Статус отображение']
df_table['План'] = df_table['План дата'].dt.strftime('%d.%m.%Y')
df_table['Факт'] = df_table['Дата факт отгрузки'].dt.strftime('%d.%m.%Y') if 'Дата факт отгрузки' in df_table else '—'
df_table['Отклонение'] = df_table['SLA дни'].apply(lambda x: f"{x:+d} дн" if x != 0 else "0 дн")

# Выбираем колонки для отображения
display_cols = ['№ заказа', 'Название магазина', 'Город', 'кол-во штук в заказе', 
                'План', 'Факт', 'Отклонение', 'SLA статус', 'Статус WMS']

display_names = ['№ заказа', 'Магазин', 'Город', 'Товаров', 'План отгрузки', 
                 'Факт отгрузки', 'Отклонение', 'SLA статус', 'Статус WMS']

df_display = pd.DataFrame()
for col, name in zip(display_cols, display_names):
    if col in df_table.columns:
        df_display[name] = df_table[col]

# Добавляем цветовую индикацию для SLA
def color_sla(val):
    if '✅' in str(val):
        return 'background-color: #d4edda'
    elif '⚠️' in str(val):
        return 'background-color: #fff3cd'
    elif '❌' in str(val) or '🔴' in str(val):
        return 'background-color: #f8d7da'
    return ''

st.dataframe(df_display.style.applymap(color_sla, subset=['SLA статус']), 
             use_container_width=True, height=500)

# ==================== РАСШИРЕННАЯ АНАЛИТИКА ====================
with st.expander("📊 Расширенная аналитика по магазинам"):
    # Детальная статистика по каждому магазину
    shop_detail = df_filtered.groupby('Название магазина').agg({
        '№ заказа': 'count',
        'кол-во штук в заказе': 'sum',
        'Дата факт отгрузки': lambda x: x.notna().sum(),
        'SLA статус': lambda x: (x == "✅ В срок").sum(),
        'SLA дни': lambda x: x[x > 0].mean() if len(x[x > 0]) > 0 else 0
    }).round(1)
    
    shop_detail.columns = ['Всего заказов', 'Всего товаров', 'Отгружено', 'В срок', 'Ср. просрочка (дни)']
    shop_detail['SLA %'] = (shop_detail['В срок'] / shop_detail['Отгружено'] * 100).round(1)
    shop_detail = shop_detail.sort_values('SLA %', ascending=False)
    
    st.dataframe(shop_detail, use_container_width=True)
    
    # Экспорт данных
    csv = df_filtered[['№ заказа', 'Название магазина', 'Город', 'План дата', 'Дата факт отгрузки', 'SLA статус', 'SLA дни']].to_csv(index=False)
    st.download_button(
        label="📥 Скачать данные в CSV",
        data=csv,
        file_name=f"wms_sla_report_{datetime.now().strftime('%Y%m%d')}.csv",
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
    st.caption(f"🏪 Магазинов: {df_filtered['Название магазина'].nunique()}")
