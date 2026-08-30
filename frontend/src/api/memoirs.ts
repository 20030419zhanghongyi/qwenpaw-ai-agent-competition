const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export type MemoirStyle = "diary" | "magazine" | "social" | "documentary";

export interface MemoirChapter {
  poi_id: string;
  poi_name: string;
  stop_order: number;
  body: string;
  personal_note: string;
  included: boolean;
  postcard_id?: string | null;
  postcard_caption?: string | null;
  postcard_image_url?: string | null;
}

export interface MemoirPhoto {
  photo_id: string;
  poi_id: string | null;
  filename: string;
  content_type: string;
  has_people: boolean;
  image_url: string;
  created_at: string;
}

export interface TravelMemoir {
  memoir_id: string;
  trip_id: string;
  user_id: string;
  route_id: string;
  trip_status: string;
  travel_date: string | null;
  title: string;
  style: MemoirStyle;
  language: string;
  introduction: string;
  closing: string;
  status: "draft" | "completed";
  chapters: MemoirChapter[];
  photos: MemoirPhoto[];
  cover_photo_id: string | null;
  active_share_token: string | null;
  created_at: string;
  updated_at: string;
}

export interface SharePrivacy {
  hide_people_photos: boolean;
  hide_date: boolean;
  hide_exact_route: boolean;
  hide_personal_notes: boolean;
}

export interface SharedMemoir {
  title: string;
  style: MemoirStyle;
  language: string;
  introduction: string;
  closing: string;
  route_id: string | null;
  travel_date: string | null;
  chapters: MemoirChapter[];
  photos: MemoirPhoto[];
  cover_photo_id: string | null;
}

async function request<T>(path: string, init?: RequestInit, token?: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
    credentials: "include",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(typeof body.detail === "string" ? body.detail : `${response.status}`);
    Object.assign(error, { status: response.status });
    throw error;
  }
  return response.json() as Promise<T>;
}

export function createMemoir(tripId: string, style: MemoirStyle, language: string, token: string) {
  return request<TravelMemoir>(`/api/v1/trips/${encodeURIComponent(tripId)}/memoir`, {
    method: "POST", body: JSON.stringify({ style, language }),
  }, token);
}

export function getTripMemoir(tripId: string, token: string) {
  return request<TravelMemoir>(`/api/v1/trips/${encodeURIComponent(tripId)}/memoir`, undefined, token);
}

export function getMemoir(memoirId: string, token: string) {
  return request<TravelMemoir>(`/api/v1/memoirs/${encodeURIComponent(memoirId)}`, undefined, token);
}

export function updateMemoir(memoirId: string, input: Partial<TravelMemoir>, token: string) {
  const { title, style, introduction, closing, status, cover_photo_id, chapters } = input;
  return request<TravelMemoir>(`/api/v1/memoirs/${encodeURIComponent(memoirId)}`, {
    method: "PUT", body: JSON.stringify({ title, style, introduction, closing, status, cover_photo_id, chapters }),
  }, token);
}

export function uploadMemoirPhoto(
  memoirId: string, photo: File, poiId: string | null, hasPeople: boolean, token: string,
) {
  const form = new FormData();
  form.append("photo", photo);
  if (poiId) form.append("poi_id", poiId);
  form.append("has_people", String(hasPeople));
  return request<MemoirPhoto>(`/api/v1/memoirs/${encodeURIComponent(memoirId)}/photos`, {
    method: "POST", body: form,
  }, token);
}

export async function loadPrivatePhoto(photo: MemoirPhoto, memoirId: string, token: string) {
  const response = await fetch(`${API_BASE}/api/v1/memoirs/${encodeURIComponent(memoirId)}/photos/${encodeURIComponent(photo.photo_id)}`, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: "include",
  });
  if (!response.ok) throw new Error("Unable to load photo");
  return URL.createObjectURL(await response.blob());
}

export function deleteMemoirPhoto(memoirId: string, photoId: string, token: string) {
  return fetch(`${API_BASE}/api/v1/memoirs/${encodeURIComponent(memoirId)}/photos/${encodeURIComponent(photoId)}`, {
    method: "DELETE", headers: { Authorization: `Bearer ${token}` }, credentials: "include",
  }).then((response) => { if (!response.ok) throw new Error(`${response.status}`); });
}

export function createMemoirShare(memoirId: string, privacy: SharePrivacy, token: string) {
  return request<{ token: string; share_url: string; privacy: SharePrivacy }>(
    `/api/v1/memoirs/${encodeURIComponent(memoirId)}/shares`,
    { method: "POST", body: JSON.stringify(privacy) }, token,
  );
}

export function revokeMemoirShare(memoirId: string, token: string) {
  return fetch(`${API_BASE}/api/v1/memoirs/${encodeURIComponent(memoirId)}/shares`, {
    method: "DELETE", headers: { Authorization: `Bearer ${token}` }, credentials: "include",
  }).then((response) => { if (!response.ok) throw new Error(`${response.status}`); });
}

export function getSharedMemoir(shareToken: string) {
  return request<SharedMemoir>(`/api/v1/shared/memoirs/${encodeURIComponent(shareToken)}`);
}

export function publicAssetUrl(path: string) {
  return `${API_BASE}${path}`;
}
