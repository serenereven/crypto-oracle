"""
Подключение к базе данных, управление сессиями SQLAlchemy.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "predictions.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Создаёт таблицы и заполняет справочник активов."""
    from backend import models
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        if db.query(models.Asset).count() == 0:
            default_assets = [
                # Основные пары к USD
                models.Asset(name="Bitcoin", symbol="BTC", external_id="bitcoin", quote_currency="usd"),
                models.Asset(name="Ethereum", symbol="ETH", external_id="ethereum", quote_currency="usd"),
                models.Asset(name="Solana", symbol="SOL", external_id="solana", quote_currency="usd"),
                # Альтернативные валюты (для демонстрации гибкости модели)
                models.Asset(name="Bitcoin", symbol="BTC", external_id="bitcoin", quote_currency="eur"),
                models.Asset(name="Bitcoin", symbol="BTC", external_id="bitcoin", quote_currency="rub"),
                # Криптопара к стейблкоину
                models.Asset(name="Bitcoin", symbol="BTC", external_id="bitcoin", quote_currency="usdt"),
            ]
            db.add_all(default_assets)
            db.commit()
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()