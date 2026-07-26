import type { LanguageCode, Preference } from "@/types";

export interface UserProfile {
  user_id: string;
  email: string | null;
  phone: string | null;
  name: string;
  language: LanguageCode;
  country: string | null;
  verification_status: "unverified" | "pending" | "verified";
  preference: Preference | null;
}

export interface RegisterInput {
  email?: string | null;
  phone?: string | null;
  password: string;
  name: string;
  language: LanguageCode;
  country?: string | null;
}

export interface LoginInput {
  email?: string | null;
  phone?: string | null;
  password: string;
}

export interface AuthResponse {
  user_id: string;
  email: string | null;
  phone: string | null;
  token: string;
  user: UserProfile;
}

export interface LoginResponse {
  user_id: string;
  email: string | null;
  phone: string | null;
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
