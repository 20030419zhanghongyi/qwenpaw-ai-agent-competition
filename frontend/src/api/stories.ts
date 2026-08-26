import type {
  FutureLetterResponse,
  StoryActionRequest,
  StoryActionResponse,
  StoryOverview,
  StorySessionResponse,
} from "@/types/stories";
import type { LanguageCode } from "@/types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export type StoryApiErrorStatus = 401 | 403 | 404 | 409 | 422 | 503;

interface StoryErrorBody {
  detail?: unknown;
  [key: string]: unknown;
}

function detailMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (detail != null) {
    try {
      return JSON.stringify(detail);
    } catch {
      // Fall through to the HTTP status text.
    }
  }
  return fallback;
}

export class StoryApiError extends Error {
  readonly status: number;
  readonly detail: unknown;
  readonly body: StoryErrorBody | null;
  readonly path: string;

  constructor(options: {
    message: string;
    status: number;
    detail?: unknown;
    body?: StoryErrorBody | null;
    path?: string;
  }) {
    super(options.message);
    this.name = "StoryApiError";
    this.status = options.status;
    this.detail = options.detail;
    this.body = options.body ?? null;
    this.path = options.path ?? "";
  }

  isStatus(...statuses: StoryApiErrorStatus[]): boolean {
    return statuses.includes(this.status as StoryApiErrorStatus);
  }
}

export function isStoryApiError(
  error: unknown,
  ...statuses: StoryApiErrorStatus[]
): error is StoryApiError {
  if (!(error instanceof StoryApiError)) return false;
  return statuses.length === 0 || error.isStatus(...statuses);
}

export function createStoryAuthError(message = "请先登录"): StoryApiError {
  return new StoryApiError({
    message,
    status: 401,
    detail: message,
  });
}

async function request<T>(
  path: string,
  init?: RequestInit,
  token?: string,
): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(init?.headers);
  if (method !== "GET" && method !== "HEAD" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    const fallback = `${response.status} ${response.statusText}`.trim();
    let body: StoryErrorBody | null = null;
    try {
      body = (await response.json()) as StoryErrorBody;
    } catch {
      // Non-JSON error bodies are represented by the status text.
    }
    const detail = body?.detail;
    throw new StoryApiError({
      message: detailMessage(detail, fallback),
      status: response.status,
      detail,
      body,
      path,
    });
  }

  return response.json() as Promise<T>;
}

function languageQuery(language: LanguageCode): string {
  return `?language=${encodeURIComponent(language)}`;
}

export function fetchStory(
  storyId: string,
  language: LanguageCode,
): Promise<StoryOverview> {
  return request<StoryOverview>(
    `/api/v1/stories/${encodeURIComponent(storyId)}${languageQuery(language)}`,
  );
}

export function startStorySession(
  storyId: string,
  token: string,
  language: LanguageCode,
  schedule?: { day: number; date: string } | null,
): Promise<StorySessionResponse> {
  const search = new URLSearchParams({ language });
  if (schedule) {
    search.set("scheduled_day", String(schedule.day));
    search.set("scheduled_date", schedule.date);
  }
  return request<StorySessionResponse>(
    `/api/v1/stories/${encodeURIComponent(storyId)}/sessions?${search.toString()}`,
    { method: "POST" },
    token,
  );
}

export function fetchStorySession(
  sessionId: string,
  token: string,
  language: LanguageCode,
): Promise<StorySessionResponse> {
  return request<StorySessionResponse>(
    `/api/v1/story-sessions/${encodeURIComponent(sessionId)}${languageQuery(language)}`,
    undefined,
    token,
  );
}

export function fetchActiveStorySession(
  storyId: string,
  token: string,
  language: LanguageCode,
): Promise<StorySessionResponse> {
  return request<StorySessionResponse>(
    `/api/v1/stories/${encodeURIComponent(storyId)}/sessions/active${languageQuery(language)}`,
    undefined,
    token,
  );
}

export function applyStoryAction(
  sessionId: string,
  actionRequest: StoryActionRequest,
  token: string,
  language: LanguageCode,
): Promise<StoryActionResponse> {
  return request<StoryActionResponse>(
    `/api/v1/story-sessions/${encodeURIComponent(sessionId)}/actions${languageQuery(language)}`,
    {
      method: "POST",
      body: JSON.stringify(actionRequest),
    },
    token,
  );
}

export async function fetchFutureLetter(
  sessionId: string,
  token: string,
): Promise<FutureLetterResponse | null> {
  try {
    return await request<FutureLetterResponse>(
      `/api/v1/story-sessions/${encodeURIComponent(sessionId)}/future-letter`,
      undefined,
      token,
    );
  } catch (error) {
    if (isStoryApiError(error, 404)) return null;
    throw error;
  }
}

export function generateFutureLetter(
  sessionId: string,
  token: string,
): Promise<FutureLetterResponse> {
  return request<FutureLetterResponse>(
    `/api/v1/story-sessions/${encodeURIComponent(sessionId)}/future-letter`,
    { method: "POST" },
    token,
  );
}

export async function fetchFutureLetterImage(
  sessionId: string,
  token: string,
): Promise<Blob> {
  const path = `/api/v1/story-sessions/${encodeURIComponent(sessionId)}/future-letter/image`;
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const fallback = `${response.status} ${response.statusText}`.trim();
    let body: StoryErrorBody | null = null;
    try {
      body = (await response.json()) as StoryErrorBody;
    } catch {
      // Preserve the HTTP status for non-JSON image errors.
    }
    throw new StoryApiError({
      message: detailMessage(body?.detail, fallback),
      status: response.status,
      detail: body?.detail,
      body,
      path,
    });
  }
  return response.blob();
}
