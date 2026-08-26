"""Memoir composition, ownership checks, and privacy projection."""

from app.db.models import MemoirPhoto, TravelMemoir
from app.db.session import SessionLocal
from app.features.pois.repository import PoiRepository
from app.features.postcards.service import postcard_service
from app.features.trips.repository import trip_repository

from .models import (
    MemoirChapter,
    MemoirCreateRequest,
    MemoirPhotoResponse,
    MemoirResponse,
    MemoirUpdateRequest,
    SharePrivacy,
    SharedMemoirResponse,
)
from .repository import memoir_repository


class MemoirError(RuntimeError):
    pass


class MemoirNotFoundError(MemoirError):
    pass


class MemoirForbiddenError(MemoirError):
    pass


class MemoirValidationError(MemoirError):
    pass


STYLE_COPY = {
    "zh-CN": {
        "title": "我的澳门旅行回忆",
        "intro": "这本回忆录按照真实打卡顺序，记录这次澳门旅程。",
        "closing": "旅程在这里告一段落，留下的是亲自走过的地点与保存下来的片段。",
        "diary": "我来到了{name}。这是本次旅程的第{number}个打卡地点。",
        "magazine": "第{number}站 · {name}。这一章节依据实际到访记录整理。",
        "social": "第{number}站，打卡{name}。",
        "documentary": "行程记录来到第{number}站：{name}。",
    },
    "zh-TW": {
        "title": "我的澳門旅行回憶",
        "intro": "這本回憶錄按照真實打卡順序，記錄這次澳門旅程。",
        "closing": "旅程在這裡告一段落，留下的是親自走過的地點與保存下來的片段。",
        "diary": "我來到了{name}。這是本次旅程的第{number}個打卡地點。",
        "magazine": "第{number}站 · {name}。這一章節依據實際到訪記錄整理。",
        "social": "第{number}站，打卡{name}。",
        "documentary": "行程記錄來到第{number}站：{name}。",
    },
    "en": {
        "title": "My Macau Travel Memoir",
        "intro": "This memoir follows the verified check-in order of my Macau trip.",
        "closing": "The route ends here, leaving a record of the places I visited and saved.",
        "diary": "I arrived at {name}, the {number} stop recorded on this trip.",
        "magazine": "Stop {number} · {name}. This chapter is assembled from the recorded visit.",
        "social": "Stop {number}: checked in at {name}.",
        "documentary": "The recorded journey reaches stop {number}: {name}.",
    },
    "pt": {
        "title": "As minhas memórias de Macau",
        "intro": "Estas memórias seguem a ordem real dos check-ins da viagem a Macau.",
        "closing": "O percurso termina aqui, deixando o registo dos lugares visitados.",
        "diary": "Cheguei a {name}, a {number}.ª paragem registada nesta viagem.",
        "magazine": "Paragem {number} · {name}. Este capítulo baseia-se na visita registada.",
        "social": "Paragem {number}: check-in em {name}.",
        "documentary": "A viagem registada chega à paragem {number}: {name}.",
    },
}


