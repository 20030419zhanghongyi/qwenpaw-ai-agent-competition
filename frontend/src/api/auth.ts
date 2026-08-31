import type { Preference } from "@/types";
import type {
  AuthResponse,
  ChangePasswordInput,
  CurrentUserResponse,
  LoginInput,
  LoginResponse,
  PreferenceSaveResponse,
  RegisterInput,
  SecurityQuestionUpdateInput,
} from "@/types/auth";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
export const COOKIE_SESSION_TOKEN = "__cookie_session__";

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

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
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

  if (response.status === 204) return undefined as T;

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

export async function changePassword(input: ChangePasswordInput): Promise<void> {
  await request("/api/v1/users/me/change-password", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getSecurityQuestion(): Promise<{ security_question_id: string | null }> {
  return request("/api/v1/users/me/security-question");
}

export async function updateSecurityQuestion(
  input: SecurityQuestionUpdateInput,
): Promise<void> {
  await request("/api/v1/users/me/security-question", {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function getRecoveryQuestion(
  email: string,
): Promise<{ security_question_id: string }> {
  return request("/api/v1/users/password-recovery/question", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(input: {
  email: string;
  security_question_id: string;
  security_answer: string;
  new_password: string;
}): Promise<void> {
  await request("/api/v1/users/password-recovery/reset", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getCurrentUser(token?: string): Promise<CurrentUserResponse> {
  return request("/api/v1/users/me", undefined, token);
}

export async function logoutUser(): Promise<void> {
  await fetch(`${API_BASE}/api/v1/users/logout`, {
    method: "POST",
    credentials: "include",
  });
}

export function claimGuestTrips(
  token: string,
  guestUserId: string,
): Promise<{ claimed_trips: number }> {
  return request(
    "/api/v1/users/me/claim-guest-trips",
    {
      method: "POST",
      body: JSON.stringify({ guest_user_id: guestUserId }),
    },
    token,
  );
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
