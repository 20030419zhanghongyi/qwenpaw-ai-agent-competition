import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { ErrorState, LoadingState } from "@/components/common/States";
import { StoryImage } from "@/features/story/assets";
import { ChapterRecapDialog } from "@/features/story/components/ChapterRecapDialog";
import { StoryAgentDrawer } from "@/features/story/components/StoryAgentDrawer";
import { StoryBottomAction } from "@/features/story/components/StoryBottomAction";
import { StoryImageViewer } from "@/features/story/components/StoryImageViewer";
import { PetalProgress } from "@/features/story/components/PetalProgress";
import { StoryTopBar } from "@/features/story/components/StoryTopBar";
import { storyStationName } from "@/features/story/storyStations";
import { useAuth } from "@/state/AuthContext";
import { useStory, useStoryRestore } from "@/state/StoryContext";
import type { StoryNodeOverview } from "@/types/stories";

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
  const [reflection, setReflection] = useState("");
  const [viewerAssetId, setViewerAssetId] = useState<string | null>(null);
  const [agentOpen, setAgentOpen] = useState(false);
  const [summaryNode, setSummaryNode] = useState<StoryNodeOverview | null>(null);

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
  const petalCount =
    session?.state.rewards.filter((reward) => reward.kind === "note_petal").length ?? 0;
  const completionAgentContext = useMemo(
    () => ({
      persona: "阿莲",
      poi_name: story?.title ?? "澳门故事路线",
      chapter_title: `完成结果：${session?.ending?.title ?? story?.title ?? "故事游"}`,
      chapter_goal: "回顾这段故事旅程，并区分史实、地方记忆与剧情演绎。",
      known_facts: [
        story?.summary,
        session?.ending?.text,
      ].filter((value): value is string => Boolean(value)),
      fiction_boundaries: story?.content_notice ? [story.content_notice] : [],
      suggested_questions: [
        "沿途线索怎样共同说明地方生活的变化？",
        "哪些现场观察最值得继续记录？",
        "哪些内容属于史实，哪些属于剧情演绎？",
      ],
      do_not_reveal: [],
    }),
    [
      session?.ending?.text,
      session?.ending?.title,
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

  if ((loading || isRestoring) && !session) {
    return <LoadingState label="正在打开故事结局…" />;
  }

  if (!session) {
    const invalidSession = errorStatus === 403 || errorStatus === 404;
    return (
      <main className="grid min-h-dvh place-items-center bg-paper px-4">
        <div className="w-full max-w-[480px]">
          <ErrorState
            message={
              invalidSession
                ? "这段旅程已经失效或不属于当前账号。"
                : error ?? "未找到故事会话"
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
            返回故事封面
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
  const chapterRewards = session.state.rewards.filter(
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
        ? chapterRewards[summaryIndex]
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
          title={story?.title ?? "StoryWalk"}
          eyebrow="旅程完成"
          petals={isLotusStory ? petalCount : undefined}
          onBack={() => navigate("/stories")}
          onAskAgent={agentContext ? () => setAgentOpen(true) : undefined}
        />

        <div className="flex-1 px-4 pb-28 pt-4">
          <StoryImage
            assetId={
              isLotusStory
                ? "V4-FOR-09"
                : story?.presentation.cover_asset_id ?? activeEndingAsset
            }
            alt={`${story?.title ?? "故事游"}完成画面`}
            eager
            onOpen={setViewerAssetId}
            imageClassName="object-contain"
          />

          <section className="relative mt-4 rounded-3xl border border-line bg-paper p-5 text-center shadow-[var(--shadow-lift)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-ochre">
              {story?.identity.name ?? "旅程完成"}
            </p>
            <h1 className="mt-2 font-display text-3xl">
              {session.ending?.title ?? "故事留言已保存"}
            </h1>
            <p className="mt-3 text-base leading-7 text-ink-soft">
              {session.ending?.text ?? "地方仍在变化，你为今天留下了一笔。"}
            </p>
          </section>

          {isLotusStory && (
            <section className="mt-4 grid grid-cols-2 gap-3">
              <StoryImage
                assetId="V4-FOR-08"
                alt="完整五瓣澳门市花"
                onOpen={setViewerAssetId}
              />
              <StoryImage
                assetId="V4-PROP-05"
                alt="五张密笺迎光重合"
                onOpen={setViewerAssetId}
              />
            </section>
          )}

          <section className="mt-4 rounded-2xl border border-line bg-card p-4">
            <div className="flex items-center justify-between">
              <h2 className="font-serif text-lg font-semibold">
                {isLotusStory ? "五瓣密笺" : "旅程收获"}
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
            <h2 className="font-serif text-lg font-semibold">你的故事留言</h2>
            <p className="mt-2 whitespace-pre-wrap text-base italic leading-7 text-ink-soft">
              {session.state.ending_reflection?.trim() ||
                "今天仍留有一处空白，交给下一位来到这里的人。"}
            </p>
          </section>

          <section className="mt-5">
            <h2 className="font-serif text-xl font-semibold">
              {stationNodes.length} 站路线回顾
            </h2>
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
                          {storyStationName(node.id) ?? node.title}
                        </span>
                        <span className="mt-0.5 block text-sm text-ink-soft">
                          {node.title}
                        </span>
                      </span>
                      <span className="text-sm text-sage-deep">查看回顾 →</span>
                    </button>
                  </li>
                ))}
            </ol>
          </section>
        </div>

        <StoryBottomAction
          label="返回故事选择"
          onClick={() => navigate("/stories")}
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
            summaryNode ? storyStationName(summaryNode.id) : undefined
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
          message="当前还没有进入今日补记。"
          onRetry={() => void refreshSession()}
        />
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col bg-paper text-ink shadow-[var(--shadow-soft)]">
      <StoryTopBar
        title={endingChoice?.title ?? finalChapter.title}
        eyebrow="最终章"
        petals={isLotusStory ? petalCount : undefined}
        onBack={() => navigate(`/story-sessions/${session.session_id}/map`)}
        onAskAgent={agentContext ? () => setAgentOpen(true) : undefined}
      />

      <div className="flex-1 px-4 pb-32 pt-4">
        <StoryImage
          assetId={activeEndingAsset}
          alt={`${endingChoice?.title ?? finalChapter.title}故事结局`}
          eager
          onOpen={setViewerAssetId}
        />

        <section className="mt-4 rounded-2xl border border-line bg-card p-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-ochre">
            留给未来的读者
          </p>
          <h1 className="mt-2 font-display text-2xl leading-tight">
            {isLotusStory
              ? "把今天看到的澳门，留给下一位读者"
              : endingChoice?.choice_text ?? "为这段旅程写下最后一句话"}
          </h1>
          <p className="mt-3 text-base leading-7 text-ink-soft">
            {isLotusStory
              ? "不必重画整座城市。写下你在什么时间来到这里、看见了什么，以及今天仍值得继续查证的部分。"
              : "写下你在沿途看见、听见或想到的一件事。它会与本次旅程的收获一起保存。"}
          </p>

          <label htmlFor="today-note" className="mt-5 block text-sm font-semibold text-sage-deep">
            故事留言（可选）
          </label>
          <textarea
            id="today-note"
            value={reflection}
            onChange={(event) => setReflection(event.target.value)}
            maxLength={2000}
            rows={6}
            placeholder={
              isLotusStory
                ? "例如：今天的城市仍然不是澳门的全部……"
                : "例如：我想把今天仍能看见的生活，留给后来的人……"
            }
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
        label={endingChoice?.choice_text ?? "完成故事"}
        onClick={() => void completeTodayNote()}
        busy={actionPending}
        busyLabel="正在保存故事留言…"
        disabled={!endingChoice}
        tone="accent"
        hint="服务端保存成功后才会完成故事"
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
