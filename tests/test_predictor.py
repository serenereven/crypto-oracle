"""
Unit-тесты для бизнес-логики расчёта прогноза.
"""
import pytest
from backend.predictor import calculate_score


class TestCalculateScore:
    """Тесты для функции calculate_score."""
    
    def test_strong_buy_signal(self):
        """Все индикаторы указывают на рост."""
        raw_data = [
            ("coingecko", "price", 50000),
            ("coingecko", "price_change_24h", 3.0),    # +20
            ("coingecko", "volume_change_24h", 25.0),   # +15
            ("coingecko", "rsi_14", 25.0),              # +30
            ("alternative.me", "fear_greed_index", 20), # +25
        ]
        result = calculate_score(raw_data)
        
        assert result["score"] == 90  # 20 + 15 + 30 + 25
        assert "Рост" in result["verdict"]
        assert result["confidence"] > 50
    
    def test_strong_sell_signal(self):
        """Все индикаторы указывают на падение."""
        raw_data = [
            ("coingecko", "price", 50000),
            ("coingecko", "price_change_24h", -3.0),    # -20
            ("coingecko", "volume_change_24h", -25.0),  # -15
            ("coingecko", "rsi_14", 75.0),              # -30
            ("alternative.me", "fear_greed_index", 80), # -25
        ]
        result = calculate_score(raw_data)
        
        assert result["score"] == -90
        assert "Падение" in result["verdict"]
        assert result["confidence"] > 50
    
    def test_neutral_signal(self):
        """Противоречивые сигналы дают боковик."""
        raw_data = [
            ("coingecko", "price", 50000),
            ("coingecko", "price_change_24h", 1.0),     # 0
            ("coingecko", "volume_change_24h", 5.0),    # 0
            ("coingecko", "rsi_14", 50.0),              # 0
            ("alternative.me", "fear_greed_index", 50), # 0
        ]
        result = calculate_score(raw_data)
        
        assert result["score"] == 0
        assert result["verdict"] == "Боковик (Neutral)"
        assert result["confidence"] == 0
    
    def test_score_normalization(self):
        """Score не выходит за пределы [-100, 100]."""
        raw_data = [
            ("coingecko", "price", 50000),
            ("coingecko", "price_change_24h", 10.0),
            ("coingecko", "volume_change_24h", 50.0),
            ("coingecko", "rsi_14", 10.0),
            ("alternative.me", "fear_greed_index", 10),
        ]
        result = calculate_score(raw_data)
        
        assert -100 <= result["score"] <= 100
    
    def test_high_risk_on_high_volatility(self):
        """Высокая волатильность повышает риск."""
        raw_data = [
            ("coingecko", "price", 50000),
            ("coingecko", "price_change_24h", 7.0),
            ("coingecko", "volume_change_24h", 0.0),
            ("coingecko", "rsi_14", 50.0),
            ("alternative.me", "fear_greed_index", 50),
        ]
        result = calculate_score(raw_data)
        
        assert "Высокий" in result["risk_level"]
    
    def test_arguments_not_empty(self):
        """Аргументация всегда заполнена."""
        raw_data = [
            ("coingecko", "price", 50000),
            ("coingecko", "price_change_24h", 0.0),
            ("coingecko", "volume_change_24h", 0.0),
            ("coingecko", "rsi_14", 50.0),
            ("alternative.me", "fear_greed_index", 50),
        ]
        result = calculate_score(raw_data)
        
        assert result["arguments"] is not None
        assert len(result["arguments"]) > 0
        assert "Ограничение" in result["arguments"]