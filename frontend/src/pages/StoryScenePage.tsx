import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { ErrorState, LoadingState } from "@/components/common/States";
import { PuzzlePanel } from "@/components/story/PuzzlePanel";
import { RewardReveal } from "@/components/story/RewardReveal";
import { StoryImage } from "@/features/story/assets";
import { DialoguePlayer } from "@/features/story/components/DialoguePlayer";
import { KnowledgeCard } from "@/features/story/components/KnowledgeCard";
import { StoryAgentDrawer } from "@/features/story/components/StoryAgentDrawer";
import { StoryBottomAction } from "@/features/story/components/StoryBottomAction";
import { StoryComicReader } from "@/features/story/components/StoryComicReader";
import { StoryImageViewer } from "@/features/story/components/StoryImageViewer";
import { StoryTopBar } from "@/features/story/components/StoryTopBar";
import { useStoryMessages } from "@/features/story/storyI18n";
import { useAuth } from "@/state/AuthContext";
import { useStory, useStoryRestore } from "@/state/StoryContext";
import type {
  StoryActionResponse,
  StoryAgentContext,
  StoryAssetRef,
  StoryChapter,
} from "@/types/stories";

interface ViewerState {
  assetId: string;
  alt?: string;
  caption?: string;
}

function isRewardAsset(assetId: string): boolean {
  return new Set([
    "V4-AMA-05",
    "V4-MAN-06",
    "V4-SEN-05",
    "V4-SAM-06",
    "V4-LOU-05",
    "V4-LOU-06",
    "V4-FOR-08",
  ]).has(assetId);
}

const ENDING_PAGE_ONLY_ASSETS = new Set(["V4-FOR-07", "V4-FOR-09"]);

const PROLOGUE_AGENT_CONTEXT: StoryAgentContext = {
  persona: "阿莲",
  poi_name: "旧书与城市双图",
  chapter_goal: "帮助玩家理解旧书、双图和第一张密笺的用途",
  known_facts: [
    "1923年《香山县志续编》是真实存在的地方志",
    "故事中的家藏版本、信封、双图、纸条、阿澜与M先生均为剧情虚构",
    "双图记录的侧重点不同，后续需要结合现场逐站核对",
  ],
  fiction_boundaries: [
    "不得把剧情中的夹藏材料、人物和地图描述成真实文物或史实",
  ],
  suggested_questions: [
    "这本古书是什么？",
    "两张地图应该怎样一起使用？",
    "为什么第一站要去妈阁庙？",
  ],
  do_not_reveal: [
    "不得提前说明后续谜题答案",
    "不得提前透露未到达章节的剧情发现",
  ],
};

function chapterPetalCount(rewards: Array<{ kind: string }>): number {
  return rewards.filter((reward) => reward.kind === "note_petal").length;
}

