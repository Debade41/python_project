import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Currency Bot Dashboard", layout="wide")
st.title("📊 Панель управления Currency Bot")
API_BASE_URL = "http://api:8000"


st.header("🧪 Тестовый парсер валют")
test_text = st.text_area("Введите текст для анализа:", "Купил пиццу за 25 баксов и кофе за 300 рублей", height=100)
if st.button("Распознать валюты"):
    with st.spinner('Анализирую текст...'):
        try:
            resp = requests.post(f'{API_BASE_URL}/detect-currencies', json={'text': test_text}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data['items']:
                    for item in data['items']:
                        st.success(f"Найдено: {item['match_text']} -> {item['source_amount']} {item['source_currency']}")
                        for conv in item['conversions']:
                            st.info(f"   → {conv['converted_amount']:.2f} {conv['quote_currency']} (курс: {conv['rate']:.4f})")
                else:
                    st.warning("В тексте не обнаружено упоминаний валют.")
            else:
                st.error("Ошибка сервера при анализе текста.")
        except requests.ConnectionError:
            st.error("Не удалось подключиться к серверу анализа. Убедитесь, что backend запущен.")


st.header("📜 История операций")
history_limit = st.slider("Количество записей", 5, 50, 10)
if st.button("Загрузить историю"):
    try:
        resp = requests.get(f'{API_BASE_URL}/history?limit={history_limit}', timeout=10)
        if resp.status_code == 200:
            history_data = resp.json()
            
            if history_data['conversions']:
                df_conv = pd.DataFrame(history_data['conversions'])
                df_conv['created_at'] = pd.to_datetime(df_conv['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                st.subheader("Конвертации")
                st.dataframe(df_conv[['amount', 'base_currency', 'converted_amount', 'quote_currency', 'rate', 'created_at']])
            else:
                st.write("Нет данных о конвертациях.")
        else:
            st.error("Не удалось загрузить историю.")
    except requests.ConnectionError:
        st.warning("Сервис истории временно недоступен.")

st.markdown("---")
st.caption(f"Панель управления | {datetime.now().strftime('%Y-%m-%d %H:%M')}")