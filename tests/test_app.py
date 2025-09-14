"""
Tests for FastAPI inference service
"""

import pytest
import numpy as np
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Mock the data quality checker before importing the app
with patch.dict('sys.modules', {'data_quality': MagicMock()}):
    from app.main import app

client = TestClient(app)

def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "model_version" in data

def test_metrics_endpoint():
    """Test metrics endpoint"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]

def test_predict_endpoint():
    """Test prediction endpoint"""
    # Mock model prediction
    with patch('app.main.model') as mock_model:
        mock_model.predict.return_value = np.array([0, 1, 0])
        
        test_data = {
            "data": [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]]
        }
        
        response = client.post("/predict", json=test_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "predictions" in data
        assert "model_version" in data
        assert "drift" in data
        assert len(data["predictions"]) == 2

def test_predict_invalid_data():
    """Test prediction with invalid data"""
    test_data = {
        "data": "invalid_data"
    }
    
    response = client.post("/predict", json=test_data)
    assert response.status_code == 422  # Validation error

def test_predict_empty_data():
    """Test prediction with empty data"""
    test_data = {
        "data": []
    }
    
    response = client.post("/predict", json=test_data)
    assert response.status_code == 200  # Should handle empty data gracefully
