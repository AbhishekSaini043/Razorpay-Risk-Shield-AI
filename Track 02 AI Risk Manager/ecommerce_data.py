import pandas as pd
import numpy as np

# Generate 5000 synthetic transactions
np.random.seed(42)
n = 5000

data = {
    "transaction_amount": np.random.uniform(500, 15000, n),
    "user_history_returns": np.random.poisson(1.5, n),
    "item_category_risk": np.random.uniform(0.1, 0.9, n),
    "delivery_distance_km": np.random.uniform(5, 500, n),
    "is_cod": np.random.choice([0, 1], n, p=[0.4, 0.6]),
}
df = pd.DataFrame(data)

# Define the target variable (will_return) based on features
risk_score = (df.user_history_returns * 0.3) + (df.is_cod * 0.5) + (df.item_category_risk * 0.8)
df['will_return'] = (risk_score + np.random.normal(0, 0.5, n) > 1.5).astype(int)

df.to_csv("ecommerce_returns.csv", index=False)
print("Synthetic data generated: ecommerce_returns.csv")