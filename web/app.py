import os
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="Currency Bot Dashboard", layout="wide")
st.title("📊 Панель управления Currency Bot")
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
try:
    API_BASE_URL = st.secrets["API_BASE_URL"]
except Exception:
    API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")


st.header("🧪 Тестовый парсер валют")
col1, col2 = st.columns([3, 1])

with col1:
    test_text = st.text_area(
        "Введите текст для анализа:", 
        "Купил пиццу за 25 баксов и кофе за 300 рублей, ноутбук за 666 долларов",
        height=100,
        key="test_input"
    )

with col2:
    st.write("") 
    st.write("")
    if st.button("🔍 Распознать валюты", type="primary", use_container_width=True):
        with st.spinner('Анализирую текст...'):
            try:
                resp = requests.post(
                    f'{API_BASE_URL}/detect-currencies', 
                    json={'text': test_text}, 
                    timeout=10
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data['items']:
                        st.success(f"✅ Найдено {len(data['items'])} валютных упоминаний")
                        for item in data['items']:
                            with st.expander(f"{item['source_amount']} {item['source_currency']} (\"{item['match_text']}\")"):
                                for conv in item['conversions']:
                                    st.info(
                                        f"**{conv['converted_amount']:.2f} {conv['quote_currency']}** "
                                        f"(курс: {conv['rate']:.4f})"
                                    )
                    else:
                        st.warning("🔍 В тексте не обнаружено упоминаний валют.")
                else:
                    st.error("❌ Ошибка сервера при анализе текста.")
            except requests.ConnectionError:
                st.error("🚫 Не удалось подключиться к серверу анализа.")


st.header("📜 История конвертаций")
st.markdown("---")


col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    limit = st.number_input("Количество записей", min_value=1, max_value=100, value=10, step=5)
with col2:
    auto_refresh = st.checkbox("Автообновление", value=True)
    if auto_refresh:
        refresh_interval = st.number_input("Интервал (сек)", min_value=5, max_value=60, value=10, step=5)
with col3:
    if st.button("🔄 Обновить сейчас", type="secondary"):
        st.rerun()


@st.cache_data(ttl=10) 
def load_history(limit: int):
    try:
        response = requests.get(f'{API_BASE_URL}/history?limit={limit}', timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.ConnectionError:
        return None


history_data = load_history(limit)

if history_data and history_data.get('conversions'):
    conversions = history_data['conversions']
    

    df = pd.DataFrame(conversions)
    
    
    df.insert(0, '№', range(1, len(df) + 1))
    
    
    def get_usd_amount(row):
        if row['quote_currency'] == 'USD':
            return row['converted_amount']
        
        return None
    
    df['Доллары (USD)'] = df.apply(
        lambda row: row['converted_amount'] if row['quote_currency'] == 'USD' else None, 
        axis=1
    )
    

    df['Время'] = pd.to_datetime(df['created_at']).dt.strftime('%H:%M:%S')
    df['Дата'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d')
    

    display_df = df[[
        '№', 
        'amount', 
        'base_currency',
        'Доллары (USD)',
        'rate',
        'Дата',
        'Время'
    ]]
    

    display_df = display_df.rename(columns={
        'amount': 'Сумма',
        'base_currency': 'Исходная валюта',
        'rate': 'Курс'
    })
    

    display_df['Сумма'] = display_df['Сумма'].apply(lambda x: f"{x:,.2f}")
    display_df['Доллары (USD)'] = display_df['Доллары (USD)'].apply(
        lambda x: f"{x:,.2f}" if x is not None else "—"
    )
    display_df['Курс'] = display_df['Курс'].apply(lambda x: f"{x:.4f}")
    
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "№": st.column_config.NumberColumn(width="small"),
            "Сумма": st.column_config.TextColumn(width="medium"),
            "Исходная валюта": st.column_config.TextColumn(width="small"),
            "Доллары (USD)": st.column_config.TextColumn(width="medium"),
            "Курс": st.column_config.TextColumn(width="medium"),
            "Дата": st.column_config.TextColumn(width="small"),
            "Время": st.column_config.TextColumn(width="small"),
        }
    )
    

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Всего операций", len(conversions))
    with col2:
        usd_conversions = df[df['quote_currency'] == 'USD'].shape[0]
        st.metric("Конвертаций в USD", usd_conversions)
    with col3:
        if not df.empty:
            last_update = df['created_at'].iloc[0]
            st.metric("Последняя операция", pd.to_datetime(last_update).strftime('%H:%M'))
    

    st.markdown("---")
    csv = df.to_csv(index=False, encoding='utf-8')
    st.download_button(
        label="📥 Скачать историю (CSV)",
        data=csv,
        file_name=f"currency_history_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )
    
else:
    st.warning("📭 История конвертаций пуста или недоступна.")
    st.info("Совершите несколько конвертаций через бота, чтобы заполнить историю.")


if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()

st.markdown("---")
st.caption(f"🔄 Панель обновлена: {datetime.now().strftime('%H:%M:%S')}")
