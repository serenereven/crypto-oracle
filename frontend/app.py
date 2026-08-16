"""
Streamlit-админка для управления прогнозами.
Обращается к FastAPI backend через HTTP-запросы.
"""
import streamlit as st
import requests
import pandas as pd
from datetime import datetime

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="Crypto Oracle — Админка аналитика",
    page_icon="📊",
    layout="wide"
)

st.title("Crypto Oracle: Управление прогнозами")
st.caption("Внутренний инструмент аналитика. Не является финансовой рекомендацией.")


# ==================== Проверка доступности backend ====================

def check_backend() -> bool:
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=3)
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


backend_ok = check_backend()

if not backend_ok:
    st.error(
        "Backend недоступен. Убедитесь, что сервер FastAPI запущен:\n\n"
        "```\npython -m uvicorn backend.main:app --reload\n```"
    )
    st.stop()

st.success("Backend подключен.")
st.markdown("---")


# ==================== Загрузка справочника активов ====================

assets_response = requests.get(f"{API_BASE}/assets")
assets = assets_response.json()

# Маппинг для отображения в таблицах
asset_display = {
    asset["id"]: f"{asset['symbol']}/{asset['quote_currency'].upper()}"
    for asset in assets
}

# Для сайдбара: полное название
asset_options = {
    f"{asset['symbol']}/{asset['quote_currency'].upper()} — {asset['name']}": asset["id"]
    for asset in assets
}


# ==================== Сайдбар: создание прогноза ====================

st.sidebar.header("Создание нового прогноза")

selected_asset_name = st.sidebar.selectbox(
    "Выберите актив",
    options=list(asset_options.keys())
)

if st.sidebar.button("Сформировать прогноз", type="primary"):
    with st.spinner("Сбор данных и расчёт прогноза..."):
        resp = requests.post(
            f"{API_BASE}/predictions",
            params={"asset_id": asset_options[selected_asset_name]}
        )
        if resp.status_code == 201:
            st.sidebar.success("Прогноз создан и активирован.")
            st.rerun()
        else:
            error_detail = resp.json().get("detail", "неизвестная ошибка")
            st.sidebar.error(f"Ошибка: {error_detail}")


# ==================== Реестр прогнозов ====================

st.header("Реестр прогнозов")

col_filter, col_refresh = st.columns([3, 1])

with col_filter:
    status_filter = st.selectbox(
        "Фильтр по статусу",
        options=["Все", "draft", "collecting", "active", "fulfilled", "expired", "cancelled"]
    )

with col_refresh:
    if st.button("Обновить"):
        st.rerun()

params = {} if status_filter == "Все" else {"status": status_filter}
predictions_response = requests.get(f"{API_BASE}/predictions", params=params)
predictions = predictions_response.json()

if predictions:
    df = pd.DataFrame(predictions)
    
    # Добавляем читаемое название актива и валюту
    df["Актив"] = df["asset_id"].map(asset_display)
    df["Валюта"] = df["quote_currency"].str.upper()
    
    # Форматирование дат и числовых полей
    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    df["confidence"] = df["confidence"].apply(lambda x: f"{x:.0f}%" if x else "-")
    df["score"] = df["score"].apply(lambda x: f"{x:.0f}" if x else "-")
    
    # Подготовка таблицы для отображения
    df_display = df.rename(columns={
        "id": "ID",
        "status": "Статус",
        "verdict": "Вердикт",
        "confidence": "Уверенность",
        "risk_level": "Риск",
        "score": "Score",
        "created_at": "Создан"
    })
    
    display_cols = [
        "ID", "Актив", "Валюта", "Статус", "Вердикт",
        "Уверенность", "Риск", "Score", "Создан"
    ]
    
    st.dataframe(
        df_display[display_cols],
        hide_index=True,
        use_container_width=True
    )
else:
    st.info("Прогнозы не найдены. Создайте первый прогноз в сайдбаре.")


# ==================== Детальная карточка ====================

