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
import { useAuth } from "@/state/AuthContext";
import { useStory, useStoryRestore } from "@/state/StoryContext";
import type { FutureLetterResponse, StoryNodeOverview } from "@/types/stories";

function futureLetterErrorMessage(error: unknown): string {
  if (isStoryApiError(error, 503)) {
    return "海风暂时没能送回配图。你的文字未来信已经保存，可以稍后重试。";
  }
  if (isStoryApiError(error, 409)) {
    return "故事进度已经变化，请刷新完成页后再试。";
  }
  return error instanceof Error ? error.message : "未来信配图暂时无法生成";
}

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
  const { sessionId: effectiveId } = useStoryRestore(sessionId);
  const st = useStoryMessages();
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
        const image = await fetchFutureLetterImage(session.session_id, token);
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
  }, [isCompleted, isTaipaStory, session, token]);

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
      persona: "阿莲",
      poi_name: isLotusStory ? "澳门历史城区" : isTaipaStory ? "氹仔旧城" : "路环",
      chapter_title: story?.title ?? st("journeyComplete"),
      chapter_goal: isLotusStory
        ? "回顾莲城双图六站旅程，并区分史实、地方记忆与剧情演绎。"
        : isTaipaStory
          ? "回顾海、钟、家、工、街五封来信，整理氹仔生活史与家园记忆。"
          : "回顾海、船、村、工、土五项记录，整理潮退之后的路环记忆。",
      known_facts: [
        story?.summary,
        session?.ending?.text,
      ].filter((value): value is string => Boolean(value)),
      fiction_boundaries: story?.content_notice ? [story.content_notice] : [],
      suggested_questions: isLotusStory
        ? [
            "六站线索怎样共同说明澳门城市的变化？",
            "两张地图分别适合记录哪些内容？",
            "哪些内容属于史实，哪些属于剧情演绎？",
          ]
        : isTaipaStory
          ? [
              "五封来信怎样串起氹仔生活的变化？",
              "哪些内容属于史实，哪些属于剧情演绎？",
            ]
          : [
              "五枚记录章怎样串成路环的故事？",
              "哪些内容属于史实，哪些属于剧情演绎？",
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
      const letter = await generateFutureLetter(session.session_id, token);
      const image = await fetchFutureLetterImage(session.session_id, token);
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
            onClick={() => navigate("/stories")}
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
              alt="由 AI 场景与玩家寄语合成的氹仔未来信"
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
                  ? "日落后的大炮台与澳门城市"
                  : isTaipaStory
                    ? "写给未来氹仔的信"
                    : "路环声音明信片"
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
                Optional AI artwork
              </p>
              <h2 id="future-letter-art-title" className="mt-1 font-serif text-xl font-semibold">
                {futureLetter ? "未来信已经写成" : "让海风为未来信配一幅图"}
              </h2>
              <p className="mt-2 text-sm leading-6 text-ink-soft">
                {futureLetter
                  ? "画面由 Qwen-Image 生成，信中文字仍是你保存的原文。"
                  : "这是可选体验，通常需要一至三分钟；生成失败不会影响已经完成的故事。"}
              </p>

              {futureLetter?.reflection_truncated && (
                <p className="mt-2 rounded-xl bg-ochre/10 px-3 py-2 text-xs leading-5 text-ink-soft">
                  配图只排版了寄语摘要，完整文字仍保存在故事记录中。
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
                    ? "正在检查已有配图…"
                    : futureLetterGenerating
                      ? "海风正在整理信纸…"
                      : futureLetterError
                        ? "重新生成未来信配图"
                        : "生成我的未来信"}
                </button>
              )}

              {futureLetter && (
                <p className="mt-3 text-xs text-ink-soft">
                  AI 场景示意 · 信件人物与寄送关系均为剧情虚构
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
                    ? "氹仔未来信"
                    : "路环声音明信片"
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
              alt={isLotusStory ? st("secretNotes") : isTaipaStory ? "氹仔退信盒" : "潮汐工作簿"}
              onOpen={setViewerAssetId}
            />
          </section>

          <section className="mt-4 rounded-2xl border border-line bg-card p-4">
            <div className="flex items-center justify-between">
              <h2 className="font-serif text-lg font-semibold">
                {isLotusStory ? st("secretNotes") : isTaipaStory ? "氹仔来信" : "路环记录章"}
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
                ? "完成写给未来氹仔的信"
                : "完成路环声音明信片"
          }
          eager
          onOpen={setViewerAssetId}
        />

        <section className="mt-4 rounded-2xl border border-line bg-card p-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-ochre">
            {isLotusStory
              ? st("leaveReader")
              : isTaipaStory
                ? "寄给未来氹仔"
                : "完成潮汐工作簿"}
          </p>
          <h1 className="mt-2 font-display text-2xl leading-tight">
            {isLotusStory
              ? st("noteHeading")
              : isTaipaStory
                ? endingChoice?.choice_text ?? "保存并寄出未来信"
                : "把路环的声音留在最后一页"}
          </h1>
          <p className="mt-3 text-base leading-7 text-ink-soft">
            {isLotusStory
              ? st("noteBody")
              : isTaipaStory
                ? "回顾海、钟、家、工、街五封来信，写下你希望未来仍能记得的一种氹仔生活。"
                : "回顾海、船、村、工、土五项记录，写下你此刻最想保留的一段路环记忆。"}
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
              ? "进度已在其他页面更新，请先重新载入。"
              : errorStatus === 422
                ? "提交内容格式不正确，你的补记草稿仍然保留。"
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
