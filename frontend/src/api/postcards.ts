import type { LanguageCode } from "@/types";
import type { PhotoStyle, Postcard, PostcardListResponse } from "@/types/postcards";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const POSTCARD_LAYOUT_VERSION = "3";

function withLayoutVersion(url: string): string {
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}layout=${POSTCARD_LAYOUT_VERSION}`;
}

export class PostcardApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "PostcardApiError";
  }
}

async function parseError(response: Response): Promise<string> {
  let detail = `${response.status} ${response.statusText}`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") detail = body.detail;
    else if (body.detail != null) detail = JSON.stringify(body.detail);
  } catch {
    // Keep the HTTP status text when the response is not JSON.
  }
  return detail;
}

/** Absolute URL for a rendered postcard SVG (usable in <img src>). */
export function postcardImageSrc(imageUrlOrId: string): string {
  if (imageUrlOrId.startsWith("http://") || imageUrlOrId.startsWith("https://")) {
    return imageUrlOrId;
  }
  if (imageUrlOrId.startsWith("/")) {
    return withLayoutVersion(`${API_BASE}${imageUrlOrId}`);
  }
  return withLayoutVersion(
    `${API_BASE}/api/v1/postcards/${encodeURIComponent(imageUrlOrId)}/image`,
  );
}

export function postcardPngSrc(postcardId: string): string {
  return `${API_BASE}/api/v1/postcards/${encodeURIComponent(postcardId)}/image.png`;
}

export async function createPostcard(args: {
  tripId: string;
  poiId: string;
  photo?: File | null;
  language: LanguageCode | string;
  /** When true, replace an existing postcard for the same trip+POI. */
  replace?: boolean;
  /** QwenPaw gc-minimal-zine-poster scene; failure is reported instead of substituted. */
  aiScene?: boolean;
  /** Optional Qwen-Image style transfer for a user-uploaded photo. */
  photoStyle?: PhotoStyle | null;
}): Promise<Postcard> {
  const form = new FormData();
  form.append("poi_id", args.poiId);
  form.append("language", args.language);
  if (args.replace) {
    form.append("replace", "true");
  }
  if (args.aiScene) {
    form.append("ai_scene", "true");
  }
  if (args.photo) {
    form.append("photo", args.photo);
    if (args.photoStyle) {
      form.append("photo_style", args.photoStyle);
    }
  }

  const response = await fetch(
    `${API_BASE}/api/v1/trips/${encodeURIComponent(args.tripId)}/postcards`,
    { method: "POST", body: form },
  );
  if (!response.ok) {
    throw new PostcardApiError(await parseError(response), response.status);
  }
  return response.json() as Promise<Postcard>;
}

export async function prewarmPostcardScene(args: {
  tripId: string;
  poiId: string;
  language: LanguageCode | string;
}): Promise<void> {
  const form = new FormData();
  form.append("poi_id", args.poiId);
  form.append("language", args.language);
  const response = await fetch(
    `${API_BASE}/api/v1/trips/${encodeURIComponent(args.tripId)}/postcards/prewarm`,
    { method: "POST", body: form },
  );
  if (!response.ok) {
    throw new PostcardApiError(await parseError(response), response.status);
  }
}

export async function deletePostcard(postcardId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE}/api/v1/postcards/${encodeURIComponent(postcardId)}`,
    { method: "DELETE" },
  );
  if (!response.ok) {
    throw new PostcardApiError(await parseError(response), response.status);
  }
}

export async function listTripPostcards(tripId: string): Promise<Postcard[]> {
  const response = await fetch(
    `${API_BASE}/api/v1/trips/${encodeURIComponent(tripId)}/postcards`,
  );
  if (!response.ok) {
    throw new PostcardApiError(await parseError(response), response.status);
  }
  const body = (await response.json()) as PostcardListResponse;
  return body.postcards ?? [];
}

export async function listAccountPostcards(token: string): Promise<Postcard[]> {
  const response = await fetch(`${API_BASE}/api/v1/postcards`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new PostcardApiError(await parseError(response), response.status);
  }
  const body = (await response.json()) as PostcardListResponse;
  return body.postcards ?? [];
}
