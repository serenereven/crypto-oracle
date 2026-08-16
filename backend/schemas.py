"""
Pydantic схемы для сериализации API.
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class AssetOut(BaseModel):
    id: int
    name: str
    symbol: str
    external_id: str
    quote_currency: str

    model_config = ConfigDict(from_attributes=True)


class RawDataPointOut(BaseModel):
    id: int
    source: str
    metric: str
    value: float
    collected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StatusHistoryOut(BaseModel):
    id: int
    from_status: str
    to_status: str
    reason: Optional[str]
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PredictionOut(BaseModel):
    id: int
    asset_id: int
    quote_currency: str
    status: str
    score: Optional[float]
    verdict: Optional[str]
    confidence: Optional[float]
    risk_level: Optional[str]
    arguments: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class PredictionDetail(PredictionOut):
    """Расширенная карточка прогноза с сырыми данными и историей."""
    raw_data: list[RawDataPointOut] = []
    history: list[StatusHistoryOut] = []
    asset: Optional[AssetOut] = None


class StatusUpdate(BaseModel):
    new_status: str
    reason: Optional[str] = "Ручное изменение"