"""
Сбор данных из внешних источников.
"""
import requests
import pandas as pd


COINGECKO_BASE = "https://api.coingecko.com/api/v3"
FNG_URL = "https://api.alternative.me/fng/"


def get_market_chart(external_id: str, quote_currency: str = "usd", days: int = 30) -> dict:
    """
    Возвращает исторические данные актива в указанной валюте котировки.
    Поддерживаемые валюты: usd, eur, rub, usdt, btc, eth и другие.
    """
    url = f"{COINGECKO_BASE}/coins/{external_id}/market_chart"
    params = {"vs_currency": quote_currency.lower(), "days": days}
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"CoinGecko API error: {e}")


def get_fear_greed_index() -> int:
    """Возвращает текущее значение индекса страха и жадности (0-100)."""
    try:
        resp = requests.get(f"{FNG_URL}?limit=1", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return int(data["data"][0]["value"])
    except (requests.exceptions.RequestException, KeyError, IndexError, ValueError) as e:
        raise RuntimeError(f"Fear & Greed API error: {e}")


def calculate_rsi(prices: list, period: int = 14) -> float:
    """Расчёт Relative Strength Index."""
    if len(prices) < period + 1:
        return 50.0
    
    df = pd.DataFrame({"price": prices})
    delta = df["price"].diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    
    rs = gain / loss.replace(0, 1e-10)
    rsi = 100 - (100 / (1 + rs))
    
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0


def collect_all(external_id: str, quote_currency: str = "usd") -> list[tuple]:
    """
    Собирает все метрики для прогноза в указанной валюте котировки.
    Возвращает список кортежей: (source, metric, value).
    """
    collected = []
    
    # Источник 1: CoinGecko (цены в указанной валюте)
    chart = get_market_chart(external_id, quote_currency=quote_currency)
    prices = [p[1] for p in chart.get("prices", [])]
    volumes = [v[1] for v in chart.get("total_volumes", [])]
    
    if len(prices) < 25:
        raise RuntimeError("Недостаточно исторических данных от CoinGecko")
    
    current_price = prices[-1]
    price_24h_ago = prices[-24]
    price_change_pct = ((current_price - price_24h_ago) / price_24h_ago) * 100
    
    current_volume = volumes[-1]
    volume_24h_ago = volumes[-24]
    volume_change_pct = ((current_volume - volume_24h_ago) / volume_24h_ago) * 100
    
    rsi = calculate_rsi(prices)
    
    collected.append(("coingecko", "price", current_price))
    collected.append(("coingecko", "price_change_24h", price_change_pct))
    collected.append(("coingecko", "volume_change_24h", volume_change_pct))
    collected.append(("coingecko", "rsi_14", rsi))
    
    # Источник 2: Alternative.me (индекс не зависит от валюты котировки)
    fng = get_fear_greed_index()
    collected.append(("alternative.me", "fear_greed_index", float(fng)))
    
    return collected