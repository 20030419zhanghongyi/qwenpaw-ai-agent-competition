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
  getCurrentUser,
  loginUser,
  registerUser,
  saveUserPreference,
} from "@/api/auth";
import {
  adoptGuestInvitationState,
  clearInvitationSession,
} from "@/story-discovery/invitationState";
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

function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function writeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Authentication still works for the current page when storage is unavailable.
  }
}

function errorMessage(error: unknown): string {
  if (error instanceof AuthApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "请求失败，请稍后重试";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => readToken());
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isRestoring, setIsRestoring] = useState(() => Boolean(readToken()));
  const [error, setError] = useState<string | null>(null);

  const logout = useCallback(() => {
    clearInvitationSession();
    setToken(null);
    setUser(null);
    setError(null);
    setIsRestoring(false);
    writeToken(null);
  }, []);

  useEffect(() => {
    if (!token) {
      setIsRestoring(false);
      return;
    }

    let cancelled = false;
    setIsRestoring(true);
    void getCurrentUser(token)
      .then(({ user: restoredUser }) => {
        if (cancelled) return;
        if (!restoredUser) {
          logout();
          return;
        }
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
      writeToken(response.token);
      setToken(response.token);
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
      writeToken(response.token);
      setToken(response.token);
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
