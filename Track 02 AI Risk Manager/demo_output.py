import json
import urllib.request

def get_json(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def post_json(url, data):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

print("=" * 72)
print("              RAZORPAY RISK SHIELD AI - LIVE EVALUATION OUTPUT           ")
print("=" * 72)

# 1. System Health
health = get_json("http://127.0.0.1:8000/api/health")
print(f"1. MICROSERVICE STATUS: {health['status'].upper()}")
print(f"   Model Loaded: {health['model_loaded']} | Optimal Business Cutoff: {int(health['optimal_threshold']*100)}%\n")

# 2. Scenarios
scenarios = [
    {
        "title": "SCENARIO A: CHRONIC RETURN FRAUD (High Risk Consignment)",
        "payload": {"transaction_amount": 7800.0, "user_history_returns": 5, "item_category_risk": 0.85, "delivery_distance_km": 420.0, "is_cod": 1}
    },
    {
        "title": "SCENARIO B: VERIFICATION CANDIDATE (Moderate Risk)",
        "payload": {"transaction_amount": 2800.0, "user_history_returns": 2, "item_category_risk": 0.50, "delivery_distance_km": 150.0, "is_cod": 1}
    },
    {
        "title": "SCENARIO C: TRUSTED PREPAID BUYER (Safe Frictionless)",
        "payload": {"transaction_amount": 1400.0, "user_history_returns": 0, "item_category_risk": 0.20, "delivery_distance_km": 15.0, "is_cod": 0}
    }
]

for sc in scenarios:
    res = post_json("http://127.0.0.1:8000/score-risk", sc["payload"])
    p = sc["payload"]
    print("-" * 72)
    print(f">> {sc['title']}")
    print(f"   Inputs: Cart: Rs. {p['transaction_amount']:,.0f} | Returns: {p['user_history_returns']} | Cat Risk: {p['item_category_risk']} | Dist: {p['delivery_distance_km']}km | COD: {bool(p['is_cod'])}")
    print(f"   * Return Probability : {int(res['risk_probability']*100)}%")
    print(f"   * Risk Tier          : {res['risk_tier']}")
    print(f"   * Action Recommended : {res['recommendation']}")
    print(f"   * COD Restricted?    : {'YES (Prepaid Only)' if res['block_cod'] else 'NO (Allow COD)'}")
    print(f"   * Savings Estimate   : Rs. {res['savings_estimate_inr']}")
    print("   * Explainable AI (XAI) Drivers:")
    for f in res.get("top_factors", []):
        print(f"       [{f['impact']}] {f['factor']}: {f['detail']}")
    print()

# 3. Portfolio Analytics
analytics = get_json("http://127.0.0.1:8000/api/analytics")
print("=" * 72)
print("                 PORTFOLIO EXECUTIVE ANALYTICS SUMMARY                  ")
print("=" * 72)
print(f"Total Transactions Scored   : {analytics['total_transactions']}")
print(f"COD Block Rate              : {analytics['block_rate_percent']}% ({analytics['blocked_cod_count']} orders flagged)")
print(f"Total Reverse Freight Saved : Rs. {analytics['estimated_savings_inr']:,}")
print(f"Risk Tier Distribution      : {analytics['tier_distribution']}")
print("=" * 72)
