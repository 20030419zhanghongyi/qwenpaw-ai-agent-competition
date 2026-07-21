"""HTTP delivery for personalized postcards."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.api.contracts import NOT_FOUND_RESPONSE, UNPROCESSABLE_RESPONSE
from app.guardrails.runtime import rate_limit

from .models import PostcardListResponse, PostcardResponse
from .service import PostcardError, PostcardNotFoundError, postcard_service

router = APIRouter(tags=["postcards"])


def _http_error(exc: Exception) -> None:
    if isinstance(exc, PostcardNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, PostcardError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    raise exc


@router.post(
    "/api/v1/trips/{trip_id}/postcards",
    response_model=PostcardResponse,
    status_code=status.HTTP_201_CREATED,
    responses={**NOT_FOUND_RESPONSE, **UNPROCESSABLE_RESPONSE},
    dependencies=[Depends(rate_limit("expensive"))],
    summary="Create a privacy-scrubbed personalized postcard from a completed check-in",
)
def create_postcard(
    trip_id: str,
    poi_id: str = Form(min_length=1),
    photo: UploadFile | None = File(default=None),
    language: str = Form(default="zh-CN"),
    replace: bool = Form(default=False),
    ai_scene: bool = Form(default=False),
) -> PostcardResponse:
    try:
        photo_bytes = photo.file.read() if photo is not None else b""
        return postcard_service.create(
            trip_id,
            poi_id,
            photo_bytes or None,
            language,
            replace=replace,
            ai_scene=ai_scene,
        )
    except (PostcardNotFoundError, PostcardError) as exc:
        _http_error(exc)


@router.get(
    "/api/v1/trips/{trip_id}/postcards",
    response_model=PostcardListResponse,
    responses=NOT_FOUND_RESPONSE,
    summary="List trip postcards in route order",
)
def list_postcards(trip_id: str) -> PostcardListResponse:
    try:
        return PostcardListResponse(postcards=postcard_service.list_by_trip(trip_id))
    except PostcardNotFoundError as exc:
        _http_error(exc)


@router.delete(
    "/api/v1/postcards/{postcard_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND_RESPONSE,
    summary="Delete a generated postcard so it can be recreated",
)
def delete_postcard(postcard_id: str) -> Response:
    try:
        postcard_service.delete(postcard_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except PostcardNotFoundError as exc:
        _http_error(exc)


@router.get(
    "/api/v1/postcards/{postcard_id}/image",
    responses=NOT_FOUND_RESPONSE,
    summary="Fetch a rendered postcard SVG",
)
def postcard_image(postcard_id: str) -> Response:
    try:
        return Response(
            content=postcard_service.image(postcard_id),
            media_type="image/svg+xml",
            headers={"Cache-Control": "private, max-age=86400"},
        )
    except PostcardNotFoundError as exc:
        _http_error(exc)