st.markdown("---")
st.header("Детальная карточка прогноза")

if predictions:
    pred_id = st.selectbox(
        "Выберите прогноз для просмотра",
        options=[p["id"] for p in predictions],
        format_func=lambda x: f"Прогноз #{x}"
    )
    
    detail_response = requests.get(f"{API_BASE}/predictions/{pred_id}")
    if detail_response.status_code != 200:
        st.error("Не удалось загрузить прогноз.")
        st.stop()
    
    pred = detail_response.json()
    
    # Получаем информацию об активе
    asset_id = pred["asset_id"]
    asset_info = next((a for a in assets if a["id"] == asset_id), None)
    asset_label = f"{asset_info['symbol']}/{asset_info['quote_currency'].upper()}" if asset_info else f"ID {asset_id}"
    
    # Основные метрики
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Актив", asset_label)
    col2.metric("Валюта", pred.get("quote_currency", "-").upper())
    col3.metric("Статус", pred["status"])
    col4.metric("Вердикт", pred["verdict"] or "-")
    col5.metric("Уверенность", f"{pred['confidence']:.0f}%" if pred["confidence"] else "-")
    col6.metric("Риск", pred["risk_level"] or "-")
    
    # Аргументация
    st.subheader("Аргументация модели")
    if pred["arguments"]:
        st.write(pred["arguments"])
    else:
        st.info("Аргументы отсутствуют.")
    
    # Сырые данные
    st.subheader("Сырые данные (источники)")
    raw_data_response = requests.get(f"{API_BASE}/predictions/{pred_id}/raw_data")
    raw_data = raw_data_response.json()
    
    if raw_data:
        df_raw = pd.DataFrame(raw_data)
        df_raw["collected_at"] = pd.to_datetime(df_raw["collected_at"]).dt.strftime("%Y-%m-%d %H:%M")
        df_raw = df_raw.rename(columns={
            "source": "Источник",
            "metric": "Метрика",
            "value": "Значение",
            "collected_at": "Собрано"
        })
        st.dataframe(
            df_raw[["Источник", "Метрика", "Значение", "Собрано"]],
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Сырые данные отсутствуют.")
    
    # История статусов
    st.subheader("История изменений статуса")
    history_response = requests.get(f"{API_BASE}/predictions/{pred_id}/history")
    history = history_response.json()
    
    if history:
        df_history = pd.DataFrame(history)
        df_history["changed_at"] = pd.to_datetime(df_history["changed_at"]).dt.strftime("%Y-%m-%d %H:%M")
        df_history = df_history.rename(columns={
            "from_status": "Из статуса",
            "to_status": "В статус",
            "reason": "Причина",
            "changed_at": "Изменён"
        })
        st.dataframe(
            df_history[["Из статуса", "В статус", "Причина", "Изменён"]],
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("История изменений пуста.")
    
    # Ручное управление статусом
    st.markdown("---")
    st.subheader("Ручное управление")
    
    col_status, col_reason = st.columns([1, 2])
    
    with col_status:
        new_status = st.selectbox(
            "Изменить статус на:",
            options=["active", "fulfilled", "expired", "cancelled"]
        )
    
    with col_reason:
        reason = st.text_input(
            "Причина изменения",
            placeholder="Например: ручная отмена аналитиком"
        )
    
    if st.button("Применить изменение статуса", type="secondary"):
        payload = {"new_status": new_status, "reason": reason or "Ручное изменение"}
        resp = requests.put(f"{API_BASE}/predictions/{pred_id}/status", json=payload)
        
        if resp.status_code == 200:
            st.success(f"Статус изменён на '{new_status}'.")
            st.rerun()
        else:
            error_detail = resp.json().get("detail", "неизвестная ошибка")
            st.error(f"Ошибка: {error_detail}")
else:
    st.info("Нет прогнозов для просмотра.")


# ==================== Подвал ====================

st.markdown("---")
st.caption(
    f"Backend: {API_BASE} | "
    f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
    "Crypto Oracle v1.0"
)