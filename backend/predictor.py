"""
Бизнес-логика расчёта прогноза.
Прозрачный rule-based скоринг с весами.
"""


def calculate_score(raw_data: list[tuple]) -> dict:
    """
    Принимает список кортежей (source, metric, value).
    Возвращает словарь с результатом прогноза.
    
    Веса правил:
    - Импульс цены (24ч):      +/- 20 очков
    - RSI (перекупленность):   +/- 30 очков
    - Fear & Greed (сентимент): +/- 25 очков
    - Объём торгов:             +/- 15 очков
    
    Итоговый score: от -100 до +100.
    """
    # Преобразуем список в словарь для удобства
    metrics = {metric: value for _, metric, value in raw_data}
    
    score = 0
    arguments = []
    
    price_change = metrics.get("price_change_24h", 0)
    rsi = metrics.get("rsi_14", 50)
    fng = metrics.get("fear_greed_index", 50)
    volume_change = metrics.get("volume_change_24h", 0)
    
    # Правило 1: Ценовой импульс (Momentum)
    if price_change > 2:
        score += 20
        arguments.append(
            f"Бычий импульс: рост на {price_change:.2f}% за 24 часа "
            f"(источник: CoinGecko)"
        )
    elif price_change < -2:
        score -= 20
        arguments.append(
            f"Медвежий импульс: падение на {abs(price_change):.2f}% за 24 часа "
            f"(источник: CoinGecko)"
        )
    else:
        arguments.append(
            f"Умеренное изменение цены ({price_change:.2f}% за 24ч), "
            f"сигнал нейтральный"
        )
    
    # Правило 2: Перекупленность / Перепроданность (RSI)
    if rsi > 70:
        score -= 30
        arguments.append(
            f"Актив перекуплен: RSI(14) = {rsi:.1f}. "
            f"Исторически высока вероятность коррекции"
        )
    elif rsi < 30:
        score += 30
        arguments.append(
            f"Актив перепродан: RSI(14) = {rsi:.1f}. "
            f"Возможен технический отскок"
        )
    else:
        arguments.append(
            f"RSI(14) = {rsi:.1f} находится в нейтральной зоне"
        )
    
    # Правило 3: Контр-трендовый сентимент (Fear & Greed)
    if fng < 25:
        score += 25
        arguments.append(
            f"Экстремальный страх на рынке (F&G = {fng:.0f}). "
            f"Контр-индикатор: хорошая точка для накопления"
        )
    elif fng > 75:
        score -= 25
        arguments.append(
            f"Экстремальная жадность на рынке (F&G = {fng:.0f}). "
            f"Рынок перегрет, риск разворота"
        )
    else:
        arguments.append(
            f"Индекс страха и жадности = {fng:.0f}, "
            f"рынок в нейтральной зоне"
        )
    
    # Правило 4: Подтверждение объёмом
    if volume_change > 20:
        score += 15
        arguments.append(
            f"Рост объёма торгов на {volume_change:.1f}% за 24ч "
            f"подтверждает силу текущего тренда"
        )
    elif volume_change < -20:
        score -= 15
        arguments.append(
            f"Падение объёма торгов на {abs(volume_change):.1f}% за 24ч, "
            f"тренд выдыхается"
        )
    
    # Нормализация счёта
    score = max(min(score, 100), -100)
    
    # Итоговый вердикт
    if score > 30:
        verdict = "Рост (Strong Buy)"
    elif score > 10:
        verdict = "Рост (Buy)"
    elif score < -30:
        verdict = "Падение (Strong Sell)"
    elif score < -10:
        verdict = "Падение (Sell)"
    else:
        verdict = "Боковик (Neutral)"
    
    # Уверенность: чем дальше score от нуля, тем выше уверенность
    confidence = min(abs(score) / 50, 1.0) * 100
    
    # Оценка риска
    risk = "Низкий"
    if abs(price_change) > 5:
        risk = "Высокий (экстремальная волатильность)"
    elif fng > 75 and score > 0:
        risk = "Высокий (покупка на эйфории)"
    elif abs(score) < 15:
        risk = "Средний (слабый сигнал)"
    
    # Границы применимости модели
    arguments.append(
        "Ограничение: модель не учитывает форс-мажоры "
        "(макроэкономические шоки, решения регуляторов, взломы бирж)"
    )
    
    return {
        "score": score,
        "verdict": verdict,
        "confidence": confidence,
        "risk_level": risk,
        "arguments": "\n".join(f"- {a}" for a in arguments)
    }