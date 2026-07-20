import type { LanguageCode, Preference } from "@/types";

export interface UserProfile {
  user_id: string;
  name: string | null;
  language: LanguageCode;
  preference: Preference | null;
}

export interface RegisterInput {
  user_id?: string;
  name?: string;
  language: LanguageCode;
}

export interface LoginInput {
  user_id: string;
}

export interface AuthResponse {
  user_id: string;
  token: string;
  user: UserProfile;
}

export interface LoginResponse {
  user_id: string;
  token: string;
}

export interface CurrentUserResponse {
  user: UserProfile | null;
}

export interface PreferenceSaveResponse {
  status: string;
  user_id: string;
  preference: Preference;
}
