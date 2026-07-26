import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  applyStoryAction,
  fetchStory,
  fetchStorySession,
  startStorySession,
} from "@/api/stories";
import type {
  StoryActionRequest,
  StoryActionResponse,
  StoryOverview,
  StoryReward,
  StorySessionResponse,
} from "@/types/stories";

const SESSION_KEY = "macau-storywalk-story-session-id";

/* ── Helpers ── */

function readSessionId(): string | null {
  try {
    return localStorage.getItem(SESSION_KEY);
  } catch {
    return null;
  }
}

function writeSessionId(id: string | null) {
  try {
    if (id) localStorage.setItem(SESSION_KEY, id);
    else localStorage.removeItem(SESSION_KEY);
  } catch {
    // ignore
  }
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "请求失败，请稍后重试";
}

/* ── Context value ── */

export interface StoryContextValue {
  /** Story metadata (loaded once per story id). */
  story: StoryOverview | null;
  /** Active session. Null while loading or if not started. */
  session: StorySessionResponse | null;
  /** Rewards that were just granted by the most recent action. */
  latestRewards: StoryReward[];
  /** Loading state for any async operation. */
  loading: boolean;
  /** Latest error message, if any. */
  error: string | null;
  /** Load a story overview. */
  loadStory: (storyId: string) => Promise<void>;
  /** Start or resume a story session. Requires a valid JWT. */
  startStory: (storyId: string) => Promise<void>;
  /** Restore a previously-persisted session by ID. */
  restoreSession: (sessionId: string) => Promise<void>;
  /** Refresh the current session from backend. */
  refreshSession: () => Promise<void>;
  /** Submit one story action. */
  submitAction: (request: StoryActionRequest) => Promise<StoryActionResponse>;
  /** Clear story state and persisted session id. */
  clearStory: () => void;
  /** Dismiss the latest-rewards display. */
  clearLatestRewards: () => void;
}

const StoryContext = createContext<StoryContextValue | null>(null);

/* ── Provider ── */

export function StoryProvider({ children }: { children: ReactNode }) {
  const [story, setStory] = useState<StoryOverview | null>(null);
  const [session, setSession] = useState<StorySessionResponse | null>(null);
  const [latestRewards, setLatestRewards] = useState<StoryReward[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStory = useCallback(async (storyId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchStory(storyId);
      setStory(data);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const startStory = useCallback(async (storyId: string) => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("macau-storywalk-auth-token");
      if (!token) throw new Error("请先登录");
      const sess = await startStorySession(storyId, token);
      setSession(sess);
      writeSessionId(sess.session_id);
    } catch (e) {
      setError(errorMessage(e));
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const restoreSession = useCallback(async (sessionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("macau-storywalk-auth-token");
      if (!token) throw new Error("请先登录");
      const sess = await fetchStorySession(sessionId, token);
      setSession(sess);
      writeSessionId(sess.session_id);
    } catch (e) {
      const msg = errorMessage(e);
      if (msg.includes("404") || msg.includes("403") || msg.includes("401")) {
        writeSessionId(null);
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshSession = useCallback(async () => {
    setError(null);
    const current = session;
    if (!current) return;
    try {
      const token = localStorage.getItem("macau-storywalk-auth-token");
      if (!token) throw new Error("请先登录");
      const sess = await fetchStorySession(current.session_id, token);
      setSession(sess);
    } catch (e) {
      setError(errorMessage(e));
    }
  }, [session]);

  const submitAction = useCallback(
    async (request: StoryActionRequest): Promise<StoryActionResponse> => {
      setLoading(true);
      setError(null);
      try {
        const token = localStorage.getItem("macau-storywalk-auth-token");
        if (!token) throw new Error("请先登录");
        const current = session;
        if (!current) throw new Error("没有进行中的故事会话");
        const response = await applyStoryAction(
          current.session_id,
          request,
          token,
        );
        setSession(response.session);
        if (response.new_rewards.length > 0) {
          setLatestRewards(response.new_rewards);
        }
        return response;
      } catch (e) {
        setError(errorMessage(e));
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [session],
  );

  const clearStory = useCallback(() => {
    setStory(null);
    setSession(null);
    setLatestRewards([]);
    setError(null);
    setLoading(false);
    writeSessionId(null);
  }, []);

  const clearLatestRewards = useCallback(() => setLatestRewards([]), []);

  const value = useMemo<StoryContextValue>(
    () => ({
      story,
      session,
      latestRewards,
      loading,
      error,
      loadStory,
      startStory,
      restoreSession,
      refreshSession,
      submitAction,
      clearStory,
      clearLatestRewards,
    }),
    [
      story,
      session,
      latestRewards,
      loading,
      error,
      loadStory,
      startStory,
      restoreSession,
      refreshSession,
      submitAction,
      clearStory,
      clearLatestRewards,
    ],
  );

  return (
    <StoryContext.Provider value={value}>{children}</StoryContext.Provider>
  );
}

/* ── Hook ── */

export function useStory(): StoryContextValue {
  const ctx = useContext(StoryContext);
  if (!ctx) throw new Error("useStory must be used within StoryProvider");
  return ctx;
}

/** Restore a persisted story session on app mount. */
export function useStoryRestore() {
  return {
    sessionId: readSessionId(),
  };
}