class MemoirService:
    @staticmethod
    def _copy(language: str) -> dict[str, str]:
        return STYLE_COPY.get(language, STYLE_COPY["zh-CN"])

    @staticmethod
    def _owned(record: TravelMemoir | None, user_id: str) -> TravelMemoir:
        if record is None:
            raise MemoirNotFoundError("Memoir not found")
        if record.user_id != user_id:
            raise MemoirForbiddenError("This memoir belongs to another user")
        return record

    @staticmethod
    def _photo_response(photo: MemoirPhoto, *, shared_token: str | None = None) -> MemoirPhotoResponse:
        path = (
            f"/api/v1/shared/memoirs/{shared_token}/photos/{photo.id}"
            if shared_token
            else f"/api/v1/memoirs/{photo.memoir_id}/photos/{photo.id}"
        )
        return MemoirPhotoResponse(
            photo_id=photo.id,
            poi_id=photo.poi_id,
            filename=photo.filename,
            content_type=photo.content_type,
            has_people=photo.has_people,
            image_url=path,
            created_at=photo.created_at,
        )

    @staticmethod
    def _postcards(trip_id: str) -> dict[str, object]:
        try:
            return {card.poi_id: card for card in postcard_service.list_by_trip(trip_id)}
        except Exception:
            return {}

    def _chapters(self, record: TravelMemoir) -> list[MemoirChapter]:
        postcards = self._postcards(record.trip_id)
        result: list[MemoirChapter] = []
        for raw in record.chapters or []:
            chapter = MemoirChapter.model_validate(raw)
            card = postcards.get(chapter.poi_id)
            if card is not None:
                chapter.postcard_id = card.postcard_id
                chapter.postcard_caption = card.caption
                chapter.postcard_image_url = card.image_url
            result.append(chapter)
        return result

    def _sync_checked_in_chapters(self, record: TravelMemoir) -> TravelMemoir:
        """Append newly checked-in POIs without overwriting edited memoir chapters."""
        trip = trip_repository.get_trip(record.trip_id)
        if trip is None:
            raise MemoirNotFoundError("Trip not found")
        existing_ids = {chapter.get("poi_id") for chapter in (record.chapters or [])}
        missing_ids = [poi_id for poi_id in trip.checked_in_poi_ids if poi_id not in existing_ids]
        if not missing_ids:
            return record

        with SessionLocal() as session:
            poi_map = PoiRepository(session).get_by_ids(missing_ids)
        copy = self._copy(record.language)
        chapters = list(record.chapters or [])
        for poi_id in missing_ids:
            order = trip.checked_in_poi_ids.index(poi_id)
            name = poi_map[poi_id].poi_name if poi_id in poi_map else poi_id
            chapters.append(
                MemoirChapter(
                    poi_id=poi_id,
                    poi_name=name,
                    stop_order=order,
                    body=copy[record.style].format(name=name, number=order + 1),
                ).model_dump()
            )
        updated = memoir_repository.update(record.id, {"chapters": chapters})
        return self._owned(updated, record.user_id)

    def _response(self, record: TravelMemoir) -> MemoirResponse:
        trip = trip_repository.get_trip(record.trip_id)
        if trip is None:
            raise MemoirNotFoundError("Trip not found")
        active_share = next(
            (share.token for share in sorted(record.shares, key=lambda item: item.created_at, reverse=True)
             if share.revoked_at is None),
            None,
        )
        return MemoirResponse(
            memoir_id=record.id,
            trip_id=record.trip_id,
            user_id=record.user_id,
            route_id=trip.route_id,
            trip_status=trip.status.value,
            travel_date=trip.created_at,
            title=record.title,
            style=record.style,
            language=record.language,
            introduction=record.introduction,
            closing=record.closing,
            status=record.status,
            chapters=self._chapters(record),
            photos=[self._photo_response(photo) for photo in record.photos],
            cover_photo_id=record.cover_photo_id,
            active_share_token=active_share,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def create(self, trip_id: str, user_id: str, request: MemoirCreateRequest) -> MemoirResponse:
        trip = trip_repository.get_trip(trip_id)
        if trip is None:
            raise MemoirNotFoundError("Trip not found")
        if trip.user_id != user_id:
            raise MemoirForbiddenError("This trip belongs to another user")
        if not trip.checked_in_poi_ids:
            raise MemoirValidationError("At least one check-in is required")
        existing = memoir_repository.get_by_trip(trip_id)
        if existing is not None:
            owned = self._owned(existing, user_id)
            return self._response(self._sync_checked_in_chapters(owned))

        with SessionLocal() as session:
            poi_map = PoiRepository(session).get_by_ids(trip.checked_in_poi_ids)
        copy = self._copy(request.language)
        chapters = []
        for order, poi_id in enumerate(trip.checked_in_poi_ids):
            name = poi_map[poi_id].poi_name if poi_id in poi_map else poi_id
            chapters.append(
                MemoirChapter(
                    poi_id=poi_id,
                    poi_name=name,
                    stop_order=order,
                    body=copy[request.style].format(name=name, number=order + 1),
                ).model_dump()
            )
        record = memoir_repository.create(
            TravelMemoir(
                trip_id=trip_id,
                user_id=user_id,
                title=copy["title"],
                style=request.style,
                language=request.language,
                introduction=copy["intro"],
                closing=copy["closing"],
                chapters=chapters,
                status="draft",
            )
        )
        return self._response(record)

    def get_by_trip(self, trip_id: str, user_id: str) -> MemoirResponse:
        record = self._owned(memoir_repository.get_by_trip(trip_id), user_id)
        return self._response(self._sync_checked_in_chapters(record))

    def get(self, memoir_id: str, user_id: str) -> MemoirResponse:
        record = self._owned(memoir_repository.get(memoir_id), user_id)
        return self._response(self._sync_checked_in_chapters(record))

    def update(self, memoir_id: str, user_id: str, request: MemoirUpdateRequest) -> MemoirResponse:
        record = self._owned(memoir_repository.get(memoir_id), user_id)
        record = self._sync_checked_in_chapters(record)
        values = request.model_dump(exclude_unset=True)
        if "chapters" in values:
            values["chapters"] = [
                chapter.model_dump() if isinstance(chapter, MemoirChapter) else chapter
                for chapter in (request.chapters or [])
            ]
        if values.get("cover_photo_id"):
            photo = memoir_repository.get_photo(values["cover_photo_id"])
            if photo is None or photo.memoir_id != record.id:
                raise MemoirValidationError("Cover photo does not belong to this memoir")
        updated = memoir_repository.update(memoir_id, values)
        return self._response(self._owned(updated, user_id))

    def add_photo(
        self, memoir_id: str, user_id: str, *, data: bytes, filename: str,
        content_type: str, poi_id: str | None, has_people: bool,
    ) -> MemoirPhotoResponse:
        record = self._owned(memoir_repository.get(memoir_id), user_id)
        record = self._sync_checked_in_chapters(record)
        allowed = {"image/jpeg", "image/png", "image/webp"}
        if content_type not in allowed:
            raise MemoirValidationError("Only JPEG, PNG, and WebP photos are supported")
        if not data or len(data) > 10 * 1024 * 1024:
            raise MemoirValidationError("Photo must be between 1 byte and 10 MB")
        if poi_id and poi_id not in {chapter.get("poi_id") for chapter in record.chapters}:
            raise MemoirValidationError("Photo location is not part of this memoir")
        photo = memoir_repository.add_photo(
            MemoirPhoto(
                memoir_id=memoir_id,
                poi_id=poi_id,
                filename=filename[:255] or "travel-photo",
                content_type=content_type,
                image_data=data,
                has_people=has_people,
            )
        )
        return self._photo_response(photo)

    def photo(self, memoir_id: str, photo_id: str, user_id: str) -> MemoirPhoto:
        self._owned(memoir_repository.get(memoir_id), user_id)
        photo = memoir_repository.get_photo(photo_id)
        if photo is None or photo.memoir_id != memoir_id:
            raise MemoirNotFoundError("Photo not found")
        return photo

    def delete_photo(self, memoir_id: str, photo_id: str, user_id: str) -> None:
        record = self._owned(memoir_repository.get(memoir_id), user_id)
        photo = memoir_repository.get_photo(photo_id)
        if photo is None or photo.memoir_id != memoir_id:
            raise MemoirNotFoundError("Photo not found")
        memoir_repository.delete_photo(photo_id)
        if record.cover_photo_id == photo_id:
            memoir_repository.update(memoir_id, {"cover_photo_id": None})

    def create_share(self, memoir_id: str, user_id: str, privacy: SharePrivacy):
        self._owned(memoir_repository.get(memoir_id), user_id)
        return memoir_repository.create_share(memoir_id, privacy.model_dump())

    def revoke_share(self, memoir_id: str, user_id: str) -> None:
        self._owned(memoir_repository.get(memoir_id), user_id)
        memoir_repository.revoke_shares(memoir_id)

    def shared(self, token: str) -> SharedMemoirResponse:
        found = memoir_repository.get_by_share(token)
        if found is None:
            raise MemoirNotFoundError("Shared memoir not found or link revoked")
        record, share = found
        privacy = SharePrivacy.model_validate(share.privacy)
        trip = trip_repository.get_trip(record.trip_id)
        if trip is None:
            raise MemoirNotFoundError("Trip not found")
        chapters = self._chapters(record)
        if privacy.hide_personal_notes:
            chapters = [chapter.model_copy(update={"personal_note": ""}) for chapter in chapters]
        photos = [
            photo for photo in record.photos
            if not (privacy.hide_people_photos and photo.has_people)
        ]
        visible_ids = {photo.id for photo in photos}
        return SharedMemoirResponse(
            title=record.title,
            style=record.style,
            language=record.language,
            introduction=record.introduction,
            closing=record.closing,
            route_id=None if privacy.hide_exact_route else trip.route_id,
            travel_date=None if privacy.hide_date else trip.created_at,
            chapters=[chapter for chapter in chapters if chapter.included],
            photos=[self._photo_response(photo, shared_token=token) for photo in photos],
            cover_photo_id=record.cover_photo_id if record.cover_photo_id in visible_ids else None,
        )

    def shared_photo(self, token: str, photo_id: str) -> MemoirPhoto:
        found = memoir_repository.get_by_share(token)
        if found is None:
            raise MemoirNotFoundError("Shared memoir not found or link revoked")
        record, share = found
        photo = next((item for item in record.photos if item.id == photo_id), None)
        privacy = SharePrivacy.model_validate(share.privacy)
        if photo is None or (privacy.hide_people_photos and photo.has_people):
            raise MemoirNotFoundError("Photo not available")
        return photo


memoir_service = MemoirService()
