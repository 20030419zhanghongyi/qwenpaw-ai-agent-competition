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
    photo: UploadFile = File(),
    language: str = Form(default="zh-CN"),
) -> PostcardResponse:
    try:
        return postcard_service.create(trip_id, poi_id, photo.file.read(), language)
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
