"""
Enhanced training script with data quality checks and drift detection
"""

import os
import pickle
import logging
from datetime import datetime

import numpy as np
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.model_selection import train_test_split

from data_quality import DataQualityChecker

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

OUT_DIR = os.getenv("OUT_DIR", "./model")
REFERENCE_DATA_PATH = os.path.join(OUT_DIR, "reference_data.npy")

os.makedirs(OUT_DIR, exist_ok=True)

def main():
    log.info("Starting model training with data quality checks")
    
    # Initialize data quality checker
    dq_checker = DataQualityChecker()
    
    # Generate training data
    X, y = make_classification(n_samples=2000, n_features=4, random_state=42)
    log.info(f"Generated dataset: {X.shape[0]} samples, {X.shape[1]} features")
    
    # Validate data quality
    if not dq_checker.validate_training_data(X, y):
        log.error("Data quality validation failed. Aborting training.")
        return False
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Train model
    clf = LogisticRegression(max_iter=1000, random_state=42)
    clf.fit(X_train, y_train)
    
    # Evaluate model
    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_proba)
    
    log.info(f"Model trained successfully. AUC: {auc:.4f}")
    log.info(f"Classification report:\n{classification_report(y_test, y_pred)}")
    
    # Save model
    with open(os.path.join(OUT_DIR, "model.pkl"), "wb") as f:
        pickle.dump(clf, f)
    
    # Save model version
    ver = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    with open(os.path.join(OUT_DIR, "model_version.txt"), "w") as f:
        f.write(ver)
    
    # Save reference data for drift detection
    dq_checker.save_reference_data(X_train, REFERENCE_DATA_PATH)
    
    # Save training metrics
    metrics = {
        "auc": float(auc),
        "accuracy": float((y_pred == y_test).mean()),
        "n_samples": int(X.shape[0]),
        "n_features": int(X.shape[1]),
        "model_version": ver
    }
    
    with open(os.path.join(OUT_DIR, "training_metrics.json"), "w") as f:
        import json
        json.dump(metrics, f, indent=2)
    
    log.info(f"Training completed successfully. Model saved to {OUT_DIR}")
    log.info(f"Model version: {ver}")
    log.info(f"Training metrics: {metrics}")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)
