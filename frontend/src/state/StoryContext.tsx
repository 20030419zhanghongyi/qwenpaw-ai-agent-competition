import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  StoryApiError,
  applyStoryAction,
  createStoryAuthError,
  fetchStory,
  fetchStorySession,
  isStoryApiError,
  startStorySession,
} from "@/api/stories";
import { useAuth } from "@/state/AuthContext";
import type {
  StoryActionRequest,
  StoryActionResponse,
  StoryChapter,
  StoryOverview,
  StoryReward,
  StorySessionResponse,
} from "@/types/stories";

export const STORY_SESSION_STORAGE_KEY = "macau-storywalk-story-session-id";

function storySessionStorageKey(userId: string): string {
  return `${STORY_SESSION_STORAGE_KEY}:${encodeURIComponent(userId)}`;
}

function readSessionId(userId: string | null): string | null {
  if (!userId) return null;
  try {
    return localStorage.getItem(storySessionStorageKey(userId));
  } catch {
    return null;
  }
}

function writeSessionId(userId: string | null, id: string | null): void {
  if (!userId) return;
  try {
    const key = storySessionStorageKey(userId);
    if (id) localStorage.setItem(key, id);
    else localStorage.removeItem(key);
    // Never reuse the legacy account-agnostic session key.
    localStorage.removeItem(STORY_SESSION_STORAGE_KEY);
  } catch {
    // The active in-memory session remains usable when storage is unavailable.
  }
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "请求失败，请稍后重试";
}

function structuredError(error: unknown): StoryApiError | null {
  return isStoryApiError(error) ? error : null;
}

function shouldDiscardSession(error: unknown): boolean {
  return isStoryApiError(error, 403, 404);
}

export class StoryActionInProgressError extends Error {
  constructor() {
    super("故事动作正在处理中，请勿重复提交");
    this.name = "StoryActionInProgressError";
  }
}

export interface StoryContextValue {
  story: StoryOverview | null;
  session: StorySessionResponse | null;
  latestRewards: StoryReward[];
  /**
   * Chapter captured immediately before the most recent action. This remains
   * available when the response has already advanced current_chapter.
   */
  submittedChapterSnapshot: StoryChapter | null;
  /** Full response from the most recently completed action. */
  lastActionResult: StoryActionResponse | null;
  loading: boolean;
  actionPending: boolean;
  error: string | null;
  apiError: StoryApiError | null;
  errorStatus: number | null;
  loadStory: (storyId: string) => Promise<StoryOverview | null>;
  /** Start or resume and return the backend's real session object. */
  startStory: (storyId: string) => Promise<StorySessionResponse>;
  /** Restore the explicitly requested session; URL callers take precedence. */
  restoreSession: (sessionId: string) => Promise<StorySessionResponse | null>;
  /** Refresh the in-memory session without recursively invoking restore. */
  refreshSession: () => Promise<StorySessionResponse | null>;
  submitAction: (request: StoryActionRequest) => Promise<StoryActionResponse>;
  clearStory: () => void;
  clearLatestRewards: () => void;
  clearLastAction: () => void;
  clearError: () => void;
}

const StoryContext = createContext<StoryContextValue | null>(null);

export function StoryProvider({ children }: { children: ReactNode }) {
  const { token, userId } = useAuth();
  const identityKey = userId
    ? `user:${userId}`
    : token
      ? "restoring-user"
      : "guest";

  return (
    <StoryStateProvider
      key={identityKey}
      token={token}
      userId={userId}
    >
      {children}
    </StoryStateProvider>
  );
}

