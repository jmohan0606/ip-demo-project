"""Train the revenue-forecast GRU (Section 11.1 §5). Re-runnable; prints real sMAPE vs baselines."""
from app.ml.training.forecast import train_revenue_forecast

if __name__ == "__main__":
    train_revenue_forecast()
