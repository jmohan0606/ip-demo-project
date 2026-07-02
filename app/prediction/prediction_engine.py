from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler

from app.models.predictions import PredictionLabel, PredictionRecord, PredictionType
from app.shared.ids import timestamp_id


class LocalPredictionEngine:
    def __init__(self) -> None:
        self.model_name = "sklearn_local_demo_model"
        self.model_version = "1.0"

    def _features(self, df: pd.DataFrame) -> list[str]:
        return [c for c in df.columns if c != "entity_id"]

    def _label(self, score: float, risk_mode: bool = False) -> str:
        if risk_mode:
            if score >= 0.70:
                return PredictionLabel.AT_RISK.value
            if score >= 0.40:
                return PredictionLabel.MEDIUM.value
            return PredictionLabel.ON_TRACK.value
        if score >= 0.70:
            return PredictionLabel.HIGH.value
        if score >= 0.40:
            return PredictionLabel.MEDIUM.value
        return PredictionLabel.LOW.value

    def _synthetic_target(self, df: pd.DataFrame, prediction_type: PredictionType) -> np.ndarray:
        rev = df.get("revenue_ltm", 0)
        nnm = df.get("nnm_ltm", 0)
        managed_pct = df.get("managed_revenue_pct", 0)
        crm = df.get("crm_activity_count", 0)
        off_track = df.get("off_track_kpi_count", 0)
        attainment = df.get("avg_goal_attainment_pct", 0)

        if prediction_type == PredictionType.REVENUE_GROWTH:
            y = rev.rank(pct=True) * 0.55 + managed_pct.rank(pct=True) * 0.25 + crm.rank(pct=True) * 0.20
        elif prediction_type == PredictionType.NNM_GROWTH:
            y = nnm.rank(pct=True) * 0.70 + crm.rank(pct=True) * 0.20 + managed_pct.rank(pct=True) * 0.10
        elif prediction_type == PredictionType.AUM_GROWTH:
            y = rev.rank(pct=True) * 0.35 + nnm.rank(pct=True) * 0.35 + managed_pct.rank(pct=True) * 0.30
        elif prediction_type == PredictionType.AGP_GOAL_RISK:
            y = (off_track.rank(pct=True) * 0.55) + ((100 - attainment).rank(pct=True) * 0.35) + ((crm.max() - crm).rank(pct=True) * 0.10)
        elif prediction_type == PredictionType.ADVISOR_SUCCESS:
            y = rev.rank(pct=True) * 0.30 + nnm.rank(pct=True) * 0.25 + managed_pct.rank(pct=True) * 0.20 + crm.rank(pct=True) * 0.15 + attainment.rank(pct=True) * 0.10
        else:
            y = managed_pct.rank(pct=True) * 0.35 + crm.rank(pct=True) * 0.25 + nnm.rank(pct=True) * 0.25 + rev.rank(pct=True) * 0.15

        return np.nan_to_num(np.asarray(y, dtype=float), nan=0.0)

    def predict(self, df: pd.DataFrame, prediction_type: PredictionType) -> tuple[list[PredictionRecord], dict]:
        if df.empty:
            return [], {"model_name": self.model_name, "records": 0}

        feature_cols = self._features(df)
        x = df[feature_cols].replace([np.inf, -np.inf], 0).fillna(0)
        y = self._synthetic_target(df, prediction_type)

        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x)

        if prediction_type == PredictionType.AGP_GOAL_RISK:
            target = (y > 0.55).astype(int)
            model = RandomForestClassifier(n_estimators=30, random_state=42, max_depth=6)
            model.fit(x_scaled, target)
            scores = model.predict_proba(x_scaled)[:, 1]
            risk_mode = True
            model_type = "RandomForestClassifier"
        else:
            model = RandomForestRegressor(n_estimators=30, random_state=42, max_depth=6)
            model.fit(x_scaled, y)
            scores = model.predict(x_scaled)
            scores = np.clip(scores, 0, 1)
            risk_mode = False
            model_type = "RandomForestRegressor"

        records: list[PredictionRecord] = []
        for idx, row in df.iterrows():
            score = float(scores[idx])
            features = {col: row[col] for col in feature_cols}
            explanation = self._explanation(prediction_type, features, score)
            records.append(PredictionRecord(
                prediction_id=timestamp_id("pred"),
                entity_id=row["entity_id"],
                prediction_type=prediction_type,
                score=round(score, 6),
                label=self._label(score, risk_mode),
                model_name=self.model_name,
                model_version=self.model_version,
                confidence=round(0.65 + min(0.30, abs(score - 0.5)), 4),
                explanation=explanation,
                feature_snapshot=features,
            ))

        metadata = {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "model_type": model_type,
            "prediction_type": prediction_type.value,
            "records": len(records),
            "features": feature_cols,
        }
        return records, metadata

    def _explanation(self, prediction_type: PredictionType, features: dict, score: float) -> str:
        parts = []
        if features.get("revenue_ltm", 0) > 0:
            parts.append(f"Revenue signal={round(features.get('revenue_ltm', 0), 2)}")
        if "managed_revenue_pct" in features:
            parts.append(f"managed revenue pct={round(features.get('managed_revenue_pct', 0), 2)}")
        if "crm_activity_count" in features:
            parts.append(f"CRM activity={features.get('crm_activity_count')}")
        if "off_track_kpi_count" in features:
            parts.append(f"off-track KPIs={features.get('off_track_kpi_count')}")
        return f"{prediction_type.value} score {round(score, 3)} based on " + ", ".join(parts[:4])
