from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.shared.exceptions import ConfigurationError, IPerformError, NotFoundError, ValidationError
from app.shared.logging import logger

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ConfigurationError)
    async def configuration_error_handler(request: Request, exc: ConfigurationError):
        logger.warning(f"Configuration error: {exc}"); return JSONResponse(status_code=400, content={"success": False, "message": str(exc)})
    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        logger.warning(f"Validation error: {exc}"); return JSONResponse(status_code=422, content={"success": False, "message": str(exc)})
    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request: Request, exc: NotFoundError):
        logger.warning(f"Not found: {exc}"); return JSONResponse(status_code=404, content={"success": False, "message": str(exc)})
    @app.exception_handler(IPerformError)
    async def iperform_error_handler(request: Request, exc: IPerformError):
        logger.warning(f"Application error: {exc}"); return JSONResponse(status_code=400, content={"success": False, "message": str(exc)})
    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled error: {exc}"); return JSONResponse(status_code=500, content={"success": False, "message": "Unexpected server error"})
