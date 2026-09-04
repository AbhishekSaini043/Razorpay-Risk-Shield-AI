# Razorpay-Risk-Shield-AI
# Razorpay AI Risk Manager Pro

An enterprise fraud intelligence platform designed to predict e-commerce return probabilities and dynamically gate Cash on Delivery (COD) transactions. Built for Track 02 of the Razorpay AI Buildathon, this microservice protects merchant profit margins by blocking high-risk orders before dispatch, saving an estimated ₹800 in reverse freight per prevented return.

## Core Architecture

* **Machine Learning Brain:** Utilizes a predictive classification model trained on synthesized e-commerce data, evaluating user return history, item category risk, delivery distance, and transaction amount.


* **Explainable AI (XAI):** Generates human-readable audit factors for every decision (e.g., "+30% Risk for High Return Category") instead of outputting an unexplainable black-box score.


* **Tiered Action Flow:** Categorizes transactions into LOW (Allow COD), MEDIUM (Verify OTP), HIGH (Require Advance), and CRITICAL (Block COD) tiers.


* **Audit Logging:** An embedded SQLite database securely records every evaluated transaction, the exact threshold used, and the corresponding XAI factors for full financial transparency.


* **Graceful Failure Recovery:** If the ML model fails to load or corrupts, the API instantly triggers a safety fallback mode, defaulting to ALLOW_COD so the merchant's checkout flow never crashes.



## Razorpay Buildathon Rubric Alignment

| Rubric Criteria | Implementation Proof |
| --- | --- |
| **Problem Taste** | Solves the massive margin-drain of COD returns, which have a 3.4x higher refusal probability at the delivery doorstep.

 |
| **Build Quality** | Deployed as a fully containerized FastAPI microservice with automated database seeding and robust exception handling.

 |
| **AI Judgment** | Relies on deterministic predictive analytics and data mining over Generative AI, guaranteeing split-second speed, mathematically bounded risk, and strict explainability.

 |
| **Failure Recovery** | Built-in `MODEL_LOADED` boolean check catches unhandled model exceptions and falls back to frictionless checkout.

 |

## Honest Metrics & Evaluation

The model operates on a mathematically optimized threshold of **0.22** to maximize net business profit.

* **Precision:** 0.484


* **Recall:** 0.867


* **ROC-AUC:** 0.835


* **Net Business Value:** The optimal threshold is calculated by weighing the cost of a false positive (₹200 lost profit margin) against the savings of a true positive (₹800 reverse logistics saving).



## Local Installation (Docker)

This project is fully containerized for zero-dependency execution.

```bash
# 1. Build the container image (this will automatically train the model and setup the DB)
docker build -t risk-manager-api .

# 2. Run the microservice
docker run -p 8000:8000 risk-manager-api

```

## Core API Endpoints

* `POST /score-risk` : Evaluate a single transaction payload and return the probability, risk tier, and XAI factors.


* `POST /score-risk/batch` : Process an array of JSON transactions in a single high-throughput request.


* `POST /score-risk/upload-csv` : Upload a raw CSV for bulk evaluation and margin-saving estimations.


* `GET /api/analytics` : Retrieve a portfolio executive summary of blocked COD counts, total transactions, and estimated INR savings.


* `GET /api/health` : Check the microservice status and model loading state.
