"""Shared OpenAPI response contracts."""

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str | list[dict[str, Any]]


NOT_FOUND_RESPONSE = {
    404: {"model": ErrorResponse, "description": "Requested resource was not found."}
}
CONFLICT_RESPONSE = {
    409: {"model": ErrorResponse, "description": "Resource state conflicts with the request."}
}
UNPROCESSABLE_RESPONSE = {
    422: {
        "model": ErrorResponse,
        "description": "Request validation or business validation failed.",
    }
}
