"""Train GraphSAGE embeddings (Section 11.1 §7, Tier 2). Prints held-out link-pred ROC-AUC."""
from app.ml.gnn import train_gnn

if __name__ == "__main__":
    train_gnn()
