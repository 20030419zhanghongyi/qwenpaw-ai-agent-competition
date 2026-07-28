import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { ErrorState, LoadingState } from "@/components/common/States";
import { StoryImage } from "@/features/story/assets";
import { StoryBottomAction } from "@/features/story/components/StoryBottomAction";
import { useAuth } from "@/state/AuthContext";
import { useStory, useStoryRestore } from "@/state/StoryContext";
import type { StorySessionResponse } from "@/types/stories";

function sessionDestination(session: StorySessionResponse): string {
  if (session.status === "completed") {
    return `/story-sessions/${session.session_id}/ending`;
  }
  if (session.current_chapter_id === "prologue_old_book") {
    return `/story-sessions/${session.session_id}/nodes/${session.current_chapter_id}`;
  }
  return `/story-sessions/${session.session_id}/map`;
}

export function StoryCoverPage() {
  const { storyId } = useParams<{ storyId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, isRestoring } = useAuth();
  const {
    story,
    session,
    loading,
    error,
    errorStatus,
    loadStory,
    startStory,
    restoreSession,
    clearError,
  } = useStory();
  const { sessionId: persistedSessionId } = useStoryRestore();
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    if (storyId) void loadStory(storyId);
  }, [loadStory, storyId]);

  useEffect(() => {
    if (
      isAuthenticated &&
      persistedSessionId &&
      session?.session_id !== persistedSessionId
    ) {
      void restoreSession(persistedSessionId);
    }
  }, [
    isAuthenticated,
    persistedSessionId,
    restoreSession,
    session?.session_id,
  ]);

  const ownStorySession =
    session && session.story_id === storyId ? session : null;
  const primaryLabel = useMemo(() => {
    if (!isAuthenticated) return "登录并开始";
    if (ownStorySession?.status === "completed") return "查看完成记录";
    if (ownStorySession?.status === "active") return "继续上次进度";
    return "开始故事";
  }, [isAuthenticated, ownStorySession?.status]);

  const handlePrimaryAction = async () => {
    if (!storyId || starting) return;
    clearError();

    if (!isAuthenticated) {
      const returnTo = `${location.pathname}${location.search}`;
      navigate(`/auth?returnTo=${encodeURIComponent(returnTo)}`);
      return;
    }

    if (ownStorySession) {
      navigate(sessionDestination(ownStorySession));
      return;
    }

    setStarting(true);
    try {
      const startedSession = await startStory(storyId);
      navigate(sessionDestination(startedSession));
    } finally {
      setStarting(false);
    }
  };

  if ((loading || isRestoring) && !story) {
    return <LoadingState label="正在展开旧地图…" />;
  }

  if (!story && error) {
    return (
      <main className="grid min-h-dvh place-items-center bg-paper px-4">
        <div className="w-full max-w-[480px]">
          <ErrorState
            message={
              errorStatus === 404 ? "故事暂未开放" : error
            }
            onRetry={() => storyId && void loadStory(storyId)}
          />
        </div>
      </main>
    );
  }

  if (!story) return null;

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col bg-paper text-ink shadow-[var(--shadow-soft)]">
      <div className="flex-1 px-4 pb-32 pt-[max(1rem,env(safe-area-inset-top))]">
        <button
          type="button"
          onClick={() => navigate("/preferences")}
          className="mb-3 inline-flex min-h-11 items-center rounded-full px-2 text-sm text-ink-soft"
        >
          ← 返回偏好页
        </button>

        <StoryImage
          assetId={story.presentation.cover_asset_id}
          alt={`${story.title}故事封面`}
          eager
          imageClassName="object-contain"
        />

        <section className="relative mt-4 rounded-3xl border border-line bg-paper px-5 pb-5 pt-6 shadow-[var(--shadow-lift)]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-ochre">
            Story Walk · 限定故事游
          </p>
          <h1 className="mt-2 font-display text-3xl leading-tight">
            {story.title}
          </h1>
          <p className="mt-2 font-serif text-base leading-relaxed text-sage-deep">
            {story.subtitle}
          </p>
          <p className="mt-4 text-base leading-7 text-ink-soft">
            {story.summary}
          </p>

          <div className="mt-5 grid grid-cols-2 gap-2 text-sm text-ink-soft">
            {[
              `约 ${story.estimated_hours} 小时`,
              "六个真实地点",
              "五个现场谜题",
              "谜题均可跳过",
            ].map((label) => (
              <span
                key={label}
                className="rounded-xl border border-line bg-paper-warm px-3 py-2 text-center"
              >
                {label}
              </span>
            ))}
          </div>
        </section>

        <section className="mt-4 rounded-2xl border border-line bg-card p-4">
          <h2 className="text-sm font-semibold text-sage-deep">安全游览说明</h2>
          <ul className="mt-2 space-y-1 text-sm leading-6 text-ink-soft">
            <li>请在开放区域游览，不进入封闭或施工区域。</li>
            <li>不需要触碰文物，也不以 GPS 作为强制通关条件。</li>
            <li>现场环境变化时，以安全和官方开放安排为先。</li>
          </ul>
        </section>

        {story.content_notice && (
          <details className="mt-4 rounded-2xl border border-ochre/30 bg-ochre/5 p-4">
            <summary className="min-h-11 cursor-pointer text-sm font-semibold text-ochre">
              史实与剧情边界
            </summary>
            <p className="text-sm leading-6 text-ink-soft">
              {story.content_notice}
            </p>
          </details>
        )}

        {error && (
          <p role="alert" className="mt-4 rounded-xl border border-clay/30 bg-clay/5 p-3 text-sm text-clay">
            {error}
          </p>
        )}
      </div>

      <StoryBottomAction
        label={primaryLabel}
        busy={starting}
        busyLabel="正在准备故事…"
        onClick={() => void handlePrimaryAction()}
        hint={
          ownStorySession?.status === "active"
            ? "会从服务端保存的最新章节继续"
            : undefined
        }
      />
    </main>
  );
}
