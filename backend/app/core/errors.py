"""One error type for business rules, rendered as {"detail": ..., "code": ...} with a real HTTP status."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")

_STATUS_CODES = {
    400: "VALIDATION_ERROR",
    401: "AUTH_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "FILE_TOO_LARGE",
    415: "INVALID_FILE_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    503: "MAINTENANCE",
}


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def bad_request(message: str, code: str = "VALIDATION_ERROR") -> AppError:
    return AppError(400, code, message)


def unauthorized(message: str = "Please sign in again.", code: str = "AUTH_REQUIRED") -> AppError:
    return AppError(401, code, message)


def forbidden(message: str = "You do not have permission to do that.", code: str = "FORBIDDEN") -> AppError:
    return AppError(403, code, message)


def not_found(message: str = "Not found.") -> AppError:
    return AppError(404, "NOT_FOUND", message)


def conflict(message: str, code: str = "DUPLICATE") -> AppError:
    return AppError(409, code, message)


def _payload(message: str, code: str, **extra) -> dict:
    return {"detail": message, "code": code, **extra}


def _readable(error: dict) -> str:
    message = str(error.get("msg", "Invalid value."))
    if error.get("type") == "value_error":  # our own validators already speak to the user
        return message.removeprefix("Value error, ")
    field = ".".join(str(part) for part in error.get("loc", ()) if part not in ("body", "query", "path"))
    return f"{field}: {message}" if field else message


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=_payload(exc.message, exc.code))

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError):
        errors = exc.errors()
        message = _readable(errors[0]) if errors else "Invalid request."
        details = [{"loc": list(e.get("loc", ())), "msg": str(e.get("msg", ""))} for e in errors]
        return JSONResponse(status_code=400, content=_payload(message, "VALIDATION_ERROR", errors=details))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_: Request, exc: StarletteHTTPException):
        code = _STATUS_CODES.get(exc.status_code, "ERROR")
        return JSONResponse(status_code=exc.status_code, content=_payload(str(exc.detail), code))

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500, content=_payload("Something went wrong. Please try again.", "SERVER_ERROR")
        )
