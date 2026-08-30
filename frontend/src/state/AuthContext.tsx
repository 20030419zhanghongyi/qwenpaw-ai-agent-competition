import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  AuthApiError,
  COOKIE_SESSION_TOKEN,
  claimGuestTrips,
  getCurrentUser,
  loginUser,
  logoutUser,
  registerUser,
  saveUserPreference,
} from "@/api/auth";
import {
  adoptGuestInvitationState,
  clearInvitationSession,
} from "@/story-discovery/invitationState";
import { clearGuestUserId, readGuestUserId } from "@/lib/guestUser";
import type { Preference } from "@/types";
import type { LoginInput, RegisterInput, UserProfile } from "@/types/auth";

const TOKEN_KEY = "macau-storywalk-auth-token";

interface AuthContextValue {
  token: string | null;
  userId: string | null;
  user: UserProfile | null;
  isAuthenticated: boolean;
  isRestoring: boolean;
  error: string | null;
  register: (input: RegisterInput) => Promise<void>;
  login: (input: LoginInput) => Promise<void>;
  logout: () => void;
  savePreference: (preference: Preference) => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function clearLegacyToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Storage may be unavailable in private or restricted browsing contexts.
  }
}

function errorMessage(error: unknown): string {
  if (error instanceof AuthApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "请求失败，请稍后重试";
}

async function adoptGuestTrips(token: string): Promise<void> {
  const guestUserId = readGuestUserId();
  if (!guestUserId) return;
  try {
    await claimGuestTrips(token, guestUserId);
    clearGuestUserId();
  } catch (claimError) {
    // Authentication should still succeed. Keep the guest id so a later restore can retry.
    console.warn("Could not attach guest trips to the account", claimError);
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(COOKIE_SESSION_TOKEN);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isRestoring, setIsRestoring] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const logout = useCallback(() => {
    clearInvitationSession();
    setToken(null);
    setUser(null);
    setError(null);
    setIsRestoring(false);
    clearLegacyToken();
    void logoutUser().catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!token) {
      setIsRestoring(false);
      return;
    }

    let cancelled = false;
    setIsRestoring(true);
    void getCurrentUser(token)
      .then(async ({ user: restoredUser }) => {
        if (cancelled) return;
        if (!restoredUser) {
          logout();
          return;
        }
        await adoptGuestTrips(token);
        if (cancelled) return;
        setUser(restoredUser);
        setError(null);
      })
      .catch((restoreError: unknown) => {
        if (cancelled) return;
        if (restoreError instanceof AuthApiError && restoreError.status === 401) {
          logout();
          return;
        }
        setError(errorMessage(restoreError));
      })
      .finally(() => {
        if (!cancelled) setIsRestoring(false);
      });

    return () => {
      cancelled = true;
    };
  }, [logout, token]);

  const register = useCallback(async (input: RegisterInput) => {
    setError(null);
    try {
      const response = await registerUser(input);
      adoptGuestInvitationState(response.user.user_id);
      await adoptGuestTrips(response.token);
      clearLegacyToken();
      setToken(COOKIE_SESSION_TOKEN);
      setUser(response.user);
    } catch (requestError) {
      const message = errorMessage(requestError);
      setError(message);
      throw requestError;
    }
  }, []);

  const login = useCallback(async (input: LoginInput) => {
    setError(null);
    try {
      const response = await loginUser(input);
      const { user: currentUser } = await getCurrentUser(response.token);
      if (!currentUser) throw new Error("用户资料不存在");
      adoptGuestInvitationState(currentUser.user_id);
      await adoptGuestTrips(response.token);
      clearLegacyToken();
      setToken(COOKIE_SESSION_TOKEN);
      setUser(currentUser);
    } catch (requestError) {
      const message = errorMessage(requestError);
      setError(message);
      throw requestError;
    }
  }, []);

  const savePreference = useCallback(
    async (preference: Preference) => {
      if (!user || !token) {
        const authError = new Error("请先登录");
        setError(authError.message);
        throw authError;
      }
      setError(null);
      try {
        const response = await saveUserPreference(user.user_id, preference, token);
        setUser((current) =>
          current
            ? {
                ...current,
                language: preference.language as UserProfile["language"],
                preference: response.preference,
              }
            : current,
        );
      } catch (requestError) {
        const message = errorMessage(requestError);
        setError(message);
        throw requestError;
      }
    },
    [token, user],
  );

  const clearError = useCallback(() => setError(null), []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      userId: user?.user_id ?? null,
      user,
      isAuthenticated: Boolean(token && user),
      isRestoring,
      error,
      register,
      login,
      logout,
      savePreference,
      clearError,
    }),
    [
      token,
      user,
      isRestoring,
      error,
      register,
      login,
      logout,
      savePreference,
      clearError,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
