"""Authenticated memoir editing and public privacy-filtered sharing endpoints."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.core.security import require_user_id

from .models import (
    MemoirCreateRequest, MemoirPhotoResponse, MemoirResponse, MemoirUpdateRequest,
    SharePrivacy, ShareResponse, SharedMemoirResponse,
)
from .service import (
    MemoirForbiddenError, MemoirNotFoundError, MemoirValidationError, memoir_service,
)

router = APIRouter(tags=["memoirs"])


def _raise(exc: Exception) -> None:
    if isinstance(exc, MemoirForbiddenError):
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if isinstance(exc, MemoirNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, MemoirValidationError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise exc


@router.post("/api/v1/trips/{trip_id}/memoir", response_model=MemoirResponse, status_code=201)
def create_memoir(
    trip_id: str, request: MemoirCreateRequest, user_id: str = Depends(require_user_id)
) -> MemoirResponse:
    try:
        return memoir_service.create(trip_id, user_id, request)
    except (MemoirForbiddenError, MemoirNotFoundError, MemoirValidationError) as exc:
        _raise(exc)


@router.get("/api/v1/trips/{trip_id}/memoir", response_model=MemoirResponse)
def get_trip_memoir(trip_id: str, user_id: str = Depends(require_user_id)) -> MemoirResponse:
    try:
        return memoir_service.get_by_trip(trip_id, user_id)
    except (MemoirForbiddenError, MemoirNotFoundError) as exc:
        _raise(exc)


@router.get("/api/v1/memoirs/{memoir_id}", response_model=MemoirResponse)
def get_memoir(memoir_id: str, user_id: str = Depends(require_user_id)) -> MemoirResponse:
    try:
        return memoir_service.get(memoir_id, user_id)
    except (MemoirForbiddenError, MemoirNotFoundError) as exc:
        _raise(exc)


@router.put("/api/v1/memoirs/{memoir_id}", response_model=MemoirResponse)
def update_memoir(
    memoir_id: str, request: MemoirUpdateRequest, user_id: str = Depends(require_user_id)
) -> MemoirResponse:
    try:
        return memoir_service.update(memoir_id, user_id, request)
    except (MemoirForbiddenError, MemoirNotFoundError, MemoirValidationError) as exc:
        _raise(exc)


@router.post(
    "/api/v1/memoirs/{memoir_id}/photos",
    response_model=MemoirPhotoResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_photo(
    memoir_id: str,
    photo: UploadFile = File(),
    poi_id: str | None = Form(default=None),
    has_people: bool = Form(default=False),
    user_id: str = Depends(require_user_id),
) -> MemoirPhotoResponse:
    try:
        return memoir_service.add_photo(
            memoir_id, user_id, data=photo.file.read(), filename=photo.filename or "travel-photo",
            content_type=photo.content_type or "application/octet-stream", poi_id=poi_id,
            has_people=has_people,
        )
    except (MemoirForbiddenError, MemoirNotFoundError, MemoirValidationError) as exc:
        _raise(exc)


@router.get("/api/v1/memoirs/{memoir_id}/photos/{photo_id}", response_model=bytes)
def get_photo(
    memoir_id: str, photo_id: str, user_id: str = Depends(require_user_id)
) -> Response:
    try:
        photo = memoir_service.photo(memoir_id, photo_id, user_id)
        return Response(photo.image_data, media_type=photo.content_type, headers={"Cache-Control": "private"})
    except (MemoirForbiddenError, MemoirNotFoundError) as exc:
        _raise(exc)


@router.delete("/api/v1/memoirs/{memoir_id}/photos/{photo_id}", status_code=204)
def delete_photo(
    memoir_id: str, photo_id: str, user_id: str = Depends(require_user_id)
) -> Response:
    try:
        memoir_service.delete_photo(memoir_id, photo_id, user_id)
        return Response(status_code=204)
    except (MemoirForbiddenError, MemoirNotFoundError) as exc:
        _raise(exc)


@router.post("/api/v1/memoirs/{memoir_id}/shares", response_model=ShareResponse, status_code=201)
def create_share(
    memoir_id: str, privacy: SharePrivacy, user_id: str = Depends(require_user_id)
) -> ShareResponse:
    try:
        share = memoir_service.create_share(memoir_id, user_id, privacy)
        return ShareResponse(
            token=share.token, share_url=f"/shared/memoirs/{share.token}", privacy=privacy
        )
    except (MemoirForbiddenError, MemoirNotFoundError) as exc:
        _raise(exc)


@router.delete("/api/v1/memoirs/{memoir_id}/shares", status_code=204)
def revoke_share(memoir_id: str, user_id: str = Depends(require_user_id)) -> Response:
    try:
        memoir_service.revoke_share(memoir_id, user_id)
        return Response(status_code=204)
    except (MemoirForbiddenError, MemoirNotFoundError) as exc:
        _raise(exc)


@router.get("/api/v1/shared/memoirs/{token}", response_model=SharedMemoirResponse)
def shared_memoir(token: str) -> SharedMemoirResponse:
    try:
        return memoir_service.shared(token)
    except MemoirNotFoundError as exc:
        _raise(exc)


@router.get("/api/v1/shared/memoirs/{token}/photos/{photo_id}", response_model=bytes)
def shared_photo(token: str, photo_id: str) -> Response:
    try:
        photo = memoir_service.shared_photo(token, photo_id)
        return Response(photo.image_data, media_type=photo.content_type, headers={"Cache-Control": "public, max-age=3600"})
    except MemoirNotFoundError as exc:
        _raise(exc)
