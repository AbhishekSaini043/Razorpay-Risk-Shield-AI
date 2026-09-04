import sqlite3
import json
from datetime import datetime, timezone

DB_PATH = "risk_audit.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        transaction_amount REAL NOT NULL,
        user_history_returns INTEGER NOT NULL,
        item_category_risk REAL NOT NULL,
        delivery_distance_km REAL NOT NULL,
        is_cod INTEGER NOT NULL,
        risk_probability REAL NOT NULL,
        block_cod INTEGER NOT NULL,
        risk_tier TEXT NOT NULL,
        recommendation TEXT NOT NULL,
        factors_json TEXT NOT NULL
    )
    """)
    conn.commit()

    # Seed initial demo transactions if empty
    cursor.execute("SELECT COUNT(*) FROM transactions")
    count = cursor.fetchone()[0]
    if count == 0:
        seed_sample_records(cursor)
        conn.commit()

    conn.close()

def seed_sample_records(cursor):
    sample_data = [
        (4800.0, 4, 0.85, 340.0, 1, 0.824, 1, "HIGH", "BLOCK_COD_PREPAID_ONLY", [
            {"factor": "Past Returns (4)", "impact": "High return history (+38%)", "direction": "danger"},
            {"factor": "Item Risk (0.85)", "impact": "High return category (+28%)", "direction": "danger"}
        ]),
        (1200.0, 0, 0.15, 12.0, 0, 0.042, 0, "LOW", "ALLOW_COD", [
            {"factor": "Return History (0)", "impact": "Clean customer history (-22%)", "direction": "safe"},
            {"factor": "Payment (Prepaid)", "impact": "Non-COD transaction (-18%)", "direction": "safe"}
        ]),
        (2500.0, 2, 0.55, 120.0, 1, 0.490, 0, "MEDIUM", "VERIFY_OTP_BEFORE_DISPATCH", [
            {"factor": "Past Returns (2)", "impact": "Moderate return history (+14%)", "direction": "warning"},
            {"factor": "Item Risk (0.55)", "impact": "Moderate category risk (+10%)", "direction": "warning"}
        ]),
        (9200.0, 5, 0.90, 480.0, 1, 0.935, 1, "CRITICAL", "FLAG_SUSPICIOUS_FRAUD", [
            {"factor": "Past Returns (5)", "impact": "Chronic returner history (+45%)", "direction": "danger"},
            {"factor": "Distance (480km)", "impact": "High reverse logistics penalty (+18%)", "direction": "danger"}
        ]),
        (1850.0, 1, 0.25, 45.0, 1, 0.198, 0, "LOW", "ALLOW_COD", [
            {"factor": "Item Risk (0.25)", "impact": "Low return category (-12%)", "direction": "safe"}
        ])
    ]

    for item in sample_data:
        cursor.execute("""
            INSERT INTO transactions (
                created_at, transaction_amount, user_history_returns, item_category_risk,
                delivery_distance_km, is_cod, risk_probability, block_cod, risk_tier,
                recommendation, factors_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7], item[8],
            json.dumps(item[9])
        ))

def log_transaction(tx_data: dict, result: dict) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    factors_json = json.dumps(result.get("top_factors", []))
    
    cursor.execute("""
        INSERT INTO transactions (
            created_at, transaction_amount, user_history_returns, item_category_risk,
            delivery_distance_km, is_cod, risk_probability, block_cod, risk_tier,
            recommendation, factors_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        created_at,
        float(tx_data["transaction_amount"]),
        int(tx_data["user_history_returns"]),
        float(tx_data["item_category_risk"]),
        float(tx_data["delivery_distance_km"]),
        int(tx_data["is_cod"]),
        float(result.get("risk_probability", 0.0)),
        1 if result.get("block_cod", False) else 0,
        result.get("risk_tier", "UNKNOWN"),
        result.get("recommendation", "UNKNOWN"),
        factors_json
    ))
    
    inserted_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return inserted_id

def get_recent_transactions(limit: int = 50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM transactions
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "created_at": r["created_at"],
            "transaction_amount": r["transaction_amount"],
            "user_history_returns": r["user_history_returns"],
            "item_category_risk": r["item_category_risk"],
            "delivery_distance_km": r["delivery_distance_km"],
            "is_cod": bool(r["is_cod"]),
            "risk_probability": round(r["risk_probability"], 3),
            "block_cod": bool(r["block_cod"]),
            "risk_tier": r["risk_tier"],
            "recommendation": r["recommendation"],
            "top_factors": json.loads(r["factors_json"]) if r["factors_json"] else []
        })
    return results

def get_analytics_summary():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*), AVG(risk_probability), SUM(block_cod) FROM transactions")
    total_count, avg_risk, total_blocked = cursor.fetchone()
    total_count = total_count or 0
    avg_risk = round(avg_risk or 0.0, 3)
    total_blocked = total_blocked or 0
    
    block_rate = round((total_blocked / total_count * 100), 1) if total_count > 0 else 0.0
    
    # Razorpay value estimation
    # ₹800 savings per prevented RTO return
    estimated_savings = total_blocked * 800
    
    cursor.execute("""
        SELECT risk_tier, COUNT(*) as count FROM transactions
        GROUP BY risk_tier
    """)
    tier_counts = {row["risk_tier"]: row["count"] for row in cursor.fetchall()}
    
    # Fetch recent risk scores for sparkline/trend
    cursor.execute("""
        SELECT id, risk_probability, block_cod, risk_tier
        FROM transactions
        ORDER BY id DESC
        LIMIT 15
    """)
    recent_trend = [
        {"id": row["id"], "score": round(row["risk_probability"], 3), "tier": row["risk_tier"]}
        for row in reversed(cursor.fetchall())
    ]
    
    conn.close()
    return {
        "total_transactions": total_count,
        "blocked_cod_count": total_blocked,
        "block_rate_percent": block_rate,
        "avg_risk_score": avg_risk,
        "estimated_savings_inr": estimated_savings,
        "tier_distribution": {
            "LOW": tier_counts.get("LOW", 0),
            "MEDIUM": tier_counts.get("MEDIUM", 0),
            "HIGH": tier_counts.get("HIGH", 0),
            "CRITICAL": tier_counts.get("CRITICAL", 0)
        },
        "recent_trend": recent_trend
    }

init_db()
