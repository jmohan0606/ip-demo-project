"""Train the REVENUE_DECLINE_RISK model (Section 11.1 §3). Re-runnable; prints real metrics."""
from app.ml.training.classifiers import train_revenue_decline

if __name__ == "__main__":
    train_revenue_decline()
