import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { LoadingState, ErrorState } from "@/components/common/States";
import { useAuth } from "@/state/AuthContext";
import { useStory } from "@/state/StoryContext";
import { useWalk } from "@/state/WalkContext";

export function StoryCoverPage() {
  const { storyId } = useParams<{ storyId: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, register } = useAuth();
  const { language } = useWalk();
  const { story, session, loading, error, loadStory, startStory, clearStory } =
    useStory();
  const [starting, setStarting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (storyId) loadStory(storyId);
  }, [storyId, loadStory]);

  const ensureStoryGuest = useCallback(async () => {
    if (isAuthenticated) return;
    const guestId =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    await register({
      email: `story-guest-${guestId}@local.test`,
      password: `StoryGuest-${guestId}`,
      name: "剧情游客",
      language,
      country: null,
    });
  }, [isAuthenticated, language, register]);

  const handleStart = useCallback(async () => {
    if (!storyId) return;
    setStarting(true);
    setActionError(null);
    try {
      await ensureStoryGuest();
      const started = await startStory(storyId);
      // Navigate to the map after starting
      navigate(`/story-sessions/${started.session_id}/map`);
    } catch (e) {
      setActionError(
        e instanceof Error ? e.message : "无法开始故事，请稍后重试",
      );
    } finally {
      setStarting(false);
    }
  }, [ensureStoryGuest, navigate, startStory, storyId]);

  const handleGoToMap = useCallback(() => {
    if (session) {
      navigate(`/story-sessions/${session.session_id}/map`);
    }
  }, [navigate, session]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || starting || loading) return;
      const target = event.target as HTMLElement | null;
      if (
        target?.closest("input, textarea, select, button, a, [contenteditable='true']")
      ) {
        return;
      }
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (session?.status === "active") handleGoToMap();
        else void handleStart();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handleGoToMap, handleStart, loading, session?.status, starting]);

  const handleBack = () => {
    clearStory();
    navigate("/");
  };

  if (loading) return <LoadingState label="加载故事信息…" />;
  if (error) {
    return (
      <div className="flex min-h-dvh flex-col bg-paper px-4 py-8">
        <ErrorState message={error} onRetry={() => storyId && loadStory(storyId)} />
      </div>
    );
  }
  if (!story) return null;

  const hasActive = session?.status === "active";
  const coverSrc =
    story.id === "coloane_after_tide"
      ? "/story/coloane-after-tide/cover.jpg"
      : null;

  return (
    <main className="flex min-h-dvh flex-col bg-paper text-ink">
      <div className="flex-1 px-4 pb-8 pt-6 sm:mx-auto sm:max-w-lg sm:px-6">
        {/* Back */}
        <button
          type="button"
          onClick={handleBack}
          className="mb-4 text-sm text-ink-soft transition hover:text-ink"
        >
          ← 返回首页
        </button>

        {/* Header */}
        <div className="overflow-hidden rounded-2xl border border-line bg-card shadow-[var(--shadow-soft)]">
          {coverSrc && (
            <img
              src={coverSrc}
              alt=""
              className="h-44 w-full object-cover"
              loading="lazy"
            />
          )}
          <div className="p-6">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-ochre">
            StoryWalk
          </p>
          <h1 className="mt-2 font-display text-2xl leading-tight text-ink">
            {story.title}
          </h1>
          <p className="mt-1 font-serif text-base italic text-sage-deep">
            {story.subtitle}
          </p>
          <p className="mt-3 text-sm leading-relaxed text-ink-soft">
            {story.summary}
          </p>

          {/* Meta */}
          <div className="mt-4 flex flex-wrap gap-3 text-xs text-ink-soft">
            {story.estimated_hours && (
              <span className="rounded-full border border-line bg-paper-warm px-3 py-1">
                约 {story.estimated_hours} 小时
              </span>
            )}
            <span className="rounded-full border border-line bg-paper-warm px-3 py-1">
              {story.nodes.length} 个章节
            </span>
          </div>
          </div>
        </div>

        {/* Identity */}
        {story.identity && (
          <div className="mt-4 rounded-2xl border border-line bg-paper-warm p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sage-deep">
              你的身份
            </p>
            <p className="mt-1 font-serif text-lg text-ink">
              {story.identity.name}
            </p>
            <p className="mt-1 text-sm text-ink-soft">
              {story.identity.description}
            </p>
          </div>
        )}

        {/* Content notice */}
        {story.content_notice && (
          <div className="mt-4 rounded-2xl border border-ochre/30 bg-ochre/5 p-4">
            <p className="text-xs leading-relaxed text-ink-soft">
              {story.content_notice}
            </p>
          </div>
        )}

        {/* Error */}
        {actionError && (
          <div className="mt-4 rounded-xl border border-clay/30 bg-clay/5 p-4 text-sm text-clay">
            {actionError}
          </div>
        )}

        {/* Actions */}
        <div className="mt-8 space-y-3">
          {hasActive ? (
            <>
              <button
                type="button"
                autoFocus
                onClick={handleGoToMap}
                className="w-full rounded-full bg-sage-deep px-6 py-4 text-base font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss active:scale-[0.99]"
              >
                继续探索
              </button>
              <button
                type="button"
                disabled={starting}
                onClick={handleStart}
                className="w-full rounded-full border border-line bg-card px-6 py-3.5 text-sm text-ink-soft transition hover:border-sage"
              >
                重新开始
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                autoFocus
                disabled={starting}
                onClick={handleStart}
                className="w-full rounded-full bg-sage-deep px-6 py-4 text-base font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss active:scale-[0.99] disabled:opacity-50"
              >
                {starting
                  ? "正在准备…"
                  : isAuthenticated
                    ? "开始探索"
                    : "游客开始探索"}
              </button>
              {!isAuthenticated && (
                <p className="text-center text-xs text-ink-soft">
                  演示模式会自动建立临时游客身份，不需要填写账号密码。
                </p>
              )}
            </>
          )}
        </div>

        {/* Chapter preview */}
        <div className="mt-8">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-soft">
            章节概览
          </p>
          <div className="mt-3 space-y-2">
            {story.nodes.map((node) => (
              <div
                key={node.id}
                className="flex items-center gap-3 rounded-xl border border-line bg-card px-4 py-3"
              >
                <span className="grid size-7 shrink-0 place-items-center rounded-full bg-sage-deep/10 font-serif text-xs font-bold text-sage-deep">
                  {node.order}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-ink">
                    {node.title}
                  </p>
                  <p className="text-xs text-ink-soft">
                    {node.kind === "prologue"
                      ? "序章"
                      : node.kind === "transition"
                        ? "过渡"
                        : node.kind === "ending"
                          ? "终章"
                          : node.kind === "narrative"
                            ? "叙述"
                            : "谜题"}
                    {node.story_time ? ` · ${node.story_time}` : ""}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom calcada */}
      <div className="calcada-wave mx-4 mb-6 h-2.5 shrink-0 opacity-40 sm:mx-6" />
    </main>
  );
}
