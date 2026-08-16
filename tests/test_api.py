"""
Integration-тесты для FastAPI endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.db import init_db, engine, Base


@pytest.fixture(scope="function")
def client():
    """Создаёт тестовый клиент с чистой БД для каждого теста."""
    # Пересоздаём таблицы
    Base.metadata.drop_all(bind=engine)
    init_db()
    
    with TestClient(app) as c:
        yield c
    
    # Очистка после теста
    Base.metadata.drop_all(bind=engine)


class TestAssetsAPI:
    """Тесты для endpoints активов."""
    
    def test_list_assets(self, client):
        response = client.get("/assets")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 3
        assert data[0]["name"] == "Bitcoin (BTC)"
    
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestPredictionsAPI:
    """Тесты для endpoints прогнозов."""
    
    def test_create_prediction(self, client):
        response = client.post("/predictions", params={"asset_id": 1})
        
        # Может вернуть 201 или 502 (если внешний API недоступен)
        assert response.status_code in (201, 502)
        
        if response.status_code == 201:
            data = response.json()
            assert data["asset_id"] == 1
            assert data["status"] == "active"
    
    def test_create_prediction_invalid_asset(self, client):
        response = client.post("/predictions", params={"asset_id": 999})
        assert response.status_code == 404
    
    def test_list_predictions_empty(self, client):
        response = client.get("/predictions")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_update_status_invalid(self, client):
        response = client.put(
            "/predictions/1/status",
            json={"new_status": "invalid_status"}
        )
        # Прогноз не существует или недопустимый статус
        assert response.status_code in (404, 400)