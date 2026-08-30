"""HTTP delivery for personalized postcards."""

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.api.contracts import NOT_FOUND_RESPONSE, UNPROCESSABLE_RESPONSE
from app.core.security import require_user_id
from app.guardrails.runtime import rate_limit

from .models import PostcardListResponse, PostcardPrewarmResponse, PostcardResponse
from .service import (
    PostcardError,
    PostcardNotFoundError,
    PostcardSceneUnavailableError,
    postcard_service,
)

router = APIRouter(tags=["postcards"])


def _http_error(exc: Exception) -> None:
    if isinstance(exc, PostcardNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, PostcardSceneUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    if isinstance(exc, PostcardError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    raise exc


@router.get(
    "/api/v1/postcards",
    response_model=PostcardListResponse,
    summary="List all persisted postcards owned by the signed-in account",
)
def list_account_postcards(user_id: str = Depends(require_user_id)) -> PostcardListResponse:
    return PostcardListResponse(postcards=postcard_service.list_by_user(user_id))


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
    ai_scene: bool = Form(default=True),
    photo_style: str | None = Form(default=None),
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
            photo_style=photo_style,
        )
    except (PostcardNotFoundError, PostcardError) as exc:
        _http_error(exc)


@router.post(
    "/api/v1/trips/{trip_id}/postcards/prewarm",
    response_model=PostcardPrewarmResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={**NOT_FOUND_RESPONSE, **UNPROCESSABLE_RESPONSE},
    dependencies=[Depends(rate_limit("expensive"))],
    summary="Pre-generate a Qwen-Image scene after a stop visit is completed",
)
def prewarm_postcard_scene(
    trip_id: str,
    background_tasks: BackgroundTasks,
    poi_id: str = Form(min_length=1),
    language: str = Form(default="zh-CN"),
) -> PostcardPrewarmResponse:
    try:
        postcard_service.validate_scene_prewarm(trip_id, poi_id, language)
        background_tasks.add_task(postcard_service.prewarm_scene, trip_id, poi_id, language)
        return PostcardPrewarmResponse(trip_id=trip_id, poi_id=poi_id)
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
    response_model=bytes,
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


@router.get(
    "/api/v1/postcards/{postcard_id}/image.png",
    response_model=bytes,
    responses={**NOT_FOUND_RESPONSE, **UNPROCESSABLE_RESPONSE},
    summary="Download a rendered postcard PNG",
)
def postcard_image_png(postcard_id: str) -> Response:
    try:
        return Response(
            content=postcard_service.image_png(postcard_id),
            media_type="image/png",
            headers={
                "Cache-Control": "private, max-age=86400",
                "Content-Disposition": f'attachment; filename="macau-postcard-{postcard_id}.png"',
            },
        )
    except (PostcardNotFoundError, PostcardError) as exc:
        _http_error(exc)
