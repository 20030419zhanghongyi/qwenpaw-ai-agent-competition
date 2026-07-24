import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { LoadingState, ErrorState } from "@/components/common/States";
import { MapRouteView } from "@/components/map/MapRouteView";
import { RewardReveal } from "@/components/story/RewardReveal";
import { fetchStory } from "@/api/stories";
import { fetchRoutePois } from "@/api/routes";
import type { RoutePoi } from "@/types/routes";
import { useAuth } from "@/state/AuthContext";
import { useStory, useStoryRestore } from "@/state/StoryContext";
import type { StoryNodeOverview } from "@/types/stories";

export function StoryMapPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { token } = useAuth();
  const {
    story,
    session,
    latestRewards,
    loading,
    error,
    restoreSession,
    clearLatestRewards,
  } = useStory();
  const { sessionId: persistedId } = useStoryRestore();
  const [pois, setPois] = useState<RoutePoi[]>([]);
  const [poisLoading, setPoisLoading] = useState(false);

  // Restore session on mount
  const effectiveId = sessionId ?? persistedId;
  useEffect(() => {
    if (effectiveId && token) {
      restoreSession(effectiveId);
    }
  }, [effectiveId, token, restoreSession]);

  // If session loaded but no story, load it from the session's story_id
  useEffect(() => {
    if (session && !story) {
      fetchStory(session.story_id).catch(() => {});
    }
  }, [session, story]);

  // Load POI data for the route
  useEffect(() => {
    if (!story) return;
    const poiIds = story.nodes
      .filter((n) => n.poi_id)
      .map((n) => n.poi_id!);
    if (poiIds.length === 0) {
      setPois([]);
      return;
    }
    setPoisLoading(true);
    fetchRoutePois(poiIds)
      .then(setPois)
      .catch(() => setPois([]))
      .finally(() => setPoisLoading(false));
  }, [story]);

  const currentChapter = session?.current_chapter;
  const currentPoiId = currentChapter?.poi_id ?? undefined;

  // Compute node status from session state
  const nodeStatus = useMemo(() => {
    if (!session || !story) return new Map<string, "completed" | "current" | "locked">();
    const completed = new Set([
      ...session.state.completed_chapter_ids,
      ...session.state.skipped_chapter_ids,
    ]);
    const map = new Map<string, "completed" | "current" | "locked">();
    let foundCurrent = session.status === "completed";
    for (const node of story.nodes) {
      if (node.id === session.current_chapter_id) {
        map.set(node.id, "current");
        foundCurrent = true;
      } else if (completed.has(node.id)) {
        map.set(node.id, "completed");
      } else if (!foundCurrent) {
        map.set(node.id, "completed");
      } else {
        map.set(node.id, "locked");
      }
    }
    return map;
  }, [session, story]);

  const handleGoToNode = (nodeId: string) => {
    if (!session) return;
    navigate(`/story-sessions/${session.session_id}/nodes/${nodeId}`);
  };

  const handleBack = () => {
    if (story) navigate(`/stories/${story.id}`);
    else navigate("/");
  };

  if (loading && !session) return <LoadingState label="加载故事进度…" />;
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

  const isCompleted = session.status === "completed";
  const progress = session.progress;

  return (
    <main className="flex min-h-dvh flex-col bg-paper text-ink">
      {/* Top bar */}
      <header className="sticky top-0 z-30 border-b border-line/80 bg-paper/95 px-4 py-3 backdrop-blur-md">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={handleBack}
            className="text-sm text-ink-soft transition hover:text-ink"
          >
            ← 返回
          </button>
          <div className="text-center">
            <p className="font-serif text-sm font-semibold text-ink">
              {story?.title ?? "剧情探索"}
            </p>
            <p className="text-xs text-ink-soft">
              {isCompleted
                ? "已完成"
                : `进度 ${progress.completed_chapters}/${progress.total_chapters}`}
            </p>
          </div>
          <div className="w-12" aria-hidden />
        </div>
      </header>

      {/* Map */}
      <div className="relative h-[42dvh] shrink-0 overflow-hidden bg-paper-warm">
        {poisLoading ? (
          <div className="flex h-full items-center justify-center">
            <LoadingState label="加载地图…" />
          </div>
        ) : (
          <MapRouteView
            poiIds={story?.nodes.filter((n) => n.poi_id).map((n) => n.poi_id!) ?? []}
            currentPoiId={currentPoiId}
            onSelectPoi={(poiId) => {
              const node = story?.nodes.find((n) => n.poi_id === poiId);
              if (node) handleGoToNode(node.id);
            }}
          />
        )}
      </div>

      {/* Node list */}
      <div className="flex-1 overflow-auto px-4 py-4 sm:mx-auto sm:max-w-lg sm:px-6">
        {/* Current chapter CTA */}
        {!isCompleted && currentChapter && (
          <div className="mb-4 rounded-2xl border border-sage-deep/30 bg-sage-deep/5 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sage-deep">
              当前章节
            </p>
            <p className="mt-1 font-serif text-lg font-semibold text-ink">
              {currentChapter.title}
            </p>
            {currentChapter.story_time && (
              <p className="text-xs text-ink-soft">{currentChapter.story_time}</p>
            )}
            {currentChapter.poi_id && (
              <p className="mt-1 text-sm text-sage-deep">
                📍 {pois.find((p) => p.poi_id === currentChapter.poi_id)?.poi_name ?? currentChapter.poi_id}
              </p>
            )}
            <button
              type="button"
              onClick={() => handleGoToNode(currentChapter.id)}
              className="mt-4 w-full rounded-full bg-sage-deep px-5 py-3 text-sm font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss active:scale-[0.99]"
            >
              进入章节
            </button>
          </div>
        )}

        {/* Completed banner */}
        {isCompleted && (
          <div className="mb-4 rounded-2xl border border-ochre/40 bg-ochre/5 p-5 text-center">
            <p className="font-serif text-lg font-semibold text-ochre">
              故事已完成
            </p>
            <p className="mt-1 text-sm text-ink-soft">
              查看你的结局与收集的线索
            </p>
            <button
              type="button"
              onClick={() =>
                navigate(
                  `/story-sessions/${session.session_id}/ending`,
                )
              }
              className="mt-3 rounded-full bg-ochre px-5 py-2.5 text-sm font-medium text-paper transition hover:opacity-90"
            >
              查看结局
            </button>
          </div>
        )}

        {/* Reward count */}
        {session.state.rewards.length > 0 && (
          <div className="mb-4 flex flex-wrap gap-2">
            {session.state.rewards.map((r) => {
              const icons: Record<string, string> = {
                stamp: "🦭",
                capability: "🔍",
                coordinate: "📍",
              };
              return (
                <span
                  key={r.id}
                  className="inline-flex items-center gap-1 rounded-full border border-line bg-card px-3 py-1.5 text-xs text-ink-soft"
                >
                  {icons[r.kind] ?? "✦"} {r.name ?? r.id}
                </span>
              );
            })}
          </div>
        )}

        {/* All nodes */}
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-soft">
            章节
          </p>
          {story?.nodes.map((node: StoryNodeOverview) => {
            const status = nodeStatus.get(node.id) ?? "locked";
            const poi = pois.find((p) => p.poi_id === node.poi_id);
            return (
              <button
                key={node.id}
                type="button"
                disabled={status === "locked"}
                onClick={() => handleGoToNode(node.id)}
                className={`flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left transition ${
                  status === "current"
                    ? "border-sage-deep bg-sage-deep/10"
                    : status === "completed"
                      ? "border-line/60 bg-card/60"
                      : "border-line bg-card opacity-50"
                }`}
              >
                <span
                  className={`grid size-8 shrink-0 place-items-center rounded-full font-serif text-xs font-bold ${
                    status === "current"
                      ? "bg-sage-deep text-paper"
                      : status === "completed"
                        ? "bg-sage-deep/20 text-sage-deep"
                        : "bg-line/40 text-ink-soft"
                  }`}
                >
                  {status === "completed" ? "✓" : node.order}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-ink">
                    {node.title}
                  </p>
                  <p className="text-xs text-ink-soft">
                    {poi?.poi_name ?? (node.poi_id ? node.poi_id : "无地点")}
                    {node.story_time ? ` · ${node.story_time}` : ""}
                  </p>
                </div>
                <span className="text-xs text-ink-soft">
                  {status === "current" ? "→" : status === "completed" ? "✓" : "🔒"}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Reward reveal modal */}
      {latestRewards.length > 0 && (
        <RewardReveal rewards={latestRewards} onDismiss={clearLatestRewards} />
      )}
    </main>
  );
}
