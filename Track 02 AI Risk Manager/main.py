import io
import os
from typing import List, Optional
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from risk_engine import engine
import database

app = FastAPI(
    title="Razorpay AI Risk Manager Pro API",
    description="Enterprise Fraud Intelligence & COD Return Risk Decisioning Platform",
    version="2.0.0"
)

# Export legacy variables for direct backward compatibility
model = engine.model
MODEL_LOADED = engine.is_loaded

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static folder exists
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

class Transaction(BaseModel):
    transaction_amount: float
    user_history_returns: int
    item_category_risk: float
    delivery_distance_km: float
    is_cod: int
    threshold_override: Optional[float] = None

class BatchRequest(BaseModel):
    transactions: List[Transaction]
    threshold_override: Optional[float] = None

@app.get("/")
def serve_dashboard():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"status": "online", "service": "Razorpay AI Risk Manager Pro API", "docs": "/docs"})

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    from fastapi import Response
    return Response(status_code=204)

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "Razorpay AI Risk Manager Pro",
        "model_loaded": engine.is_loaded,
        "optimal_threshold": engine.metadata.get("optimal_threshold", 0.50)
    }

@app.post("/score-risk")
def score_risk(tx: Transaction):
    tx_dict = tx.model_dump() if hasattr(tx, "model_dump") else tx.dict()
    result = engine.evaluate(tx_dict, threshold_override=tx.threshold_override)
    
    # Audit log in database if model is operating
    try:
        tx_id = database.log_transaction(tx_dict, result)
        result["transaction_id"] = tx_id
    except Exception as e:
        result["db_log_error"] = str(e)
        
    return result

@app.post("/score-risk/batch")
def score_risk_batch(payload: BatchRequest):
    results = []
    blocked_count = 0
    total_savings = 0
    
    for tx in payload.transactions:
        tx_dict = tx.model_dump() if hasattr(tx, "model_dump") else tx.dict()
        override = payload.threshold_override or tx.threshold_override
        res = engine.evaluate(tx_dict, threshold_override=override)
        try:
            tx_id = database.log_transaction(tx_dict, res)
            res["transaction_id"] = tx_id
        except Exception:
            pass
        
        if res.get("block_cod"):
            blocked_count += 1
            total_savings += 800
            
        results.append(res)

    return {
        "total_scored": len(results),
        "blocked_cod_count": blocked_count,
        "total_estimated_savings_inr": total_savings,
        "results": results
    }

try:
    import multipart
    HAS_MULTIPART = True
except Exception:
    HAS_MULTIPART = False

if HAS_MULTIPART:
    @app.post("/score-risk/upload-csv")
    async def score_risk_csv(file: UploadFile = File(...), threshold_override: Optional[float] = Query(None)):
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        required = ["transaction_amount", "user_history_returns", "item_category_risk", "delivery_distance_km", "is_cod"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            return {"error": f"Missing required columns in CSV: {missing}"}

        scored_rows = []
        blocked_count = 0
        total_savings = 0

        for _, row in df.iterrows():
            tx_dict = {
                "transaction_amount": float(row["transaction_amount"]),
                "user_history_returns": int(row["user_history_returns"]),
                "item_category_risk": float(row["item_category_risk"]),
                "delivery_distance_km": float(row["delivery_distance_km"]),
                "is_cod": int(row["is_cod"])
            }
            res = engine.evaluate(tx_dict, threshold_override=threshold_override)
            try:
                tx_id = database.log_transaction(tx_dict, res)
                res["transaction_id"] = tx_id
            except Exception:
                pass

            if res.get("block_cod"):
                blocked_count += 1
                total_savings += 800

            res_row = dict(tx_dict)
            res_row.update({
                "risk_probability": res["risk_probability"],
                "risk_tier": res["risk_tier"],
                "recommendation": res["recommendation"],
                "block_cod": res["block_cod"]
            })
            scored_rows.append(res_row)

        return {
            "filename": file.filename,
            "total_scored": len(scored_rows),
            "blocked_cod_count": blocked_count,
            "total_estimated_savings_inr": total_savings,
            "sample_preview": scored_rows[:50]
        }
else:
    @app.post("/score-risk/upload-csv")
    def score_risk_csv_fallback():
        return {"error": "python-multipart is required for CSV upload. Run: pip install python-multipart"}


@app.get("/api/analytics")
def get_analytics():
    return database.get_analytics_summary()

@app.get("/api/audit-log")
def get_audit_log(limit: int = 50):
    return database.get_recent_transactions(limit=limit)

@app.get("/api/model-info")
def get_model_info():
    return engine.get_metadata()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)