function StoryStateProvider({
  children,
  token,
  userId,
}: {
  children: ReactNode;
  token: string | null;
  userId: string | null;
}) {
  const [story, setStory] = useState<StoryOverview | null>(null);
  const [session, setSessionState] = useState<StorySessionResponse | null>(null);
  const [latestRewards, setLatestRewards] = useState<StoryReward[]>([]);
  const [submittedChapterSnapshot, setSubmittedChapterSnapshot] =
    useState<StoryChapter | null>(null);
  const [lastActionResult, setLastActionResult] =
    useState<StoryActionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionPending, setActionPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<StoryApiError | null>(null);

  const sessionRef = useRef<StorySessionResponse | null>(null);
  const pendingCountRef = useRef(0);
  const startPromiseRef = useRef<Promise<StorySessionResponse> | null>(null);
  const restorePromiseRef = useRef<{
    sessionId: string;
    promise: Promise<StorySessionResponse | null>;
  } | null>(null);
  const refreshPromiseRef =
    useRef<Promise<StorySessionResponse | null> | null>(null);
  const actionLockRef = useRef(false);
  const restoreGenerationRef = useRef(0);

  const setCurrentSession = useCallback(
    (nextSession: StorySessionResponse | null) => {
      sessionRef.current = nextSession;
      setSessionState(nextSession);
    },
    [],
  );

  const beginLoading = useCallback(() => {
    pendingCountRef.current += 1;
    setLoading(true);
  }, []);

  const endLoading = useCallback(() => {
    pendingCountRef.current = Math.max(0, pendingCountRef.current - 1);
    if (pendingCountRef.current === 0) setLoading(false);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
    setApiError(null);
  }, []);

  const recordError = useCallback((requestError: unknown) => {
    setError(errorMessage(requestError));
    setApiError(structuredError(requestError));
  }, []);

  const requireToken = useCallback((): string => {
    if (!token) throw createStoryAuthError();
    return token;
  }, [token]);

  const discardPersistedSessionIfMatching = useCallback(
    (sessionId: string) => {
      if (readSessionId(userId) === sessionId) {
        writeSessionId(userId, null);
      }
      if (sessionRef.current?.session_id === sessionId) setCurrentSession(null);
    },
    [setCurrentSession, userId],
  );

  const loadStory = useCallback(
    async (storyId: string): Promise<StoryOverview | null> => {
      beginLoading();
      clearError();
      try {
        const data = await fetchStory(storyId);
        setStory(data);
        return data;
      } catch (requestError) {
        recordError(requestError);
        return null;
      } finally {
        endLoading();
      }
    },
    [beginLoading, clearError, endLoading, recordError],
  );

  const startStory = useCallback(
    (storyId: string): Promise<StorySessionResponse> => {
      if (startPromiseRef.current) return startPromiseRef.current;

      beginLoading();
      clearError();
      const operation = (async () => {
        try {
          const authToken = requireToken();
          const startedSession = await startStorySession(storyId, authToken);
          setCurrentSession(startedSession);
          writeSessionId(userId, startedSession.session_id);
          setLatestRewards([]);
          setSubmittedChapterSnapshot(null);
          setLastActionResult(null);
          return startedSession;
        } catch (requestError) {
          recordError(requestError);
          throw requestError;
        } finally {
          endLoading();
        }
      })();

      startPromiseRef.current = operation;
      void operation.then(
        () => {
          if (startPromiseRef.current === operation) startPromiseRef.current = null;
        },
        () => {
          if (startPromiseRef.current === operation) startPromiseRef.current = null;
        },
      );
      return operation;
    },
    [
      beginLoading,
      clearError,
      endLoading,
      recordError,
      requireToken,
      setCurrentSession,
      userId,
    ],
  );

  const restoreSession = useCallback(
    (sessionId: string): Promise<StorySessionResponse | null> => {
      const existing = restorePromiseRef.current;
      if (existing?.sessionId === sessionId) return existing.promise;

      const generation = restoreGenerationRef.current + 1;
      restoreGenerationRef.current = generation;
      // Never render a different in-memory session under an explicit URL.
      if (
        sessionRef.current &&
        sessionRef.current.session_id !== sessionId
      ) {
        setCurrentSession(null);
      }
      beginLoading();
      clearError();

      const operation = (async () => {
        try {
          const authToken = requireToken();
          const restoredSession = await fetchStorySession(sessionId, authToken);
          if (restoreGenerationRef.current !== generation) return restoredSession;

          const isDifferentSession =
            sessionRef.current?.session_id !== restoredSession.session_id;
          setCurrentSession(restoredSession);
          writeSessionId(userId, restoredSession.session_id);
          if (isDifferentSession) {
            setLatestRewards([]);
            setSubmittedChapterSnapshot(null);
            setLastActionResult(null);
          }
          return restoredSession;
        } catch (requestError) {
          if (restoreGenerationRef.current === generation) {
            if (shouldDiscardSession(requestError)) {
              discardPersistedSessionIfMatching(sessionId);
            }
            recordError(requestError);
          }
          return null;
        } finally {
          endLoading();
        }
      })();

      restorePromiseRef.current = { sessionId, promise: operation };
      void operation.then(() => {
        if (restorePromiseRef.current?.promise === operation) {
          restorePromiseRef.current = null;
        }
      });
      return operation;
    },
    [
      beginLoading,
      clearError,
      discardPersistedSessionIfMatching,
      endLoading,
      recordError,
      requireToken,
      setCurrentSession,
      userId,
    ],
  );

  const refreshSession = useCallback((): Promise<StorySessionResponse | null> => {
    if (refreshPromiseRef.current) return refreshPromiseRef.current;
    const current = sessionRef.current;
    if (!current) return Promise.resolve(null);

    beginLoading();
    clearError();
    const operation = (async () => {
      try {
        const authToken = requireToken();
        const refreshedSession = await fetchStorySession(
          current.session_id,
          authToken,
        );
        if (sessionRef.current?.session_id === current.session_id) {
          setCurrentSession(refreshedSession);
        }
        return refreshedSession;
      } catch (requestError) {
        if (shouldDiscardSession(requestError)) {
          discardPersistedSessionIfMatching(current.session_id);
        }
        recordError(requestError);
        return null;
      } finally {
        endLoading();
      }
    })();

    refreshPromiseRef.current = operation;
    void operation.then(() => {
      if (refreshPromiseRef.current === operation) refreshPromiseRef.current = null;
    });
    return operation;
  }, [
    beginLoading,
    clearError,
    discardPersistedSessionIfMatching,
    endLoading,
    recordError,
    requireToken,
    setCurrentSession,
  ]);

  const submitAction = useCallback(
    async (request: StoryActionRequest): Promise<StoryActionResponse> => {
      if (actionLockRef.current) throw new StoryActionInProgressError();

      const current = sessionRef.current;
      try {
        const authToken = requireToken();
        if (!current) throw new Error("没有进行中的故事会话");

        actionLockRef.current = true;
        setActionPending(true);
        beginLoading();
        clearError();
        setSubmittedChapterSnapshot(current.current_chapter);
        setLastActionResult(null);

        const response = await applyStoryAction(
          current.session_id,
          request,
          authToken,
        );
        setCurrentSession(response.session);
        writeSessionId(userId, response.session.session_id);
        setLastActionResult(response);
        setLatestRewards(response.new_rewards);
        return response;
      } catch (requestError) {
        if (
          current &&
          shouldDiscardSession(requestError)
        ) {
          discardPersistedSessionIfMatching(current.session_id);
        }
        recordError(requestError);
        throw requestError;
      } finally {
        if (actionLockRef.current) {
          actionLockRef.current = false;
          setActionPending(false);
          endLoading();
        }
      }
    },
    [
      beginLoading,
      clearError,
      discardPersistedSessionIfMatching,
      endLoading,
      recordError,
      requireToken,
      setCurrentSession,
      userId,
    ],
  );

  const clearStory = useCallback(() => {
    restoreGenerationRef.current += 1;
    setStory(null);
    setCurrentSession(null);
    setLatestRewards([]);
    setSubmittedChapterSnapshot(null);
    setLastActionResult(null);
    setError(null);
    setApiError(null);
    writeSessionId(userId, null);
  }, [setCurrentSession, userId]);

  const clearLatestRewards = useCallback(() => setLatestRewards([]), []);

  const clearLastAction = useCallback(() => {
    setSubmittedChapterSnapshot(null);
    setLastActionResult(null);
  }, []);

  const value = useMemo<StoryContextValue>(
    () => ({
      story,
      session,
      latestRewards,
      submittedChapterSnapshot,
      lastActionResult,
      loading,
      actionPending,
      error,
      apiError,
      errorStatus: apiError?.status ?? null,
      loadStory,
      startStory,
      restoreSession,
      refreshSession,
      submitAction,
      clearStory,
      clearLatestRewards,
      clearLastAction,
      clearError,
    }),
    [
      story,
      session,
      latestRewards,
      submittedChapterSnapshot,
      lastActionResult,
      loading,
      actionPending,
      error,
      apiError,
      loadStory,
      startStory,
      restoreSession,
      refreshSession,
      submitAction,
      clearStory,
      clearLatestRewards,
      clearLastAction,
      clearError,
    ],
  );

  return <StoryContext.Provider value={value}>{children}</StoryContext.Provider>;
}

export function useStory(): StoryContextValue {
  const context = useContext(StoryContext);
  if (!context) throw new Error("useStory must be used within StoryProvider");
  return context;
}

/** URL session IDs always win over a previously persisted fallback ID. */
export function resolveStorySessionId(
  urlSessionId?: string | null,
  userId: string | null = null,
): string | null {
  const normalizedUrlId = urlSessionId?.trim();
  return normalizedUrlId || readSessionId(userId);
}

export function useStoryRestore(urlSessionId?: string | null) {
  const { userId } = useAuth();
  return {
    sessionId: resolveStorySessionId(urlSessionId, userId),
  };
}
