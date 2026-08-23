import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { ErrorState, LoadingState } from "@/components/common/States";
import { MapRouteView } from "@/components/map/MapRouteView";
import { fetchRoutePois } from "@/api/routes";
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
import type { RoutePoi } from "@/types/routes";
import type { StoryNodeOverview } from "@/types/stories";

type NodeStatus = "completed" | "current" | "locked";

export function StoryMapPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { token, isRestoring } = useAuth();
  const {
    story,
    session,
    loading,
    error,
    errorStatus,
    restoreSession,
    loadStory,
  } = useStory();
  const { sessionId: effectiveId } = useStoryRestore(sessionId);
  const [pois, setPois] = useState<RoutePoi[]>([]);
  const [agentOpen, setAgentOpen] = useState(false);
  const [viewerAssetId, setViewerAssetId] = useState<string | null>(null);
  const [summaryNode, setSummaryNode] = useState<StoryNodeOverview | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

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
    if (session?.status === "completed") {
      navigate(`/story-sessions/${session.session_id}/ending`, { replace: true });
    }
  }, [navigate, session?.session_id, session?.status]);

  const storyPoiIds = useMemo(
    () => story?.nodes.flatMap((node) => (node.poi_id ? [node.poi_id] : [])) ?? [],
    [story],
  );
  const storyPoiLabels = useMemo(
    () =>
      Object.fromEntries(
        story?.nodes.flatMap((node) =>
          node.poi_id
            ? [[node.poi_id, storyStationName(node.id) ?? node.title]]
            : [],
        ) ?? [],
      ),
    [story],
  );

  useEffect(() => {
    if (storyPoiIds.length === 0) {
      setPois([]);
      return;
    }
    const controller = new AbortController();
    void fetchRoutePois(storyPoiIds, controller.signal)
      .then(setPois)
      .catch(() => setPois([]));
    return () => controller.abort();
  }, [storyPoiIds]);

  const completedIds = useMemo(
    () =>
      new Set([
        ...(session?.state.completed_chapter_ids ?? []),
        ...(session?.state.skipped_chapter_ids ?? []),
      ]),
    [session?.state.completed_chapter_ids, session?.state.skipped_chapter_ids],
  );
  const isLotusStory = story?.id === "lotus_city_double_map";
  const petalCount =
    session?.state.rewards.filter((reward) => reward.kind === "note_petal").length ?? 0;
  const stationNodes = story?.nodes.filter((node) => node.poi_id) ?? [];
  const chapterRewards =
    session?.state.rewards.filter(
      (reward) =>
        reward.kind !== "story_prop" &&
        reward.kind !== "collection" &&
        reward.kind !== "reflection",
    ) ?? [];

  const statusFor = (node: StoryNodeOverview): NodeStatus => {
    if (node.id === session?.current_chapter_id) return "current";
    if (completedIds.has(node.id)) return "completed";
    return "locked";
  };

  const enterCurrentChapter = () => {
    if (!session) return;
    navigate(
      `/story-sessions/${session.session_id}/nodes/${session.current_chapter_id}`,
    );
  };

  if ((loading || isRestoring) && (!session || !story)) {
    return <LoadingState label="正在恢复故事路线…" />;
  }

  if (!session || !story) {
    const invalidSession = errorStatus === 403 || errorStatus === 404;
    return (
      <main className="grid min-h-dvh place-items-center bg-paper px-4">
        <div className="w-full max-w-[480px]">
          <ErrorState
            message={
              invalidSession
                ? "这段旅程已经失效或不属于当前账号。你可以返回故事封面重新载入自己的进度。"
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

  const currentChapter = session.current_chapter;
  const currentPoi = pois.find((poi) => poi.poi_id === currentChapter?.poi_id);
  const agentContext = currentChapter?.agent_context
    ? {
        ...currentChapter.agent_context,
        chapter_title: currentChapter.title,
      }
    : undefined;

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col bg-paper text-ink shadow-[var(--shadow-soft)]">
      <StoryTopBar
        title={story.title}
        eyebrow="故事路线"
        petals={isLotusStory ? petalCount : undefined}
        onBack={() => navigate(`/stories/${story.id}`)}
        onAskAgent={agentContext ? () => setAgentOpen(true) : undefined}
      />

      <div className="flex-1 px-4 pb-28 pt-4">
        <section className="rounded-2xl border border-sage-deep/25 bg-sage-deep/5 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-sage-deep">
            当前任务
          </p>
          <h1 className="mt-1 font-serif text-xl font-semibold">
            {currentChapter?.title ?? "载入当前章节"}
          </h1>
          <p className="mt-2 text-base leading-7 text-ink-soft">
            {currentChapter?.location_name ??
              currentPoi?.poi_name ??
              `先完成序章，开启 ${stationNodes.length} 站路线`}
            {currentChapter?.story_time ? ` · ${currentChapter.story_time}` : ""}
          </p>
        </section>

        {isLotusStory ? (
          <section className="mt-4 rounded-2xl border border-line bg-card p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="font-serif text-lg font-semibold">五张密笺</h2>
                <p className="mt-1 text-sm text-ink-soft">
                  花瓣仅在服务端发放奖励后点亮
                </p>
              </div>
              <PetalProgress collected={petalCount} />
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <StoryImage
                assetId="V4-PROP-03"
                alt="城市双图"
                onOpen={setViewerAssetId}
                className="rounded-xl"
              />
              <StoryImage
                assetId={petalCount === 5 ? "V4-PROP-05" : "V4-PROP-04"}
                alt={petalCount === 5 ? "五张密笺重合" : "尚未集齐的密笺"}
                onOpen={setViewerAssetId}
                className="rounded-xl"
              />
            </div>
          </section>
        ) : (
          <section className="mt-4 rounded-2xl border border-line bg-card p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="font-serif text-lg font-semibold">已收集的故事线索</h2>
                <p className="mt-1 text-sm text-ink-soft">
                  完成现场任务后，收获会由服务端保存
                </p>
              </div>
              <span className="rounded-full border border-ochre/30 bg-ochre/10 px-3 py-1 text-sm font-semibold text-ochre">
                {chapterRewards.length}/{session.progress.total_puzzles}
              </span>
            </div>
            {chapterRewards.length > 0 ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {chapterRewards.map((reward) => (
                  <span
                    key={reward.id}
                    className="rounded-full border border-line bg-paper-warm px-3 py-2 text-sm text-ink"
                  >
                    {reward.name ?? reward.id}
                  </span>
                ))}
              </div>
            ) : (
              <p className="mt-3 rounded-xl border border-dashed border-line bg-paper-warm p-3 text-sm text-ink-soft">
                第一份线索会在完成首个现场任务后出现。
              </p>
            )}
          </section>
        )}

        <section className="mt-5" aria-labelledby="story-timeline-title">
          <div className="flex items-end justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-ochre">
                {story.estimated_hours >= 6 ? "一日故事游" : "半日故事游"}
              </p>
              <h2 id="story-timeline-title" className="font-serif text-xl font-semibold">
                章节时间线
              </h2>
            </div>
            <span className="text-sm text-ink-soft">
              {session.progress.solved_puzzles + session.progress.skipped_puzzles}/
              {session.progress.total_puzzles}
            </span>
          </div>

          <ol className="relative mt-4 space-y-3 before:absolute before:bottom-7 before:left-[1.35rem] before:top-7 before:w-px before:bg-line">
            {stationNodes.map((node, index) => {
              const status = statusFor(node);
              const poi = pois.find((item) => item.poi_id === node.poi_id);
              const skipped = session.state.skipped_chapter_ids.includes(node.id);
              return (
                <li key={node.id} className="relative">
                  <button
                    type="button"
                    onClick={() => {
                      if (status === "current") {
                        navigate(
                          `/story-sessions/${session.session_id}/nodes/${node.id}`,
                        );
                      } else if (status === "completed") {
                        setSummaryNode(node);
                      } else {
                        setNotice("完成前一站后解锁");
                      }
                    }}
                    className={`flex min-h-20 w-full items-center gap-3 rounded-2xl border p-3 text-left ${
                      status === "current"
                        ? "border-sage-deep bg-sage-deep/8 shadow-[var(--shadow-soft)]"
                        : status === "completed"
                          ? "border-line bg-card"
                          : "border-line bg-paper-warm opacity-65"
                    }`}
                  >
                    <span
                      className={`relative z-10 grid size-11 shrink-0 place-items-center rounded-full border font-serif font-semibold ${
                        status === "current"
                          ? "border-sage-deep bg-sage-deep text-paper"
                          : status === "completed"
                            ? "border-ochre bg-ochre/15 text-ochre"
                            : "border-line bg-paper text-ink-soft"
                      }`}
                    >
                      {status === "completed" ? "✓" : index + 1}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-base font-medium">
                        {storyStationName(node.id) ?? poi?.poi_name ?? node.title}
                      </span>
                      <span className="mt-1 block text-sm text-ink-soft">
                        {status === "current"
                          ? "当前站 · 点击进入"
                          : skipped
                            ? "已完成 · 谜题已跳过"
                            : status === "completed"
                              ? "已完成 · 查看回顾"
                              : "尚未解锁"}
                      </span>
                    </span>
                    <span aria-hidden>{status === "locked" ? "锁" : "→"}</span>
                  </button>
                </li>
              );
            })}
          </ol>
        </section>

        <details className="mt-5 overflow-hidden rounded-2xl border border-line bg-card">
          <summary className="flex min-h-12 cursor-pointer items-center justify-between px-4 text-base font-medium">
            查看 {stationNodes.length} 站地图
            <span aria-hidden>⌄</span>
          </summary>
          <div className="relative isolate h-72 overflow-hidden border-t border-line">
            <MapRouteView
              poiIds={storyPoiIds}
              poiLabels={storyPoiLabels}
              currentPoiId={currentChapter?.poi_id}
              onSelectPoi={(poiId) => {
                const node = stationNodes.find((item) => item.poi_id === poiId);
                if (!node) return;
                if (statusFor(node) === "current") {
                  navigate(`/story-sessions/${session.session_id}/nodes/${node.id}`);
                } else {
                  setSummaryNode(statusFor(node) === "completed" ? node : null);
                  if (statusFor(node) === "locked") setNotice("完成前一站后解锁");
                }
              }}
            />
          </div>
        </details>

        {(notice || errorStatus === 409) && (
          <div
            role="status"
            className="mt-4 flex items-center justify-between gap-3 rounded-xl border border-ochre/30 bg-ochre/5 p-3 text-sm text-ink-soft"
          >
            <span>{errorStatus === 409 ? "进度已在其他页面更新，请重新载入。" : notice}</span>
            <button
              type="button"
              onClick={() => {
                setNotice(null);
                if (errorStatus === 409) void restoreSession(session.session_id);
              }}
              className="min-h-11 shrink-0 rounded-full border border-line px-3"
            >
              {errorStatus === 409 ? "重新载入" : "知道了"}
            </button>
          </div>
        )}
      </div>

      {currentChapter && (
        <StoryBottomAction
          label="进入当前章节"
          onClick={enterCurrentChapter}
        />
      )}

      <ChapterRecapDialog
        node={summaryNode}
        poiName={
          summaryNode
            ? storyStationName(summaryNode.id) ??
              pois.find((poi) => poi.poi_id === summaryNode.poi_id)?.poi_name
            : undefined
        }
        reward={
          summaryNode
            ? chapterRewards[stationNodes.findIndex((node) => node.id === summaryNode.id)]
            : undefined
        }
        skipped={
          summaryNode
            ? session.state.skipped_chapter_ids.includes(summaryNode.id)
            : false
        }
        onClose={() => setSummaryNode(null)}
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
