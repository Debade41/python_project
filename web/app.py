import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
import time
import os

st.set_page_config(page_title="Currency Bot Dashboard", layout="wide")
st.title("📊 Панель управления Currency Bot")


API_BASE_URL = "http://api:8000"


st.header("Best парсер валют")


with st.form("parser_form"):
    test_text = st.text_area(
        "Введите текст для анализа:", 
        "Купил пиццу за 25 баксов и кофе за 300 рублей, ноутбук за 666 долларов",
        height=100
    )
    
    submit_button = st.form_submit_button("🔍 Распознать валюты")

if submit_button:
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
    limit = st.number_input("Количество записей", min_value=1, max_value=100, value=10, step=5, key="history_limit")
with col2:
    auto_refresh = st.checkbox("Автообновление", value=False, key="auto_refresh")  
    if auto_refresh:
        refresh_interval = st.number_input("Интервал (сек)", min_value=5, max_value=60, value=10, step=5, key="refresh_interval")
with col3:
    refresh_clicked = st.button("🔄 Обновить историю", type="secondary", key="refresh_btn")


@st.cache_data(ttl=5)
def load_history_cached(limit: int, force_refresh: bool = False):
    """Загружает историю с кешированием"""
    try:
        response = requests.get(f'{API_BASE_URL}/history?limit={limit}', timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.ConnectionError:
        return None


if 'force_refresh' not in st.session_state:
    st.session_state.force_refresh = False


if refresh_clicked:
    st.session_state.force_refresh = True
    st.cache_data.clear()  


history_data = load_history_cached(limit, st.session_state.force_refresh)


st.session_state.force_refresh = False

if history_data and history_data.get('conversions'):
    conversions = history_data['conversions']
    
    
    df = pd.DataFrame(conversions)
    
    
    df.insert(0, '№', range(1, len(df) + 1))
    
    parsed_time = pd.to_datetime(df['created_at'], utc=True, errors='coerce')
    parsed_local = parsed_time.dt.tz_convert('Europe/Moscow')
    df['Время'] = parsed_local.dt.strftime('%H:%M')
    df['Дата'] = parsed_local.dt.strftime('%d.%m.%Y')
    
    
    def format_number(x):
        return f"{x:,.2f}".replace(",", " ")
    
    df['Сумма'] = df['amount'].apply(format_number)
    df['Результат'] = df['converted_amount'].apply(format_number)
    df['Курс'] = df['rate'].apply(lambda x: f"{x:.4f}")
    
    
    st.dataframe(
        df[['№', 'Сумма', 'base_currency', 'Результат', 'quote_currency', 'Курс', 'Дата', 'Время']],
        use_container_width=True,
        hide_index=True,
        height=400  
    )
    
   
    ccol1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Всего операций", len(conversions))
    with col2:
        usd_conversions = df[df['quote_currency'] == 'USD'].shape[0]
        st.metric("Конвертаций в USD", usd_conversions)
    with col3:
        if not df.empty:
            last_time = df['created_at'].iloc[0]
            last_parsed = pd.to_datetime(last_time, utc=True, errors='coerce')
            last_local = last_parsed.tz_convert('Europe/Moscow')
            st.metric("Последняя операция", last_local.strftime('%d.%m.%Y %H:%M'))
    
else:
    st.warning("📭 История конвертаций пуста или недоступна.")
    st.info("Совершите несколько конвертаций через бота, чтобы заполнить историю.")

st.markdown("---")
st.caption(f"🔄 Панель обновлена: {datetime.now().strftime('%H:%M:%S')}")
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
