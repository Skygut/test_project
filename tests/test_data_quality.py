"""
Tests for data quality checker
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

# Mock Great Expectations before importing
with patch.dict('sys.modules', {'great_expectations': MagicMock()}):
    from model.data_quality import DataQualityChecker

def test_data_quality_checker_init():
    """Test DataQualityChecker initialization"""
    checker = DataQualityChecker()
    assert checker.expectation_suite is not None

def test_validate_training_data():
    """Test training data validation"""
    checker = DataQualityChecker()
    
    # Valid data
    X = np.random.randn(100, 4)
    y = np.random.randint(0, 2, 100)
    
    # Mock the validation result
    with patch.object(checker, 'expectation_suite') as mock_suite:
        mock_dataset = MagicMock()
        mock_dataset.validate.return_value = MagicMock(success=True)
        
        with patch('model.data_quality.PandasDataset', return_value=mock_dataset):
            result = checker.validate_training_data(X, y)
            assert result is True

def test_validate_inference_data():
    """Test inference data validation"""
    checker = DataQualityChecker()
    
    # Valid data
    X = np.random.randn(10, 4)
    
    # Mock the validation result
    with patch.object(checker, 'expectation_suite') as mock_suite:
        mock_dataset = MagicMock()
        mock_dataset.validate.return_value = MagicMock(success=True)
        
        with patch('model.data_quality.PandasDataset', return_value=mock_dataset):
            result = checker.validate_inference_data(X)
            assert result is True

def test_detect_data_drift():
    """Test data drift detection"""
    checker = DataQualityChecker()
    
    # Generate reference and current data
    np.random.seed(42)
    ref_data = np.random.normal(0, 1, (100, 4))
    current_data = np.random.normal(0, 1, (50, 4))
    
    # Mock scipy.stats
    with patch('model.data_quality.stats') as mock_stats:
        mock_stats.ks_2samp.return_value = (0.1, 0.05)  # p-value < 0.05 (drift)
        mock_stats.anderson_ksamp.return_value = (1.0, [0.5], [0.05])
        
        drift_detected, details = checker.detect_data_drift(ref_data, current_data)
        
        assert drift_detected is True
        assert "feature_0" in details
        assert "ks_pvalue" in details["feature_0"]

def test_save_load_reference_data():
    """Test saving and loading reference data"""
    checker = DataQualityChecker()
    
    # Test data
    test_data = np.random.randn(50, 4)
    test_path = "/tmp/test_reference_data.npy"
    
    # Mock file operations
    with patch('os.makedirs'), patch('np.save'), patch('np.load', return_value=test_data):
        checker.save_reference_data(test_data, test_path)
        loaded_data = checker.load_reference_data(test_path)
        
        assert loaded_data is not None
