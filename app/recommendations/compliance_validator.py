from __future__ import annotations

from app.models.recommendations import ComplianceStatus


class RecommendationComplianceValidator:
    """Simple demo compliance checks.

    Enterprise swap: replace this with firm policy validation rules and SMARTSDK tools.
    """

    BLOCKED_TERMS = ["guaranteed return", "risk free", "must buy", "certain profit"]

    def validate(self, action_text: str, rationale: str, evidence: list[str]) -> tuple[ComplianceStatus, list[str]]:
        warnings: list[str] = []
        lower = f"{action_text} {rationale}".lower()

        for term in self.BLOCKED_TERMS:
            if term in lower:
                return ComplianceStatus.BLOCKED, [f"Blocked unsupported claim: {term}"]

        if not evidence:
            warnings.append("No evidence supplied for recommendation.")

        if "suitability" not in lower and "risk profile" not in lower:
            warnings.append("Suitability/risk profile language should be reviewed.")

        if warnings:
            return ComplianceStatus.NEEDS_REVIEW, warnings

        return ComplianceStatus.PASSED, []
