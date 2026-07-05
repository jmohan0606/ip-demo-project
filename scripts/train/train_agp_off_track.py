"""Train the AGP_OFF_TRACK_RISK model (Section 11.1 §3). Re-runnable; prints real metrics."""
from app.ml.training.classifiers import train_agp_off_track

if __name__ == "__main__":
    train_agp_off_track()
