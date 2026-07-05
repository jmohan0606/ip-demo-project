"""Train every Section 11.1 model in sequence and print a registry summary.

Re-runnable end to end; each trainer writes its artifact + registry entry and asserts the
anchored A001 figures are intact. Extended as later commits add the forecast/GNN/anomaly
models.
"""
import json

from app.ml import registry
from app.ml.training.classifiers import (
    train_agp_off_track,
    train_household_churn,
    train_revenue_decline,
)

TRAINERS = [
    ("revenue-decline-xgb", train_revenue_decline),
    ("household-churn-xgb", train_household_churn),
    ("agp-off-track-xgb", train_agp_off_track),
]

if __name__ == "__main__":
    for name, fn in TRAINERS:
        print(f"\n### training {name} ...")
        fn()

    print(f"\n{'='*72}\nREGISTRY SUMMARY\n{'='*72}")
    for e in registry.list_entries():
        print(f"  {e['name']:24} {e['algorithm']:38} "
              f"{e['primary_metric']}={e['primary_metric_value']} gate={e['quality_gate']}")
    print("\nFull registry: models/registry.json")
