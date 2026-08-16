"""
SQLAlchemy модели базы данных.
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from backend.db import Base


def utcnow():
    """Фабрика текущего времени в UTC для default-значений SQLAlchemy."""
    return datetime.now(timezone.utc)


class PredictionStatus(str, enum.Enum):
    """Статусы жизненного цикла прогноза."""
    DRAFT = "draft"
    COLLECTING = "collecting"
    ACTIVE = "active"
    FULFILLED = "fulfilled"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Asset(Base):
    """Справочник активов с указанием валюты котировки."""
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)                       # BTC, ETH, SOL
    external_id = Column(String, nullable=False)                  # bitcoin, ethereum
    quote_currency = Column(String, nullable=False, default="usd")  # usd, eur, rub, usdt

    predictions = relationship("Prediction", back_populates="asset")

    def __repr__(self):
        return f"<Asset {self.symbol}/{self.quote_currency.upper()}>"


class Prediction(Base):
    """Прогноз как бизнес-сущность (заявка)."""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    asset = relationship("Asset", back_populates="predictions")

    # Дублируем валюту котировки для независимости прогноза
    quote_currency = Column(String, nullable=False)

    status = Column(
        SQLEnum(PredictionStatus),
        default=PredictionStatus.DRAFT,
        nullable=False
    )
    score = Column(Float, nullable=True)
    verdict = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    risk_level = Column(String, nullable=True)
    arguments = Column(String, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime, nullable=True)

    raw_data = relationship("RawDataPoint", back_populates="prediction", cascade="all, delete-orphan")
    history = relationship("StatusHistory", back_populates="prediction", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Prediction {self.id} [{self.status}]>"


class RawDataPoint(Base):
    """Сырые метрики, собранные для конкретного прогноза."""
    __tablename__ = "raw_data"

    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=False)
    prediction = relationship("Prediction", back_populates="raw_data")

    source = Column(String, nullable=False)    # coingecko | alternative.me
    metric = Column(String, nullable=False)    # price | rsi_14 | fear_greed_index
    value = Column(Float, nullable=False)
    collected_at = Column(DateTime, default=utcnow)


class StatusHistory(Base):
    """Аудит-трейл изменений статуса прогноза."""
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=False)
    prediction = relationship("Prediction", back_populates="history")

    from_status = Column(String, nullable=False)
    to_status = Column(String, nullable=False)
    reason = Column(String, nullable=True)
    changed_at = Column(DateTime, default=utcnow)