export function StoryScenePage() {
  const { sessionId, nodeId } = useParams<{
    sessionId: string;
    nodeId: string;
  }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { token, isRestoring } = useAuth();
  const {
    session,
    latestRewards,
    submittedChapterSnapshot,
    lastActionResult,
    loading,
    actionPending,
    error,
    errorStatus,
    restoreSession,
    refreshSession,
    submitAction,
    clearLatestRewards,
    clearLastAction,
    clearError,
  } = useStory();
  const { sessionId: effectiveId } = useStoryRestore(sessionId);
  const st = useStoryMessages();

  const [comicIndex, setComicIndex] = useState(0);
  const [comicDone, setComicDone] = useState(false);
  const [dialogueDone, setDialogueDone] = useState(false);
  const [viewer, setViewer] = useState<ViewerState | null>(null);
  const [agentOpen, setAgentOpen] = useState(false);
  const [overlayOpacity, setOverlayOpacity] = useState(55);
  const [arrivalMessage, setArrivalMessage] = useState<string | null>(null);

  const advancedSnapshot =
    submittedChapterSnapshot &&
    lastActionResult &&
    submittedChapterSnapshot.id !== session?.current_chapter_id
      ? submittedChapterSnapshot
      : null;
  const displayChapter: StoryChapter | null =
    advancedSnapshot ?? session?.current_chapter ?? null;

  useEffect(() => {
    if (!isRestoring && !token) {
      const returnTo = `${location.pathname}${location.search}`;
      navigate(`/auth?returnTo=${encodeURIComponent(returnTo)}`, { replace: true });
    }
  }, [isRestoring, location.pathname, location.search, navigate, token]);

  useEffect(() => {
    if (effectiveId && token && session?.session_id !== effectiveId) {
      void restoreSession(effectiveId);
    }
  }, [effectiveId, restoreSession, session?.session_id, token]);

  useEffect(() => {
    if (!session || !nodeId) return;
    if (session.status === "completed") {
      navigate(`/story-sessions/${session.session_id}/ending`, { replace: true });
      return;
    }
    if (advancedSnapshot?.id === nodeId) return;
    if (session.current_chapter_id !== nodeId) {
      navigate(`/story-sessions/${session.session_id}/map`, { replace: true });
    }
  }, [advancedSnapshot?.id, navigate, nodeId, session]);

  useEffect(() => {
    setComicIndex(0);
    setComicDone(false);
    setDialogueDone(false);
    setOverlayOpacity(55);
    setArrivalMessage(null);
  }, [displayChapter?.id]);

  const comics = displayChapter?.arrival_comic ?? [];
  const currentComic = comics[comicIndex];
  const comicAssetIds = useMemo(
    () => new Set(comics.map((comic) => comic.asset_id)),
    [comics],
  );
  const clueAssets = useMemo(
    () =>
      (displayChapter?.presentation?.assets ?? []).filter(
        (assetId) =>
          !comicAssetIds.has(assetId) &&
          !assetId.startsWith("V4-CHAR") &&
          !isRewardAsset(assetId) &&
          !ENDING_PAGE_ONLY_ASSETS.has(assetId),
      ),
    [comicAssetIds, displayChapter?.presentation?.assets],
  );

  const openComic = (comic: StoryAssetRef) => {
    setViewer({
      assetId: comic.asset_id,
      alt: comic.alt,
      caption: comic.caption,
    });
  };

  const runAction = async (
    request: Parameters<typeof submitAction>[0],
  ): Promise<StoryActionResponse | null> => {
    clearError();
    try {
      return await submitAction(request);
    } catch {
      return null;
    }
  };

  const handleArrive = async () => {
    if (!displayChapter) return;
    const response = await runAction({
      action: "arrive",
      chapter_id: displayChapter.id,
    });
    if (response) {
      setArrivalMessage(response.message);
      clearLastAction();
    }
  };

  const handleContinue = async () => {
    if (!displayChapter) return;
    await runAction({
      action: "continue",
      chapter_id: displayChapter.id,
    });
  };

  const handleAnswer = async (answer: unknown) => {
    if (!displayChapter) return;
    await runAction({
      action: "answer",
      chapter_id: displayChapter.id,
      answer,
    });
  };

  const handleHint = async () => {
    if (!displayChapter) return;
    await runAction({
      action: "hint",
      chapter_id: displayChapter.id,
    });
  };

  const handleSkip = async () => {
    if (!displayChapter) return;
    await runAction({
      action: "skip",
      chapter_id: displayChapter.id,
    });
  };

  const handleNextStop = () => {
    if (!session) return;
    clearLatestRewards();
    clearLastAction();
    navigate(`/story-sessions/${session.session_id}/map`);
  };

  if ((loading || isRestoring) && !session) {
    return <LoadingState label={st("loadingChapter")} />;
  }

  if (!session || !displayChapter) {
    const invalidSession = errorStatus === 403 || errorStatus === 404;
    return (
      <main className="grid min-h-dvh place-items-center bg-paper px-4">
        <div className="w-full max-w-[480px]">
          <ErrorState
            message={
              invalidSession
                ? st("storyUnavailable")
                : error ?? st("loadingChapter")
            }
            onRetry={
              effectiveId && !invalidSession
                ? () => void restoreSession(effectiveId)
                : undefined
            }
          />
          <button
            type="button"
            onClick={() => navigate("/stories/lotus_city_double_map")}
            className="mt-4 min-h-12 w-full rounded-full bg-sage-deep px-5 text-base font-medium text-paper"
          >
            {st("back")}
          </button>
        </div>
      </main>
    );
  }

  const hasArrived = session.state.arrived_chapter_ids.includes(displayChapter.id);
  const needsArrival =
    Boolean(displayChapter.poi_id) &&
    !hasArrived &&
    !advancedSnapshot;
  const hasDialogue = Boolean(displayChapter.dialogue?.length);
  const isEndingChapter = displayChapter.kind === "ending";
  const narrativeReady =
    (comics.length === 0 || comicDone) &&
    (!hasDialogue || dialogueDone || isEndingChapter);
  const isPuzzleChapter =
    displayChapter.kind === "puzzle" && Boolean(displayChapter.puzzle);
  const petalCount = chapterPetalCount(session.state.rewards);
  const chapterNumber =
    displayChapter.order === 0
      ? st("prologue")
      : displayChapter.order <= 6
        ? st("chapter", { order: displayChapter.order })
        : st("loadingChapterTitle");
  const lastResultForChapter =
    lastActionResult && submittedChapterSnapshot?.id === displayChapter.id
      ? lastActionResult
      : null;
  const sourceAgentContext =
    displayChapter.agent_context ??
    (displayChapter.kind === "prologue" ? PROLOGUE_AGENT_CONTEXT : undefined);
  const agentContext = sourceAgentContext
    ? {
        ...sourceAgentContext,
        chapter_title: displayChapter.title,
      }
    : undefined;

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col bg-paper text-ink shadow-[var(--shadow-soft)]">
      <StoryTopBar
        title={displayChapter.location_name ?? displayChapter.title}
        eyebrow={chapterNumber}
        petals={petalCount}
        onBack={() => navigate(`/story-sessions/${session.session_id}/map`)}
        onAskAgent={agentContext ? () => setAgentOpen(true) : undefined}
      />

      <div className="flex-1 px-4 pb-32 pt-4">
        <div className="landscape-story-hint mb-4 hidden rounded-xl border border-ochre/30 bg-ochre/5 p-3 text-center text-sm text-ink-soft">
          {st("landscapeHint")}
        </div>

        <header className="mb-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-ochre">
            {displayChapter.story_time ?? "莲城双图"}
          </p>
          <h1 className="mt-1 font-display text-2xl leading-tight">
            {displayChapter.title}
          </h1>
          {displayChapter.location_name && (
            <p className="mt-2 text-base text-sage-deep">
              {st("location", { name: displayChapter.location_name })}
            </p>
          )}
        </header>

        {needsArrival ? (
          <section>
            {currentComic ? (
              <StoryImage
                assetId={currentComic.asset_id}
                alt={currentComic.alt}
                eager
                onOpen={() => openComic(currentComic)}
              />
            ) : (
              <StoryImage
                assetId={displayChapter.presentation?.assets[0] ?? "V4-PROP-03"}
                alt={displayChapter.location_name ?? displayChapter.title}
                eager
                onOpen={(assetId) => setViewer({ assetId })}
              />
            )}
            <div className="mt-4 rounded-2xl border border-line bg-card p-4">
              <h2 className="font-serif text-lg font-semibold">{st("arrivalCheck")}</h2>
              <p className="mt-2 text-base leading-7 text-ink-soft">
                {st("arrivalSafety")}
              </p>
              {error && (
                <p role="alert" className="mt-3 text-sm text-clay">
                  {error}
                </p>
              )}
            </div>
          </section>
        ) : advancedSnapshot ? (
          <section className="space-y-4">
            <div className="rounded-3xl border border-sage-deep/30 bg-sage-deep/5 p-5 text-center">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-sage-deep">
                {session.state.skipped_chapter_ids.includes(displayChapter.id)
                  ? st("skipped")
                  : displayChapter.kind === "prologue"
                    ? st("routeOpened")
                    : st("chapterCompleted")}
              </p>
              <h2 className="mt-2 font-serif text-xl font-semibold">
                {lastActionResult?.message ?? st("progressSaved")}
              </h2>
              <p className="mt-2 text-base leading-7 text-ink-soft">
                {st("progressKeeps")}
              </p>
            </div>
          </section>
        ) : (
          <>
            {displayChapter.scene && (
              <section className="rounded-2xl border border-line bg-card p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-sage-deep">
                  {st("scene")}
                </p>
                <p className="mt-2 text-base leading-7 text-ink-soft">
                  {displayChapter.scene}
                </p>
              </section>
            )}

            {arrivalMessage && (
              <p className="mt-3 rounded-xl border border-sage/30 bg-sage/10 p-3 text-sm text-sage-deep">
                {arrivalMessage}
              </p>
            )}

            {!comicDone && currentComic && (
              <StoryComicReader
                comics={comics}
                index={comicIndex}
                onIndexChange={setComicIndex}
                onComplete={() => setComicDone(true)}
                onOpen={openComic}
              />
            )}

            {(comicDone || comics.length === 0) &&
              !isEndingChapter &&
              !dialogueDone &&
              displayChapter.dialogue &&
              displayChapter.dialogue.length > 0 && (
                <section className="mt-5">
                  <DialoguePlayer
                    lines={displayChapter.dialogue}
                    chapterId={displayChapter.id}
                    continueLabel="继续观察"
                    onComplete={() => setDialogueDone(true)}
                  />
                </section>
              )}

            {narrativeReady && (
              <>
                {clueAssets.length > 0 && (
                  <section className="mt-5">
                    <h2 className="font-serif text-xl font-semibold">{st("observations")}</h2>
                    <div className="mt-3 grid gap-3">
                      {clueAssets.map((assetId) => (
                        <StoryImage
                          key={assetId}
                          assetId={assetId}
                          alt={displayChapter.location_name ?? displayChapter.title}
                          onOpen={(openedAssetId) =>
                            setViewer({ assetId: openedAssetId })
                          }
                        />
                      ))}
                    </div>
                  </section>
                )}

                {displayChapter.knowledge_cards &&
                  displayChapter.knowledge_cards.length > 0 && (
                    <section className="mt-5">
                      <h2 className="font-serif text-xl font-semibold">{st("knowledgeCards")}</h2>
                      <div className="mt-3 space-y-3">
                        {displayChapter.knowledge_cards.map((card) => (
                          <KnowledgeCard
                            key={`${card.kind}-${card.title}`}
                            card={card}
                          />
                        ))}
                      </div>
                    </section>
                  )}

                {displayChapter.fallback && (
                  <div className="mt-4 rounded-xl border border-ochre/30 bg-ochre/5 p-4">
                    <p className="text-base leading-7 text-ink-soft">
                      {displayChapter.fallback.text}
                    </p>
                  </div>
                )}

                {isPuzzleChapter && displayChapter.puzzle && (
                  <section className="mt-6" aria-labelledby="chapter-puzzle-title">
                    <h2 id="chapter-puzzle-title" className="font-serif text-xl font-semibold">
                      {st("puzzleQuestion")}
                    </h2>
                    <div className="mt-3">
                      <PuzzlePanel
                        puzzle={displayChapter.puzzle}
                        disabled={actionPending}
                        onSubmitAnswer={(answer) => void handleAnswer(answer)}
                        onRequestHint={() => void handleHint()}
                        onSkip={() => void handleSkip()}
                        attempts={session.state.attempts[displayChapter.id] ?? 0}
                        lastHint={lastResultForChapter?.hint}
                        lastMessage={lastResultForChapter?.message}
                      />
                    </div>
                  </section>
                )}

                {isEndingChapter && (
                  <>
                    <section className="mt-6 rounded-2xl border border-line bg-card p-4">
                      <h2 className="font-serif text-xl font-semibold">{st("combineMaps")}</h2>
                      <p className="mt-2 text-base leading-7 text-ink-soft">
                        {st("combineMapsBody")}
                      </p>
                      <div className="relative mt-4 overflow-hidden rounded-2xl border border-line bg-paper-warm">
                        <StoryImage
                          assetId="V4-PROP-03"
                          alt={st("cityMaps")}
                          className="rounded-none border-0"
                        />
                        <div
                          className="absolute inset-0"
                          style={{ opacity: overlayOpacity / 100 }}
                        >
                          <StoryImage
                            assetId="V4-FOR-03"
                            alt={st("cityMaps")}
                            className="rounded-none border-0"
                          />
                        </div>
                      </div>
                      <label htmlFor="map-overlay" className="mt-4 block text-sm font-medium text-sage-deep">
                        {st("opacity", { value: overlayOpacity })}
                      </label>
                      <input
                        id="map-overlay"
                        type="range"
                        min={0}
                        max={100}
                        value={overlayOpacity}
                        onChange={(event) => setOverlayOpacity(Number(event.target.value))}
                        className="mt-2 min-h-11 w-full accent-sage-deep"
                      />
                      <button
                        type="button"
                        onPointerDown={() => setOverlayOpacity(100)}
                        onPointerUp={() => setOverlayOpacity(70)}
                        onPointerCancel={() => setOverlayOpacity(70)}
                        className="mt-3 min-h-12 w-full rounded-full border border-sage-deep/30 bg-sage-deep/5 px-5 text-base font-medium text-sage-deep"
                      >
                        {st("holdOverlay")}
                      </button>
                      <div className="mt-4 border-t border-line pt-4">
                        <StoryImage
                          assetId="V4-FOR-08"
                          alt={st("petalsComplete")}
                          onOpen={(assetId) => setViewer({ assetId })}
                          className="mx-auto max-w-64"
                          imageClassName="object-contain"
                        />
                        <p className="mt-2 text-center text-sm leading-6 text-ink-soft">
                          {st("petalsComplete")}
                        </p>
                      </div>
                    </section>

                    {!dialogueDone &&
                      displayChapter.dialogue &&
                      displayChapter.dialogue.length > 0 && (
                        <section className="mt-5">
                          <DialoguePlayer
                            lines={displayChapter.dialogue}
                            chapterId={displayChapter.id}
                            continueLabel="完成回顾"
                            onComplete={() => setDialogueDone(true)}
                          />
                        </section>
                      )}
                  </>
                )}
              </>
            )}

            {error && (
              <div
                role="alert"
                className="mt-4 rounded-xl border border-clay/30 bg-clay/5 p-3 text-sm text-clay"
              >
                {errorStatus === 409
                  ? "进度已在其他页面更新，请重新载入最新章节。"
                  : errorStatus === 422
                    ? "提交内容格式不正确，你的当前选择仍然保留。"
                    : error}
                {errorStatus === 409 && (
                  <button
                    type="button"
                    onClick={() => void refreshSession()}
                    className="ml-2 min-h-11 rounded-full border border-clay/30 px-3"
                  >
                    重新载入
                  </button>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {needsArrival && (
        <StoryBottomAction
          label={st("arrived")}
          busy={actionPending}
          busyLabel={st("confirmingArrival")}
          onClick={() => void handleArrive()}
          hint={st("arrivalHint")}
        />
      )}

      {!needsArrival &&
        !advancedSnapshot &&
        narrativeReady &&
        displayChapter.kind === "prologue" && (
          <StoryBottomAction
            label={st("goToAmaze")}
            busy={actionPending}
            busyLabel={st("preparing")}
            onClick={() => void handleContinue()}
          />
        )}

      {!needsArrival &&
        !advancedSnapshot &&
        narrativeReady &&
        isEndingChapter &&
        (!hasDialogue || dialogueDone) && (
          <StoryBottomAction
            label={st("writeNote")}
            onClick={() =>
              navigate(`/story-sessions/${session.session_id}/ending`)
            }
            tone="accent"
          />
        )}

      {advancedSnapshot && latestRewards.length === 0 && (
        <StoryBottomAction label="查看下一站" onClick={handleNextStop} />
      )}

      {latestRewards.length > 0 && (
        <RewardReveal
          rewards={latestRewards}
          onDismiss={handleNextStop}
        />
      )}
      <StoryAgentDrawer
        open={agentOpen}
        context={agentContext}
        onClose={() => setAgentOpen(false)}
      />
      <StoryImageViewer
        assetId={viewer?.assetId ?? null}
        alt={viewer?.alt}
        caption={viewer?.caption}
        onClose={() => setViewer(null)}
      />
    </main>
  );
}
