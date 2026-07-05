"""Train the HOUSEHOLD_CHURN_PROPENSITY model (Section 11.1 §3). Re-runnable; real metrics."""
from app.ml.training.classifiers import train_household_churn

if __name__ == "__main__":
    train_household_churn()
