import os
import json
import pickle
import logging
from typing import List, Any

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.requests import Request
from starlette.responses import Response
import numpy as np

# Import data quality checker
import sys
sys.path.append('/app/model')
from data_quality import DataQualityChecker

# Optional drift detection with alibi-detect
DRIFT_ENABLED = os.getenv("DRIFT_ENABLED", "false").lower() == "true"
DRIFT_WEBHOOK = os.getenv("DRIFT_WEBHOOK")

if DRIFT_ENABLED:
    try:
        from alibi_detect.cd import MMDDrift
    except Exception as e:
        raise RuntimeError(
            "Set DRIFT_ENABLED=false or add 'alibi-detect' to requirements"
        )

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("inference")

# Prometheus metrics
REQUEST_COUNT = Counter(
    "requests_total", "Total prediction requests", ["endpoint", "method", "code"]
)
LATENCY = Histogram(
    "request_latency_seconds",
    "Request latency",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
DRIFT_EVENTS = Counter("drift_events_total", "Detected drift events")


class PredictRequest(BaseModel):
    data: List[List[float]]  # табличні фічі: список зразків (n x d)


class PredictResponse(BaseModel):
    predictions: List[Any]
    model_version: str
    drift: bool = False


app = FastAPI(title="aiops-quality-project inference")

# Load model at startup
MODEL_PATH = os.getenv("MODEL_PATH", "./model/model.pkl")
VERSION_PATH = os.getenv("MODEL_VERSION_PATH", "./model/model_version.txt")

model = None
model_version = "unknown"
ref_data = None
cd = None
dq_checker = None


@app.on_event("startup")
def load_model():
    global model, model_version, ref_data, cd, dq_checker
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    if os.path.exists(VERSION_PATH):
        with open(VERSION_PATH) as vf:
            model_version = vf.read().strip()
    
    # Initialize data quality checker
    dq_checker = DataQualityChecker()
    
    # Load reference data for drift detection
    ref_data_path = os.path.join(os.path.dirname(MODEL_PATH), "reference_data.npy")
    if os.path.exists(ref_data_path):
        ref_data = dq_checker.load_reference_data(ref_data_path)
    else:
        # Fallback to mock data if reference data not available
        np.random.seed(0)
        ref_data = np.random.normal(0, 1, size=(200, getattr(model, "n_features_in_", 4)))
    
    # Prepare drift detector
    if DRIFT_ENABLED:
        cd = MMDDrift(ref_data, p_val=0.05)
    
    log.info("Model loaded. Version=%s", model_version)


@app.get("/health")
def health():
    return {"status": "ok", "model_version": model_version}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict", response_model=PredictResponse)
@LATENCY.time()
async def predict(
    req: PredictRequest, background_tasks: BackgroundTasks, request: Request
):
    try:
        X = np.array(req.data)
        
        # Validate data quality
        if dq_checker and not dq_checker.validate_inference_data(X):
            log.warning("Data quality validation failed for inference request")
            # Continue with prediction but log the issue
        
        y_pred = model.predict(X)
    except Exception as e:
        REQUEST_COUNT.labels("/predict", request.method, "500").inc()
        log.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    drift_flag = False
    drift_details = {}
    
    # Check for drift using both Alibi Detect and statistical tests
    if DRIFT_ENABLED and cd is not None:
        preds = cd.predict(X)
        drift_flag = bool(preds.get("data", {}).get("is_drift", 0))
        if drift_flag:
            DRIFT_EVENTS.inc()
            log.warning("Drift detected: p_val=%.4f", preds["data"]["p_val"])
            if DRIFT_WEBHOOK:
                background_tasks.add_task(_notify_webhook, preds)
    
    # Additional drift detection using statistical tests
    if ref_data is not None and dq_checker:
        stat_drift, drift_details = dq_checker.detect_data_drift(ref_data, X)
        if stat_drift:
            drift_flag = True
            DRIFT_EVENTS.inc()
            log.warning("Statistical drift detected: %s", drift_details)

    REQUEST_COUNT.labels("/predict", request.method, "200").inc()
    return PredictResponse(
        predictions=list(map(_pyify, y_pred)),
        model_version=model_version,
        drift=drift_flag,
    )


def _notify_webhook(payload):
    import requests  # optional dependency inside container

    try:
        requests.post(DRIFT_WEBHOOK, json={"event": "drift", "payload": payload})
    except Exception as e:
        log.error("Webhook failed: %s", e)


def _pyify(x):
    try:
        return x.item()
    except Exception:
        return x
