from __future__ import annotations

from app.runtime_validation.runtime_validator import FinalRuntimeValidator


class RuntimeValidationService:
    def run(self) -> dict:
        return FinalRuntimeValidator(".").write_report()
