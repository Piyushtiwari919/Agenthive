from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AgentHiveError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "AGENTHIVE_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class DatabaseUnavailableError(AgentHiveError):
    """Raised when FalkorDB is unreachable (enforces C-01 / K-09 fail-closed behavior)."""

    def __init__(self, message: str = "FalkorDB primary graph database is unavailable.") -> None:
        super().__init__(
            message=message,
            code="FALKORDB_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class TenantAccessDeniedError(AgentHiveError):
    """Raised when tenant resolution or authorization fails (BR-001, FR-014)."""

    def __init__(
        self,
        message: str = "Tenant scope invalid or unauthorized.",
        status_code: int = status.HTTP_403_FORBIDDEN,
    ) -> None:
        super().__init__(
            message=message,
            code="TENANT_ACCESS_DENIED",
            status_code=status_code,
        )


class ResourceNotFoundError(AgentHiveError):
    """Raised when an entity, episode, procedure, agent, or handoff does not exist in the resolved tenant."""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        super().__init__(
            message=f"{resource_type} '{resource_id}' not found in the active tenant scope.",
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource_type": resource_type, "resource_id": resource_id},
        )


class ConflictStateError(AgentHiveError):
    """Raised on invalid state transitions or duplicate non-idempotent conflicts."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            code="STATE_CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
        )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AgentHiveError)
    async def handle_agenthive_error(request: Request, exc: AgentHiveError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": request_id,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        safe_errors = []
        for err in exc.errors():
            safe_errors.append(
                {
                    "loc": [str(x) for x in err.get("loc", [])],
                    "msg": err.get("msg", "Invalid value"),
                    "type": err.get("type", "value_error"),
                }
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request payload failed schema validation.",
                    "details": {"errors": safe_errors},
                    "request_id": request_id,
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal error occurred.",
                    "details": {"category": exc.__class__.__name__},
                    "request_id": request_id,
                }
            },
        )