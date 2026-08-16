from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from backend import models, schemas, data_collector, predictor
from backend.db import get_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Crypto Oracle API",
    description="Backend для прогнозирования цен криптовалют",
    version="1.0",
    lifespan=lifespan
)


@app.get("/assets", response_model=list[schemas.AssetOut])
def list_assets(db: Session = Depends(get_db)):
    return db.query(models.Asset).all()


@app.post("/predictions", response_model=schemas.PredictionOut, status_code=201)
def create_prediction(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(models.Asset).filter_by(id=asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Актив не найден")
    
    prediction = models.Prediction(
        asset_id=asset_id,
        quote_currency=asset.quote_currency,  # сохраняем валюту котировки
        status=models.PredictionStatus.DRAFT,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    
    prediction.status = models.PredictionStatus.COLLECTING
    db.add(models.StatusHistory(
        prediction_id=prediction.id,
        from_status="draft",
        to_status="collecting",
        reason=f"Начат сбор данных в {asset.quote_currency.upper()}"
    ))
    db.commit()
    
    try:
        # Передаём валюту котировки в сборщик данных
        raw_data = data_collector.collect_all(
            asset.external_id,
            quote_currency=asset.quote_currency
        )
        
        for source, metric, value in raw_data:
            db.add(models.RawDataPoint(
                prediction_id=prediction.id,
                source=source,
                metric=metric,
                value=value
            ))
        
        result = predictor.calculate_score(raw_data)
        
        prediction.score = result["score"]
        prediction.verdict = result["verdict"]
        prediction.confidence = result["confidence"]
        prediction.risk_level = result["risk_level"]
        prediction.arguments = result["arguments"]
        prediction.status = models.PredictionStatus.ACTIVE
        
        db.add(models.StatusHistory(
            prediction_id=prediction.id,
            from_status="collecting",
            to_status="active",
            reason="Данные собраны, прогноз рассчитан"
        ))
        db.commit()
        db.refresh(prediction)
        return prediction
        
    except Exception as e:
        prediction.status = models.PredictionStatus.DRAFT
        db.add(models.StatusHistory(
            prediction_id=prediction.id,
            from_status="collecting",
            to_status="draft",
            reason=f"Ошибка сбора данных: {str(e)}"
        ))
        db.commit()
        raise HTTPException(status_code=502, detail=f"Ошибка сбора данных: {str(e)}")


@app.get("/predictions", response_model=list[schemas.PredictionOut])
def list_predictions(status: str = None, db: Session = Depends(get_db)):
    query = db.query(models.Prediction)
    if status:
        query = query.filter(models.Prediction.status == status)
    return query.order_by(models.Prediction.created_at.desc()).all()


@app.get("/predictions/{prediction_id}", response_model=schemas.PredictionDetail)
def get_prediction(prediction_id: int, db: Session = Depends(get_db)):
    prediction = db.query(models.Prediction).filter_by(id=prediction_id).first()
    if not prediction:
        raise HTTPException(status_code=404, detail="Прогноз не найден")
    return prediction


@app.put("/predictions/{prediction_id}/status", response_model=schemas.PredictionOut)
def update_status(
    prediction_id: int,
    payload: schemas.StatusUpdate,
    db: Session = Depends(get_db)
):
    prediction = db.query(models.Prediction).filter_by(id=prediction_id).first()
    if not prediction:
        raise HTTPException(status_code=404, detail="Прогноз не найден")
    
    try:
        new_status = models.PredictionStatus(payload.new_status)
    except ValueError:
        valid = [s.value for s in models.PredictionStatus]
        raise HTTPException(status_code=400, detail=f"Недопустимый статус. Допустимые: {valid}")
    
    old_status = prediction.status
    prediction.status = new_status
    
    db.add(models.StatusHistory(
        prediction_id=prediction_id,
        from_status=old_status.value,
        to_status=new_status.value,
        reason=payload.reason
    ))
    db.commit()
    db.refresh(prediction)
    return prediction


@app.get("/predictions/{prediction_id}/raw_data", response_model=list[schemas.RawDataPointOut])
def get_raw_data(prediction_id: int, db: Session = Depends(get_db)):
    return db.query(models.RawDataPoint).filter_by(prediction_id=prediction_id).all()


@app.get("/predictions/{prediction_id}/history", response_model=list[schemas.StatusHistoryOut])
def get_history(prediction_id: int, db: Session = Depends(get_db)):
    return db.query(models.StatusHistory).filter_by(prediction_id=prediction_id).all()


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }