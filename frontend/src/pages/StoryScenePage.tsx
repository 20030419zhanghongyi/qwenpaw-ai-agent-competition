import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { LoadingState, ErrorState } from "@/components/common/States";
import { PuzzlePanel } from "@/components/story/PuzzlePanel";
import { RewardReveal } from "@/components/story/RewardReveal";
import { useAuth } from "@/state/AuthContext";
import { useStory, useStoryRestore } from "@/state/StoryContext";
import type { StoryAction, StoryChapter, StoryPage } from "@/types/stories";

const CONTENT_LABELS: Record<string, string> = {
  historical_fact: "史实",
  folklore: "民间说法",
  contextual_reconstruction: "语境化重建",
  fictional_story: "虚构剧情",
  dynamic_operational_info: "动态营运信息",
};

const STORY_ASSET_SRC: Record<string, string> = {
  "CAT-COVER-01": "/story/coloane-after-tide/cover.svg",
  "CAT-PROP-01": "/story/coloane-after-tide/tide-workbook.svg",
  "CAT-SEA-01": "/story/coloane-after-tide/temple.svg",
  "CAT-BOAT-01": "/story/coloane-after-tide/tam-kung.svg",
  "CAT-VILLAGE-01": "/story/coloane-after-tide/chapel-square.svg",
  "CAT-CRAFT-01": "/story/coloane-after-tide/shipyards.svg",
  "CAT-SOIL-01": "/story/coloane-after-tide/hac-sa.svg",
  "CAT-END-01": "/story/coloane-after-tide/sound-postcard.svg",
};

const INITIAL_ACTION_STATE = {
  busy: false,
  lastMessage: null as string | null,
  lastHint: null as string | null,
  hintCount: 0,
  solved: false,
  skipped: false,
};

function storyAssetSrc(page?: StoryPage | null) {
  if (!page?.asset_id) return null;
  return STORY_ASSET_SRC[page.asset_id] ?? null;
}

export function StoryScenePage() {
  const { sessionId, nodeId } = useParams<{ sessionId: string; nodeId: string }>();
  const navigate = useNavigate();
  const { token } = useAuth();
  const {
    session,
    latestRewards,
    loading,
    error,
    restoreSession,
    refreshSession,
    submitAction,
    clearLatestRewards,
  } = useStory();
  const { sessionId: persistedId } = useStoryRestore();

  const [actionState, setActionState] = useState<{
    busy: boolean;
    lastMessage: string | null;
    lastHint: string | null;
    hintCount: number;
    solved: boolean;
    skipped: boolean;
  }>(INITIAL_ACTION_STATE);
  const [pageIndex, setPageIndex] = useState(0);
  const [activeTimeLayer, setActiveTimeLayer] = useState(0);

  // Restore session on mount
  const effectiveId = sessionId ?? persistedId;
  useEffect(() => {
    if (effectiveId && token) {
      restoreSession(effectiveId);
    }
  }, [effectiveId, token, restoreSession]);

  // Refresh when nodeId param changes
  useEffect(() => {
    refreshSession();
  }, [nodeId, refreshSession]);

  useEffect(() => {
    setPageIndex(0);
    setActiveTimeLayer(0);
    setActionState(INITIAL_ACTION_STATE);
  }, [nodeId]);

  if (loading && !session) return <LoadingState label="加载章节…" />;
  if (error && !session) {
    return (
      <div className="flex min-h-dvh flex-col bg-paper px-4 py-8">
        <ErrorState
          message={error}
          onRetry={() => effectiveId && restoreSession(effectiveId)}
        />
      </div>
    );
  }
  if (!session) {
    return (
      <div className="flex min-h-dvh flex-col bg-paper px-4 py-8">
        <ErrorState message="未找到故事会话" />
      </div>
    );
  }

  const chapter = session.current_chapter;
  const allowedActions = session.allowed_actions;
  const isCompleted = session.status === "completed";

  // Determine chapter display
  const displayChapter: StoryChapter | null = chapter ?? null;
  if (!displayChapter) {
    return (
      <div className="flex min-h-dvh flex-col bg-paper px-4 py-8">
        <ErrorState
          message="无法加载当前章节"
          onRetry={refreshSession}
        />
      </div>
    );
  }

  const chapterComplete =
    session.state.completed_chapter_ids.includes(displayChapter.id) ||
    session.state.skipped_chapter_ids.includes(displayChapter.id);
  const attempts = session.state.attempts[displayChapter.id] ?? 0;

  // Node kinds that require arrival
  const needsArrive =
    displayChapter.poi_id &&
    !session.state.arrived_chapter_ids.includes(displayChapter.id) &&
    !chapterComplete;

  // Determine if puzzle is solved for this chapter
  const puzzleSolved =
    actionState.solved || chapterComplete;
  const puzzleSkipped =
    actionState.skipped ||
    session.state.skipped_chapter_ids.includes(displayChapter.id);

  /* ── Actions ── */

  const doAction = async (
    action: StoryAction,
    extra?: { answer?: unknown; choice_id?: string; reflection?: string },
  ) => {
    setActionState((s) => ({ ...s, busy: true, lastMessage: null, lastHint: null }));
    try {
      const res = await submitAction({
        action,
        chapter_id: displayChapter.id,
        ...extra,
      });
      setActionState((s) => ({
        ...s,
        busy: false,
        lastMessage: res.message,
        lastHint: res.hint ?? null,
        hintCount: s.hintCount + (action === "hint" ? 1 : 0),
        solved: action === "answer" && res.accepted ? true : s.solved,
        skipped: action === "skip" ? true : s.skipped,
      }));
      return res;
    } catch {
      setActionState((s) => ({ ...s, busy: false }));
      throw new Error("操作失败");
    }
  };

  const handleArrive = () => doAction("arrive");
  const handleContinue = () => {
    doAction("continue").then(() => {
      navigate(`/story-sessions/${effectiveId}/map`);
    });
  };
  const handleAnswer = (answer: unknown) => doAction("answer", { answer });
  const handleHint = () => doAction("hint");
  const handleSkip = () => doAction("skip");

  const handleBackToMap = () => {
    navigate(`/story-sessions/${effectiveId}/map`);
  };

  // Determine if node was advanced (after solve/skip/continue)
  const wasAdvanced = chapterComplete || puzzleSolved || puzzleSkipped;
  const pages = displayChapter.pages ?? [];
  const hasPages = pages.length > 0;
  const currentPage = hasPages ? pages[Math.min(pageIndex, pages.length - 1)] : null;
  const currentPageAssetSrc = storyAssetSrc(currentPage);
  const isLastPage = !hasPages || pageIndex >= pages.length - 1;
  const canAdvancePage = hasPages && pageIndex < pages.length - 1;
  const shouldShowPuzzle = !hasPages || currentPage?.kind === "puzzle";
  const handleNextPage = () =>
    setPageIndex((index) => Math.min(index + 1, Math.max(pages.length - 1, 0)));
  const handlePrevPage = () =>
    setPageIndex((index) => Math.max(index - 1, 0));

  return (
    <main className="flex min-h-dvh flex-col bg-paper text-ink">
      {/* Top bar */}
      <header className="sticky top-0 z-30 border-b border-line/80 bg-paper/95 px-4 py-3 backdrop-blur-md">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={handleBackToMap}
            className="text-sm text-ink-soft transition hover:text-ink"
          >
            ← 故事地图
          </button>
          <div className="text-center">
            <p className="text-xs text-ink-soft">
              {session.progress.completed_chapters}/{session.progress.total_chapters}
            </p>
          </div>
          <div className="w-12" aria-hidden />
        </div>
      </header>

      <div className="flex-1 overflow-auto px-4 py-4 pb-8 sm:mx-auto sm:max-w-lg sm:px-6">
        {/* Node title */}
        <div className="mb-5">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-ochre">
            {displayChapter.kind === "prologue"
              ? "序章"
              : displayChapter.kind === "transition"
                ? "过渡"
                : displayChapter.kind === "ending"
                  ? "终章"
                  : displayChapter.kind === "narrative"
                    ? "叙述"
                    : displayChapter.kind === "puzzle"
                      ? `章节 ${displayChapter.order}`
                      : "章节"}
          </p>
          <h2 className="mt-1 font-display text-xl leading-tight text-ink">
            {displayChapter.title}
          </h2>
          {displayChapter.story_time && (
            <p className="mt-1 text-sm text-ink-soft">{displayChapter.story_time}</p>
          )}
          {displayChapter.poi_id && (
            <p className="mt-1 text-xs text-sage-deep">
              地点：{displayChapter.location_name ?? displayChapter.poi_id}
            </p>
          )}
        </div>

        {/* Completed badge */}
        {chapterComplete && (
          <div className="mb-4 rounded-xl border border-sage-deep/30 bg-sage-deep/5 px-4 py-2.5 text-center text-sm font-medium text-sage-deep">
            {puzzleSkipped ? "已跳过" : "已完成"}
          </div>
        )}

        {/* Page-by-page script */}
        {hasPages && currentPage && (
          <section className="mb-5 overflow-hidden rounded-2xl border border-line bg-card">
            {currentPageAssetSrc && (
              <img
                src={currentPageAssetSrc}
                alt=""
                className="h-56 w-full object-cover"
                loading="lazy"
              />
            )}
            <div className="p-5">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-soft">
                  第 {pageIndex + 1} 页 / 共 {pages.length} 页
                </p>
                {currentPage.kind && (
                  <span className="rounded-full border border-line bg-paper-warm px-2.5 py-1 text-[10px] font-semibold text-sage-deep">
                    {currentPage.kind === "puzzle"
                      ? "谜题"
                      : currentPage.kind === "dialogue"
                        ? "对话"
                        : currentPage.kind === "transition"
                          ? "衔接"
                          : "剧情"}
                  </span>
                )}
              </div>
              {currentPage.title && (
                <h3 className="mt-3 font-serif text-lg font-semibold leading-tight text-ink">
                  {currentPage.title}
                </h3>
              )}
              {currentPage.speaker && (
                <p className="mt-3 text-xs font-semibold text-sage-deep">
                  {currentPage.speaker}
                </p>
              )}
              {currentPage.text && (
                <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-ink">
                  {currentPage.kind === "dialogue"
                    ? `"${currentPage.text}"`
                    : currentPage.text}
                </p>
              )}
              {pages.length > 1 && (
                <div className="mt-5 flex gap-3">
                  <button
                    type="button"
                    disabled={pageIndex === 0}
                    onClick={handlePrevPage}
                    className="rounded-full border border-line bg-paper px-4 py-2 text-sm text-ink-soft transition hover:border-sage hover:text-ink disabled:opacity-40"
                  >
                    上一页
                  </button>
                  {canAdvancePage && (
                    <button
                      type="button"
                      onClick={handleNextPage}
                      className="flex-1 rounded-full bg-sage-deep px-5 py-2 text-sm font-medium text-paper transition hover:bg-moss"
                    >
                      下一页
                    </button>
                  )}
                </div>
              )}
            </div>
          </section>
        )}

        {/* Scene / Narrative */}
        {!hasPages && displayChapter.scene && (
          <div className="mb-5 rounded-2xl border border-line bg-card p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-soft">
              场景
            </p>
            <p className="mt-2 text-sm leading-relaxed text-ink">
              {displayChapter.scene}
            </p>
          </div>
        )}

        {/* Dialogue */}
        {!hasPages && displayChapter.dialogue && displayChapter.dialogue.length > 0 && (
          <div className="mb-5 space-y-3">
            {displayChapter.dialogue.map((d, i) => (
              <div
                key={i}
                className="rounded-2xl border border-line bg-paper-warm p-4"
              >
                <p className="text-xs font-semibold text-sage-deep">{d.speaker}</p>
                <p className="mt-1 text-sm italic leading-relaxed text-ink-soft">
                  "{d.text}"
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Time Layers */}
        {!hasPages && displayChapter.time_layers && displayChapter.time_layers.length > 0 && (
          <div className="mb-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-soft">
              时间层
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {displayChapter.time_layers.map((tl, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setActiveTimeLayer(i)}
                  className={`rounded-full border px-3 py-1.5 text-xs transition ${
                    activeTimeLayer === i
                      ? "border-sage-deep bg-sage-deep text-paper"
                      : "border-line bg-paper text-ink-soft hover:border-sage"
                  }`}
                >
                  {tl.period}
                </button>
              ))}
            </div>
            <div className="mt-3 rounded-xl border border-line bg-card p-4">
              <p className="text-xs font-semibold text-sage-deep">
                {displayChapter.time_layers[activeTimeLayer].period}
              </p>
              <p className="mt-1 text-sm text-ink-soft">
                {displayChapter.time_layers[activeTimeLayer].focus}
              </p>
            </div>
          </div>
        )}

        {/* Knowledge Cards */}
        {!hasPages && displayChapter.knowledge_cards && displayChapter.knowledge_cards.length > 0 && (
          <div className="mb-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-soft">
              知识卡片
            </p>
            <div className="mt-2 space-y-2">
              {displayChapter.knowledge_cards.map((card, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-line bg-card p-4"
                >
                  <div className="flex items-center gap-2">
                    <span className="rounded-full border border-line bg-paper-warm px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-sage-deep">
                      {CONTENT_LABELS[card.kind] ?? card.kind}
                    </span>
                    <span className="text-sm font-medium text-ink">
                      {card.title}
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-relaxed text-ink-soft">
                    {card.text}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Fallback info */}
        {displayChapter.fallback && (
          <div className="mb-5 rounded-xl border border-ochre/30 bg-ochre/5 p-4">
            <p className="text-xs text-ink-soft">{displayChapter.fallback.text}</p>
          </div>
        )}

        {/* Action area */}
        <div className="mt-6">
          {isCompleted ? (
            <div className="rounded-2xl border border-line bg-card p-5 text-center">
              <p className="text-sm text-ink-soft">故事已完成</p>
              <button
                type="button"
                onClick={() =>
                  navigate(`/story-sessions/${effectiveId}/ending`)
                }
                className="mt-3 rounded-full bg-sage-deep px-5 py-2.5 text-sm font-medium text-paper"
              >
                查看结局
              </button>
            </div>
          ) : needsArrive ? (
            /* Arrival required */
            <div className="space-y-3">
              <p className="text-sm text-ink-soft text-center">
                请先到达此地点，然后确认
              </p>
              <button
                type="button"
                disabled={actionState.busy}
                onClick={handleArrive}
                className="w-full rounded-full bg-sage-deep px-6 py-4 text-base font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss active:scale-[0.99] disabled:opacity-50"
              >
                我已到达
              </button>
            </div>
          ) : wasAdvanced ? (
            /* Node completed / skipped — return to map */
            <div className="space-y-3">
              <div className="rounded-xl border border-sage-deep/30 bg-sage-deep/5 p-4 text-center">
                <p className="text-sm font-medium text-sage-deep">
                  {puzzleSkipped ? "已跳过此章节" : "章节完成"}
                </p>
                {actionState.lastMessage && (
                  <p className="mt-1 text-sm text-ink-soft">
                    {actionState.lastMessage}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={handleBackToMap}
                className="w-full rounded-full bg-sage-deep px-6 py-3.5 text-sm font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss active:scale-[0.99]"
              >
                返回故事地图
              </button>
            </div>
          ) : canAdvancePage && !shouldShowPuzzle ? (
            /* Page mode — read forward before the action */
            <button
              type="button"
              onClick={handleNextPage}
              className="w-full rounded-full bg-sage-deep px-6 py-4 text-base font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss active:scale-[0.99]"
            >
              下一页
            </button>
          ) : allowedActions.includes("answer") && shouldShowPuzzle ? (
            /* Puzzle node */
            <PuzzlePanel
              puzzle={displayChapter.puzzle!}
              disabled={actionState.busy}
              onSubmitAnswer={handleAnswer}
              onRequestHint={handleHint}
              onSkip={handleSkip}
              attempts={attempts}
              lastHint={actionState.lastHint}
              lastMessage={actionState.lastMessage}
            />
          ) : allowedActions.includes("answer") && canAdvancePage ? (
            <button
              type="button"
              onClick={handleNextPage}
              className="w-full rounded-full bg-sage-deep px-6 py-4 text-base font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss active:scale-[0.99]"
            >
              前往谜题页
            </button>
          ) : allowedActions.includes("continue") && !isLastPage ? (
            <button
              type="button"
              onClick={handleNextPage}
              className="w-full rounded-full bg-sage-deep px-6 py-4 text-base font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss active:scale-[0.99]"
            >
              下一页
            </button>
          ) : allowedActions.includes("continue") ? (
            /* Prologue / Narrative / Transition */
            <button
              type="button"
              disabled={actionState.busy}
              onClick={handleContinue}
              className="w-full rounded-full bg-sage-deep px-6 py-4 text-base font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss active:scale-[0.99] disabled:opacity-50"
            >
              {actionState.busy ? "处理中…" : "继续"}
            </button>
          ) : allowedActions.includes("choose_ending") && !isLastPage ? (
            <button
              type="button"
              onClick={handleNextPage}
              className="w-full rounded-full bg-sage-deep px-6 py-4 text-base font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss active:scale-[0.99]"
            >
              下一页
            </button>
          ) : allowedActions.includes("choose_ending") ? (
            /* Ending — go to ending page */
            <button
              type="button"
              onClick={() =>
                navigate(`/story-sessions/${effectiveId}/ending`)
              }
              className="w-full rounded-full bg-ochre px-6 py-4 text-base font-medium text-paper shadow-[var(--shadow-soft)] transition hover:opacity-90 active:scale-[0.99]"
            >
              选择结局
            </button>
          ) : (
            /* Unknown state */
            <div className="rounded-2xl border border-line bg-card p-5 text-center">
              <p className="text-sm text-ink-soft">暂无可用操作</p>
              <button
                type="button"
                onClick={handleBackToMap}
                className="mt-3 rounded-full border border-line px-5 py-2.5 text-sm text-ink transition hover:border-sage"
              >
                返回故事地图
              </button>
            </div>
          )}
        </div>

        {/* Action feedback */}
        {actionState.lastMessage && wasAdvanced && (
          <div className="mt-4 rounded-xl border border-sage-deep/30 bg-sage-deep/5 p-4">
            <p className="text-sm text-sage-deep">{actionState.lastMessage}</p>
          </div>
        )}
      </div>

      {/* Reward reveal modal */}
      {latestRewards.length > 0 && (
        <RewardReveal rewards={latestRewards} onDismiss={clearLatestRewards} />
      )}
    </main>
  );
}
