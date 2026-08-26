import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import {
  fetchFutureLetter,
  fetchFutureLetterImage,
  generateFutureLetter,
  isStoryApiError,
} from "@/api/stories";
import { ErrorState, LoadingState } from "@/components/common/States";
import { StoryImage } from "@/features/story/assets";
import { ChapterRecapDialog } from "@/features/story/components/ChapterRecapDialog";
import { StoryAgentDrawer } from "@/features/story/components/StoryAgentDrawer";
import { StoryBottomAction } from "@/features/story/components/StoryBottomAction";
import { StoryImageViewer } from "@/features/story/components/StoryImageViewer";
import { PetalProgress } from "@/features/story/components/PetalProgress";
import { StoryTopBar } from "@/features/story/components/StoryTopBar";
import { useStoryMessages } from "@/features/story/storyI18n";
import { navigateBack } from "@/lib/backNavigation";
import { useAuth } from "@/state/AuthContext";
import { useStory, useStoryRestore } from "@/state/StoryContext";
import { useWalk } from "@/state/WalkContext";
import type { FutureLetterResponse, StoryNodeOverview } from "@/types/stories";

export function StoryEndingPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { token, isRestoring } = useAuth();
  const {
    story,
    session,
    submittedChapterSnapshot,
    loading,
    actionPending,
    error,
    errorStatus,
    restoreSession,
    refreshSession,
    loadStory,
    submitAction,
  } = useStory();
  const { language } = useWalk();
  const { sessionId: effectiveId } = useStoryRestore(sessionId);
  const st = useStoryMessages();
  const futureLetterErrorMessage = (requestError: unknown): string => {
    if (isStoryApiError(requestError, 503)) return st("futureLetterUnavailable");
    if (isStoryApiError(requestError, 409)) return st("futureLetterConflict");
    return requestError instanceof Error ? requestError.message : st("futureLetterError");
  };
  const [reflection, setReflection] = useState("");
  const [viewerAssetId, setViewerAssetId] = useState<string | null>(null);
  const [agentOpen, setAgentOpen] = useState(false);
  const [summaryNode, setSummaryNode] = useState<StoryNodeOverview | null>(null);
  const [futureLetter, setFutureLetter] = useState<FutureLetterResponse | null>(null);
  const [futureLetterImageUrl, setFutureLetterImageUrl] = useState<string | null>(null);
  const [futureLetterChecking, setFutureLetterChecking] = useState(false);
  const [futureLetterGenerating, setFutureLetterGenerating] = useState(false);
  const [futureLetterError, setFutureLetterError] = useState<string | null>(null);

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
    if (session && story?.id !== session.story_id) {
      void loadStory(session.story_id);
    }
  }, [loadStory, session, story?.id]);

  useEffect(() => {
    if (
      session?.status === "active" &&
      session.current_chapter?.kind === "ending" &&
      !session.state.arrived_chapter_ids.includes(session.current_chapter.id)
    ) {
      navigate(
        `/story-sessions/${session.session_id}/nodes/${session.current_chapter.id}`,
        { replace: true },
      );
    }
  }, [navigate, session]);

  useEffect(() => {
    if (session?.state.ending_reflection && !reflection) {
      setReflection(session.state.ending_reflection);
    }
  }, [reflection, session?.state.ending_reflection]);

  const finalChapter =
    session?.current_chapter?.kind === "ending"
      ? session.current_chapter
      : submittedChapterSnapshot?.kind === "ending"
        ? submittedChapterSnapshot
        : null;
  const endingChoice = useMemo(
    () =>
      finalChapter?.ending_options?.find(
        (option) => option.id === "complete_today_note",
      ) ?? finalChapter?.ending_options?.[0],
    [finalChapter?.ending_options],
  );
  const isCompleted = session?.status === "completed";
  const isLotusStory = session?.story_id === "lotus_city_double_map";
  const isTaipaStory = session?.story_id === "taipa_letters";

  useEffect(() => {
    if (!isCompleted || !isTaipaStory || !session || !token) return;
    let cancelled = false;
    setFutureLetterChecking(true);
    setFutureLetterError(null);
    void fetchFutureLetter(session.session_id, token)
      .then(async (letter) => {
        if (!letter || cancelled) return;
        const image = await fetchFutureLetterImage(session.session_id, token, language);
        if (cancelled) return;
        setFutureLetter(letter);
        setFutureLetterImageUrl(URL.createObjectURL(image));
      })
      .catch((requestError: unknown) => {
        if (!cancelled) setFutureLetterError(futureLetterErrorMessage(requestError));
      })
      .finally(() => {
        if (!cancelled) setFutureLetterChecking(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isCompleted, isTaipaStory, language, session, token]);

  useEffect(
    () => () => {
      if (futureLetterImageUrl) URL.revokeObjectURL(futureLetterImageUrl);
    },
    [futureLetterImageUrl],
  );

  const petalCount =
    session?.state.rewards.filter((reward) => reward.kind === "note_petal").length ?? 0;
  const completionAgentContext = useMemo(
    () => ({
      persona: st("alianName"),
      poi_name: isLotusStory
        ? st("macauHistoricCentre")
        : isTaipaStory
          ? st("taipaOldTown")
          : st("coloanePlace"),
      chapter_title: story?.title ?? st("journeyComplete"),
      chapter_goal: isLotusStory
        ? st("lotusReviewGoal")
        : isTaipaStory
          ? st("taipaReviewGoal")
          : st("coloaneReviewGoal"),
      known_facts: [
        story?.summary,
        session?.ending?.text,
      ].filter((value): value is string => Boolean(value)),
      fiction_boundaries: story?.content_notice ? [story.content_notice] : [],
      suggested_questions: isLotusStory
        ? [
            st("lotusReviewQuestion"),
            st("mapReviewQuestion"),
            st("factFictionQuestion"),
          ]
        : isTaipaStory
          ? [
              st("taipaReviewQuestion"),
              st("factFictionQuestion"),
            ]
          : [
              st("coloaneReviewQuestion"),
              st("factFictionQuestion"),
            ],
      do_not_reveal: [],
    }),
    [
      isLotusStory,
      isTaipaStory,
      session?.ending?.text,
      st,
      story?.content_notice,
      story?.summary,
      story?.title,
    ],
  );

  const completeTodayNote = async () => {
    if (!session || !finalChapter || !endingChoice || actionPending) return;
    try {
      await submitAction({
        action: "choose_ending",
        chapter_id: finalChapter.id,
        choice_id: endingChoice.id,
        reflection: reflection.trim() || undefined,
      });
    } catch {
      // Structured context error remains visible and the draft is preserved.
    }
  };

  const generateTaipaFutureLetter = async () => {
    if (!session || !token || futureLetterGenerating) return;
    setFutureLetterGenerating(true);
    setFutureLetterError(null);
    try {
      const letter = await generateFutureLetter(session.session_id, token, language);
      const image = await fetchFutureLetterImage(session.session_id, token, language);
      setFutureLetter(letter);
      setFutureLetterImageUrl(URL.createObjectURL(image));
    } catch (requestError) {
      setFutureLetterError(futureLetterErrorMessage(requestError));
    } finally {
      setFutureLetterGenerating(false);
    }
  };

  if ((loading || isRestoring) && !session) {
    return <LoadingState label={st("loadingChapter")} />;
  }

  if (!session) {
    const invalidSession = errorStatus === 403 || errorStatus === 404;
    return (
      <main className="grid min-h-dvh place-items-center bg-paper px-4">
        <div className="w-full max-w-[480px]">
          <ErrorState
            message={
              invalidSession
                ? st("storyUnavailable")
                : error ?? st("loadingRoute")
            }
            onRetry={
              effectiveId && !invalidSession
                ? () => void restoreSession(effectiveId)
                : undefined
            }
          />
          <button
            type="button"
            onClick={() => navigateBack(navigate, location.key)}
            className="mt-4 min-h-12 w-full rounded-full bg-sage-deep px-5 text-base font-medium text-paper"
          >
            {st("back")}
          </button>
        </div>
      </main>
    );
  }

  const agentContext =
    finalChapter?.agent_context
      ? {
          ...finalChapter.agent_context,
          chapter_title: finalChapter.title,
        }
      : isCompleted
        ? completionAgentContext
        : undefined;
  const stationNodes = story?.nodes.filter((node) => node.poi_id) ?? [];
  const collectibleRewards = session.state.rewards.filter(
    (reward) =>
      reward.kind !== "story_prop" &&
      reward.kind !== "collection" &&
      reward.kind !== "reflection",
  );
  const summaryIndex = summaryNode
    ? stationNodes.findIndex((node) => node.id === summaryNode.id)
    : -1;
  const summaryReward =
    summaryNode?.kind === "ending"
      ? session.state.rewards.find(
          (reward) =>
            reward.id === "complete_city_flower" ||
            reward.kind === "collection",
        )
      : summaryIndex >= 0
        ? collectibleRewards[summaryIndex]
        : undefined;
  const endingAssets = finalChapter?.presentation?.assets ?? [];
  const activeEndingAsset =
    endingAssets[endingAssets.length - 1] ??
    story?.presentation.cover_asset_id ??
    "V4-FOR-07";

  if (isCompleted) {
    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col bg-paper text-ink shadow-[var(--shadow-soft)]">
        <StoryTopBar
          title={story?.title ?? st("journeyComplete")}
          eyebrow={st("journeyComplete")}
          petals={isLotusStory ? petalCount : undefined}
          onBack={() => navigate("/preferences")}
          onAskAgent={agentContext ? () => setAgentOpen(true) : undefined}
        />

        <div className="flex-1 px-4 pb-28 pt-4">
          {isTaipaStory && futureLetterImageUrl ? (
            <img
              src={futureLetterImageUrl}
              alt={st("taipaFutureLetterAlt")}
              className="aspect-[9/16] w-full rounded-2xl border border-line bg-card object-contain shadow-[var(--shadow-soft)]"
            />
          ) : (
            <StoryImage
              assetId={
                isLotusStory
                  ? "V4-FOR-09"
                  : isTaipaStory
                    ? activeEndingAsset
                    : "CAT-END-01"
              }
              alt={
                isLotusStory
                  ? st("lotusSunsetAlt")
                  : isTaipaStory
                    ? st("taipaFutureLetterAlt")
                    : st("coloanePostcardAlt")
              }
              eager
              onOpen={setViewerAssetId}
              imageClassName="object-contain"
            />
          )}

          <section className="relative mt-4 rounded-3xl border border-line bg-paper p-5 text-center shadow-[var(--shadow-lift)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-ochre">
              {session.ending?.title ?? st("journeyComplete")}
            </p>
            <h1 className="mt-2 font-display text-3xl">
              {session.ending?.title ?? st("noteToday")}
            </h1>
            <p className="mt-3 text-base leading-7 text-ink-soft">
              {session.ending?.text ??
                st("noteBody")}
            </p>
          </section>

          {isTaipaStory && (
            <section
              className="mt-4 rounded-2xl border border-sage-deep/25 bg-sage-deep/5 p-4"
              aria-labelledby="future-letter-art-title"
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-sage-deep">
                {st("futureLetterArtwork")}
              </p>
              <h2 id="future-letter-art-title" className="mt-1 font-serif text-xl font-semibold">
                {futureLetter ? st("futureLetterReadyTitle") : st("futureLetterGenerateTitle")}
              </h2>
              <p className="mt-2 text-sm leading-6 text-ink-soft">
                {futureLetter
                  ? st("futureLetterReadyBody")
                  : st("futureLetterGenerateBody")}
              </p>

              {futureLetter?.reflection_truncated && (
                <p className="mt-2 rounded-xl bg-ochre/10 px-3 py-2 text-xs leading-5 text-ink-soft">
                  {st("futureLetterTruncated")}
                </p>
              )}

              {futureLetterError && (
                <p role="alert" className="mt-3 rounded-xl bg-clay/10 px-3 py-2 text-sm text-clay">
                  {futureLetterError}
                </p>
              )}

              {!futureLetter && (
                <button
                  type="button"
                  onClick={() => void generateTaipaFutureLetter()}
                  disabled={futureLetterChecking || futureLetterGenerating}
                  className="mt-4 min-h-12 w-full rounded-full bg-sage-deep px-5 font-medium text-paper disabled:cursor-wait disabled:opacity-55"
                >
                  {futureLetterChecking
                    ? st("futureLetterChecking")
                    : futureLetterGenerating
                      ? st("futureLetterGenerating")
                      : futureLetterError
                        ? st("futureLetterRetry")
                        : st("futureLetterGenerate")}
                </button>
              )}

              {futureLetter && (
                <p className="mt-3 text-xs text-ink-soft">
                  {st("futureLetterDisclosure")}
                </p>
              )}
            </section>
          )}

          <section className="mt-4 grid grid-cols-2 gap-3">
            <StoryImage
              assetId={
                isLotusStory
                  ? "V4-FOR-08"
                  : isTaipaStory
                    ? activeEndingAsset
                    : "CAT-END-01"
              }
              alt={
                isLotusStory
                  ? st("petalsComplete")
                  : isTaipaStory
                    ? st("taipaFutureLetterAlt")
                    : st("coloanePostcardAlt")
              }
              onOpen={setViewerAssetId}
            />
            <StoryImage
              assetId={
                isLotusStory
                  ? "V4-PROP-05"
                  : isTaipaStory
                    ? "TAI-PROP-01"
                    : "CAT-PROP-01"
              }
              alt={isLotusStory ? st("secretNotes") : isTaipaStory ? st("taipaLetterBoxAlt") : st("tideWorkbook")}
              onOpen={setViewerAssetId}
            />
          </section>

          <section className="mt-4 rounded-2xl border border-line bg-card p-4">
            <div className="flex items-center justify-between">
              <h2 className="font-serif text-lg font-semibold">
                {isLotusStory ? st("secretNotes") : isTaipaStory ? st("taipaLetters") : st("coloaneRecordStamps")}
              </h2>
              {isLotusStory && <PetalProgress collected={petalCount} />}
            </div>
            <div className="mt-3 space-y-2">
              {session.state.rewards.map((reward) => (
                <div
                  key={reward.id}
                  className="rounded-xl border border-line bg-paper-warm px-3 py-3"
                >
                  <p className="text-base font-medium">{reward.name ?? reward.id}</p>
                  {reward.text && (
                    <p className="mt-1 text-sm leading-6 text-ink-soft">{reward.text}</p>
                  )}
                </div>
              ))}
            </div>
          </section>

          <section className="mt-4 rounded-2xl border border-ochre/30 bg-ochre/5 p-4">
            <h2 className="font-serif text-lg font-semibold">{st("noteToday")}</h2>
            <p className="mt-2 whitespace-pre-wrap text-base italic leading-7 text-ink-soft">
              {session.state.ending_reflection?.trim() ||
                st("leaveReader")}
            </p>
          </section>

          <section className="mt-5">
            <h2 className="font-serif text-xl font-semibold">{st("timeline")}</h2>
            <ol className="mt-3 space-y-2">
              {stationNodes.map((node, index) => (
                  <li
                    key={node.id}
                  >
                    <button
                      type="button"
                      onClick={() => setSummaryNode(node)}
                      className="flex min-h-16 w-full items-center gap-3 rounded-xl border border-line bg-card p-3 text-left"
                    >
                      <span className="grid size-10 shrink-0 place-items-center rounded-full bg-sage-deep/10 font-serif text-sage-deep">
                        {index + 1}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-base">
                          {node.title}
                        </span>
                        <span className="mt-0.5 block text-sm text-ink-soft">
                          {node.title}
                        </span>
                      </span>
                      <span className="text-sm text-sage-deep">{st("recap")} →</span>
                    </button>
                  </li>
                ))}
            </ol>
          </section>
        </div>

        <StoryBottomAction
          label={st("returnPlanner")}
          onClick={() => navigate("/preferences")}
        />
        <StoryAgentDrawer
          open={agentOpen}
          context={agentContext}
          onClose={() => setAgentOpen(false)}
        />
        <StoryImageViewer
          assetId={viewerAssetId}
          onClose={() => setViewerAssetId(null)}
        />
        <ChapterRecapDialog
          node={summaryNode}
          poiName={
            summaryNode?.title
          }
          reward={summaryReward}
          skipped={
            summaryNode
              ? session.state.skipped_chapter_ids.includes(summaryNode.id)
              : false
          }
          onClose={() => setSummaryNode(null)}
        />
      </main>
    );
  }

  if (!finalChapter) {
    return (
      <main className="grid min-h-dvh place-items-center bg-paper px-4">
        <ErrorState
          message={st("noteToday")}
          onRetry={() => void refreshSession()}
        />
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col bg-paper text-ink shadow-[var(--shadow-soft)]">
      <StoryTopBar
        title={st("noteToday")}
        eyebrow={st("ending")}
        petals={isLotusStory ? petalCount : undefined}
        onBack={() => navigate(`/story-sessions/${session.session_id}/map`)}
        onAskAgent={agentContext ? () => setAgentOpen(true) : undefined}
      />

      <div className="flex-1 px-4 pb-32 pt-4">
        <StoryImage
          assetId={
            isLotusStory
              ? "V4-FOR-07"
              : isTaipaStory
                ? activeEndingAsset
                : "CAT-END-01"
          }
          alt={
            isLotusStory
              ? st("noteToday")
              : isTaipaStory
                ? st("completeTaipaLetterAlt")
                : st("completeColoanePostcardAlt")
          }
          eager
          onOpen={setViewerAssetId}
        />

        <section className="mt-4 rounded-2xl border border-line bg-card p-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-ochre">
            {isLotusStory
              ? st("leaveReader")
              : isTaipaStory
                ? st("toFutureTaipa")
                : st("completeTideWorkbook")}
          </p>
          <h1 className="mt-2 font-display text-2xl leading-tight">
            {isLotusStory
              ? st("noteHeading")
              : isTaipaStory
                ? endingChoice?.choice_text ?? st("saveFutureLetter")
                : st("preserveColoaneSounds")}
          </h1>
          <p className="mt-3 text-base leading-7 text-ink-soft">
            {isLotusStory
              ? st("noteBody")
              : isTaipaStory
                ? st("taipaReflectionBody")
                : st("coloaneReflectionBody")}
          </p>

          <label htmlFor="today-note" className="mt-5 block text-sm font-semibold text-sage-deep">
            {st("noteOptional")}
          </label>
          <textarea
            id="today-note"
            value={reflection}
            onChange={(event) => setReflection(event.target.value)}
            maxLength={2000}
            rows={6}
            placeholder={st("notePlaceholder")}
            className="mt-2 w-full resize-y rounded-2xl border border-line bg-paper px-4 py-3 text-base leading-7 text-ink outline-none placeholder:text-ink-soft/55 focus:border-sage focus:ring-2 focus:ring-sage/25"
          />
          <p className="mt-1 text-right text-xs text-ink-soft">
            {reflection.length}/2000
          </p>
        </section>

        {error && (
          <div
            role="alert"
            className="mt-4 rounded-xl border border-clay/30 bg-clay/5 p-3 text-sm text-clay"
          >
            {errorStatus === 409
              ? st("endingConflict")
              : errorStatus === 422
                ? st("endingInvalid")
                : error}
            {errorStatus === 409 && (
              <button
                type="button"
                onClick={() => void refreshSession()}
                className="ml-2 min-h-11 rounded-full border border-clay/30 px-3"
              >
                {st("reload")}
              </button>
            )}
          </div>
        )}
      </div>

      <StoryBottomAction
        label={endingChoice?.choice_text ?? st("finishNote")}
        onClick={() => void completeTodayNote()}
        busy={actionPending}
        busyLabel={st("saveNote")}
        disabled={!endingChoice}
        tone="accent"
        hint={st("progressSaved")}
      />
      <StoryAgentDrawer
        open={agentOpen}
        context={agentContext}
        onClose={() => setAgentOpen(false)}
      />
      <StoryImageViewer
        assetId={viewerAssetId}
        onClose={() => setViewerAssetId(null)}
      />
    </main>
  );
}
