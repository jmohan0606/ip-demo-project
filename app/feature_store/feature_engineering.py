from __future__ import annotations

from collections import defaultdict
from app.feature_store.csv_loader import DemoCsvLoader
from app.models.features import FeatureEntityType, FeatureGroupName, FeatureVector


def _f(value, default=0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


class FeatureEngineeringPipeline:
    def __init__(self) -> None:
        self.loader = DemoCsvLoader()

    def advisor_growth_features(self) -> list[FeatureVector]:
        advisors = self.loader.read_csv("phx_dm_advisor.csv")
        txns = self.loader.read_csv("phx_dm_transaction.csv")
        advisor_household_edges = self.loader.read_csv("edges_phx_dm_advisor_serves_household.csv")

        revenue = defaultdict(float)
        managed = defaultdict(float)
        nnm = defaultdict(float)
        ncf = defaultdict(float)
        household_count = defaultdict(int)

        for edge in advisor_household_edges:
            household_count[edge["from_id"]] += 1

        for txn in txns:
            advisor_id = txn.get("advisor_id")
            revenue[advisor_id] += _f(txn.get("revenue_amount"))
            managed[advisor_id] += _f(txn.get("managed_revenue_amount"))
            nnm[advisor_id] += _f(txn.get("net_new_money_amount"))
            ncf[advisor_id] += _f(txn.get("net_cash_flow_amount"))

        vectors = []
        for advisor in advisors:
            advisor_id = advisor["advisor_id"]
            rev = revenue[advisor_id]
            man = managed[advisor_id]
            vectors.append(FeatureVector(
                entity_type=FeatureEntityType.ADVISOR,
                entity_id=advisor_id,
                feature_group=FeatureGroupName.ADVISOR_GROWTH,
                features={
                    "revenue_ltm": round(rev, 2),
                    "managed_revenue_ltm": round(man, 2),
                    "managed_revenue_pct": round((man / rev * 100) if rev else 0, 2),
                    "nnm_ltm": round(nnm[advisor_id], 2),
                    "ncf_ltm": round(ncf[advisor_id], 2),
                    "household_count": household_count[advisor_id],
                    "tenure_years": _f(advisor.get("tenure_years")),
                    "agp_enrolled": advisor.get("agp_enrolled") == "true",
                },
            ))
        return vectors

    def crm_activity_features(self) -> list[FeatureVector]:
        crm = self.loader.read_csv("phx_dm_crm_activity.csv")
        counts = defaultdict(lambda: defaultdict(int))
        for row in crm:
            advisor_id = row.get("advisor_id")
            activity_type = row.get("activity_type", "Unknown").lower().replace(" ", "_")
            counts[advisor_id]["crm_activity_count"] += 1
            counts[advisor_id][f"{activity_type}_count"] += 1

        return [
            FeatureVector(
                entity_type=FeatureEntityType.ADVISOR,
                entity_id=advisor_id,
                feature_group=FeatureGroupName.CRM_ACTIVITY,
                features=dict(features),
            )
            for advisor_id, features in counts.items()
        ]

    def agp_progress_features(self) -> list[FeatureVector]:
        goals = self.loader.read_csv("phx_dm_goal.csv")
        kpis = self.loader.read_csv("phx_dm_kpi.csv")
        grouped = defaultdict(lambda: {"goal_count": 0, "kpi_count": 0, "off_track_kpi_count": 0, "attainment_sum": 0.0})

        for goal in goals:
            grouped[goal.get("advisor_id")]["goal_count"] += 1

        for kpi in kpis:
            advisor_id = kpi.get("advisor_id")
            grouped[advisor_id]["kpi_count"] += 1
            grouped[advisor_id]["attainment_sum"] += _f(kpi.get("attainment_pct"))
            if kpi.get("on_track_flag") != "true":
                grouped[advisor_id]["off_track_kpi_count"] += 1

        vectors = []
        for advisor_id, features in grouped.items():
            kpi_count = features["kpi_count"] or 1
            features["avg_goal_attainment_pct"] = round(features["attainment_sum"] / kpi_count, 2)
            del features["attainment_sum"]
            vectors.append(FeatureVector(
                entity_type=FeatureEntityType.ADVISOR,
                entity_id=advisor_id,
                feature_group=FeatureGroupName.AGP_PROGRESS,
                features=dict(features),
            ))
        return vectors

    def household_opportunity_features(self) -> list[FeatureVector]:
        households = self.loader.read_csv("phx_dm_household.csv")
        vectors = []
        for h in households:
            aum = _f(h.get("total_aum"))
            cash = _f(h.get("cash_balance"))
            vectors.append(FeatureVector(
                entity_type=FeatureEntityType.HOUSEHOLD,
                entity_id=h["household_id"],
                feature_group=FeatureGroupName.HOUSEHOLD_OPPORTUNITY,
                features={
                    "household_aum": round(aum, 2),
                    "cash_balance": round(cash, 2),
                    "cash_to_aum_ratio": round((cash / aum) if aum else 0, 4),
                    "segment": h.get("segment"),
                    "risk_profile": h.get("risk_profile"),
                },
            ))
        return vectors

    def account_revenue_features(self) -> list[FeatureVector]:
        accounts = self.loader.read_csv("phx_dm_account.csv")
        vectors = []
        for a in accounts:
            vectors.append(FeatureVector(
                entity_type=FeatureEntityType.ACCOUNT,
                entity_id=a["account_id"],
                feature_group=FeatureGroupName.ACCOUNT_REVENUE,
                features={
                    "account_value": _f(a.get("account_value")),
                    "managed_flag": a.get("managed_flag") == "true",
                    "account_type": a.get("account_type"),
                },
            ))
        return vectors
