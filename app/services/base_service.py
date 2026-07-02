from __future__ import annotations
from app.models.common import ServiceResponse


class BaseService:
    service_name = "base_service"

    def ok(self, data=None, message: str | None = None) -> ServiceResponse:
        return ServiceResponse(success=True, data=data, message=message)

    def fail(self, message: str, warnings: list[str] | None = None) -> ServiceResponse:
        return ServiceResponse(success=False, message=message, warnings=warnings or [])
