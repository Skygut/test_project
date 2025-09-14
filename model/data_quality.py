"""
Great Expectations data quality checks for model training and inference
"""

import os
import pandas as pd
import numpy as np
from great_expectations.core import ExpectationSuite
from great_expectations.dataset import PandasDataset
from great_expectations.core.expectation_configuration import ExpectationConfiguration
import logging

log = logging.getLogger(__name__)

class DataQualityChecker:
    def __init__(self, reference_data_path=None):
        self.reference_data_path = reference_data_path
        self.expectation_suite = None
        self._create_expectation_suite()
    
    def _create_expectation_suite(self):
        """Create expectation suite for data quality checks"""
        suite = ExpectationSuite(expectation_suite_name="data_quality_suite")
        
        # Basic data shape expectations
        suite.add_expectation(ExpectationConfiguration(
            expectation_type="expect_table_row_count_to_be_between",
            kwargs={"min_value": 1, "max_value": 10000}
        ))
        
        # Column expectations
        suite.add_expectation(ExpectationConfiguration(
            expectation_type="expect_table_columns_to_match_ordered_list",
            kwargs={"column_list": ["feature_0", "feature_1", "feature_2", "feature_3"]}
        ))
        
        # Data type expectations
        for i in range(4):
            suite.add_expectation(ExpectationConfiguration(
                expectation_type="expect_column_to_exist",
                kwargs={"column": f"feature_{i}"}
            ))
            suite.add_expectation(ExpectationConfiguration(
                expectation_type="expect_column_values_to_be_of_type",
                kwargs={"column": f"feature_{i}", "type_": "float64"}
            ))
            suite.add_expectation(ExpectationConfiguration(
                expectation_type="expect_column_values_to_not_be_null",
                kwargs={"column": f"feature_{i}"}
            ))
            suite.add_expectation(ExpectationConfiguration(
                expectation_type="expect_column_values_to_be_between",
                kwargs={"column": f"feature_{i}", "min_value": -10, "max_value": 10}
            ))
        
        self.expectation_suite = suite
        log.info("Data quality expectation suite created")
    
    def validate_training_data(self, X, y):
        """Validate training data quality"""
        try:
            # Convert to DataFrame for GE
            df = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(X.shape[1])])
            df["target"] = y
            
            # Create dataset
            dataset = PandasDataset(df, expectation_suite=self.expectation_suite)
            
            # Run validations
            validation_result = dataset.validate()
            
            if validation_result.success:
                log.info("Training data quality validation passed")
                return True
            else:
                log.warning(f"Training data quality validation failed: {validation_result.statistics}")
                return False
                
        except Exception as e:
            log.error(f"Data quality validation error: {e}")
            return False
    
    def validate_inference_data(self, X):
        """Validate inference data quality"""
        try:
            # Convert to DataFrame for GE
            df = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(X.shape[1])])
            
            # Create dataset
            dataset = PandasDataset(df, expectation_suite=self.expectation_suite)
            
            # Run validations
            validation_result = dataset.validate()
            
            if validation_result.success:
                log.info("Inference data quality validation passed")
                return True
            else:
                log.warning(f"Inference data quality validation failed: {validation_result.statistics}")
                return False
                
        except Exception as e:
            log.error(f"Data quality validation error: {e}")
            return False
    
    def detect_data_drift(self, reference_data, current_data):
        """Detect data drift using statistical tests"""
        try:
            from scipy import stats
            
            drift_detected = False
            drift_details = {}
            
            for i in range(reference_data.shape[1]):
                # Kolmogorov-Smirnov test
                ks_stat, ks_pvalue = stats.ks_2samp(
                    reference_data[:, i], 
                    current_data[:, i]
                )
                
                # Anderson-Darling test
                try:
                    ad_stat, ad_critical, ad_significance = stats.anderson_ksamp([
                        reference_data[:, i], 
                        current_data[:, i]
                    ])
                except:
                    ad_stat, ad_critical, ad_significance = None, None, None
                
                drift_details[f"feature_{i}"] = {
                    "ks_statistic": ks_stat,
                    "ks_pvalue": ks_pvalue,
                    "ad_statistic": ad_stat,
                    "ad_critical": ad_critical,
                    "ad_significance": ad_significance
                }
                
                # Consider drift if p-value < 0.05
                if ks_pvalue < 0.05:
                    drift_detected = True
                    log.warning(f"Data drift detected in feature_{i}: KS p-value={ks_pvalue:.4f}")
            
            return drift_detected, drift_details
            
        except Exception as e:
            log.error(f"Data drift detection error: {e}")
            return False, {}
    
    def save_reference_data(self, data, path):
        """Save reference data for drift detection"""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            np.save(path, data)
            log.info(f"Reference data saved to {path}")
        except Exception as e:
            log.error(f"Failed to save reference data: {e}")
    
    def load_reference_data(self, path):
        """Load reference data for drift detection"""
        try:
            if os.path.exists(path):
                data = np.load(path)
                log.info(f"Reference data loaded from {path}")
                return data
            else:
                log.warning(f"Reference data not found at {path}")
                return None
        except Exception as e:
            log.error(f"Failed to load reference data: {e}")
            return None
