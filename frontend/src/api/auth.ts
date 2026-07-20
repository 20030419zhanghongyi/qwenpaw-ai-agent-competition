import type { Preference } from "@/types";
import type {
  AuthResponse,
  CurrentUserResponse,
  LoginInput,
  LoginResponse,
  PreferenceSaveResponse,
  RegisterInput,
} from "@/types/auth";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class AuthApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "AuthApiError";
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
      // Keep the HTTP status text when the response is not JSON.
    }
    throw new AuthApiError(detail, response.status);
  }

  return response.json() as Promise<T>;
}

export function registerUser(input: RegisterInput): Promise<AuthResponse> {
  return request("/api/v1/users/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function loginUser(input: LoginInput): Promise<LoginResponse> {
  return request("/api/v1/users/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getCurrentUser(token: string): Promise<CurrentUserResponse> {
  return request("/api/v1/users/me", undefined, token);
}

export function saveUserPreference(
  userId: string,
  preference: Preference,
  token?: string,
): Promise<PreferenceSaveResponse> {
  return request(
    `/api/v1/users/${encodeURIComponent(userId)}/preferences`,
    {
      method: "PUT",
      body: JSON.stringify(preference),
    },
    token,
  );
}
