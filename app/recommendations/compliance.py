from __future__ import annotations


class ComplianceService:
    def validate(self, recommendation: dict) -> dict:
        title = recommendation.get("title", "")
        review_required = "NNM" in title or "Recovery" in title
        return {
            "status": "Review Required" if review_required else "Passed",
            "rules": [
                {"rule": "Suitability context required", "status": "Passed"},
                {"rule": "No promissory language", "status": "Passed"},
                {"rule": "Review required for recovery messaging", "status": "Review Required" if review_required else "Passed"},
            ],
        }
