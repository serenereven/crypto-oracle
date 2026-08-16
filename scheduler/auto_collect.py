"""
Фоновый скрипт для автоматической проверки истёкших прогнозов.

Запуск по расписанию (cron / Task Scheduler):
    python -m scheduler.auto_collect

Или вручную для одноразовой проверки:
    python scheduler/auto_collect.py
"""
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path для импортов
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime
from sqlalchemy.orm import Session
from backend import models, data_collector
from backend.db import SessionLocal, init_db


def check_expired_predictions(db: Session) -> dict:
    """
    Проверяет прогнозы с истёкшим сроком действия.
    Возвращает статистику проверки.
    """
    stats = {"checked": 0, "fulfilled": 0, "expired": 0, "errors": 0}
    
    expired_predictions = db.query(models.Prediction).filter(
        models.Prediction.status == models.PredictionStatus.ACTIVE,
        models.Prediction.expires_at <= datetime.utcnow()
    ).all()
    
    for prediction in expired_predictions:
        stats["checked"] += 1
        
        try:
            asset = db.query(models.Asset).filter_by(id=prediction.asset_id).first()
            if not asset:
                continue
            
            # Получаем фактическую цену
            chart = data_collector.get_market_chart(asset.external_id, days=1)
            actual_price = chart["prices"][-1][1]
            
            # Получаем начальную цену из сырых данных
            initial_data = db.query(models.RawDataPoint).filter(
                models.RawDataPoint.prediction_id == prediction.id,
                models.RawDataPoint.metric == "price"
            ).first()
            
            if not initial_data:
                continue
            
            initial_price = initial_data.value
            actual_change = (actual_price - initial_price) / initial_price
            
            # Определяем, сбылся ли прогноз
            predicted_up = prediction.verdict in ("Рост (Strong Buy)", "Рост (Buy)")
            predicted_down = prediction.verdict in ("Падение (Strong Sell)", "Падение (Sell)")
            actually_up = actual_change > 0
            
            if (predicted_up and actually_up) or (predicted_down and not actually_up):
                new_status = models.PredictionStatus.FULFILLED
                stats["fulfilled"] += 1
            elif predicted_up or predicted_down:
                new_status = models.PredictionStatus.EXPIRED
                stats["expired"] += 1
            else:
                # Для "Боковик" проверяем, что изменение незначительное
                if abs(actual_change) < 0.02:  # ±2%
                    new_status = models.PredictionStatus.FULFILLED
                    stats["fulfilled"] += 1
                else:
                    new_status = models.PredictionStatus.EXPIRED
                    stats["expired"] += 1
            
            prediction.status = new_status
            
            db.add(models.StatusHistory(
                prediction_id=prediction.id,
                from_status="active",
                to_status=new_status.value,
                reason=(
                    f"Автоматическая проверка через 24ч. "
                    f"Фактическое изменение: {actual_change:.2%}. "
                    f"Начальная цена: ${initial_price:.2f}, "
                    f"фактическая: ${actual_price:.2f}"
                )
            ))
            
        except Exception as e:
            stats["errors"] += 1
            print(f"Ошибка проверки прогноза #{prediction.id}: {e}")
    
    db.commit()
    return stats


def main():
    """Точка входа для скрипта."""
    print(f"[{datetime.now().isoformat()}] Запуск проверки истёкших прогнозов...")
    
    init_db()
    db = SessionLocal()
    
    try:
        stats = check_expired_predictions(db)
        print(f"Проверено прогнозов: {stats['checked']}")
        print(f"Подтвердилось: {stats['fulfilled']}")
        print(f"Не подтвердилось: {stats['expired']}")
        print(f"Ошибок: {stats['errors']}")
    finally:
        db.close()
    
    print(f"[{datetime.now().isoformat()}] Проверка завершена.")


if __name__ == "__main__":
    main()