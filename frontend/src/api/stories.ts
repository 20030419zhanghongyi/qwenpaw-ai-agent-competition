import type {
  StoryActionRequest,
  StoryActionResponse,
  StoryOverview,
  StorySessionResponse,
} from "@/types/stories";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class StoryApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "StoryApiError";
  }
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
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (body.detail != null) detail = JSON.stringify(body.detail);
    } catch {
      // keep status text
    }
    throw new StoryApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

export function fetchStory(storyId: string): Promise<StoryOverview> {
  return request<StoryOverview>(`/api/v1/stories/${encodeURIComponent(storyId)}`);
}

export function startStorySession(
  storyId: string,
  token: string,
): Promise<StorySessionResponse> {
  return request<StorySessionResponse>(
    `/api/v1/stories/${encodeURIComponent(storyId)}/sessions`,
    { method: "POST" },
    token,
  );
}

export function fetchStorySession(
  sessionId: string,
  token: string,
): Promise<StorySessionResponse> {
  return request<StorySessionResponse>(
    `/api/v1/story-sessions/${encodeURIComponent(sessionId)}`,
    undefined,
    token,
  );
}

export function applyStoryAction(
  sessionId: string,
  actionRequest: StoryActionRequest,
  token: string,
): Promise<StoryActionResponse> {
  return request<StoryActionResponse>(
    `/api/v1/story-sessions/${encodeURIComponent(sessionId)}/actions`,
    {
      method: "POST",
      body: JSON.stringify(actionRequest),
    },
    token,
  );
}
