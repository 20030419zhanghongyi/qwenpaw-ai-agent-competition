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
import { useStoryMessages } from "@/features/story/storyI18n";
import { navigateBack } from "@/lib/backNavigation";
import { useAuth } from "@/state/AuthContext";
import { useStory, useStoryRestore } from "@/state/StoryContext";
import { useWalk } from "@/state/WalkContext";
import type { RoutePoi } from "@/types/routes";
import type { StoryNodeOverview } from "@/types/stories";

type NodeStatus = "completed" | "current" | "locked";

export function StoryMapPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { token, isRestoring } = useAuth();
  const { language } = useWalk();
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
  const st = useStoryMessages();
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
            ? [[node.poi_id, node.title]]
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
  const petalCount =
    session?.state.rewards.filter((reward) => reward.kind === "note_petal").length ?? 0;
  const isLotusStory = story?.id === "lotus_city_double_map";
  const isTaipaStory = story?.id === "taipa_letters";
  const stationNodes = story?.nodes.filter((node) => node.poi_id) ?? [];
  const collectibleRewards =
    session?.state.rewards.filter(
      (reward) =>
        reward.kind !== "story_prop" &&
        reward.kind !== "collection" &&
        reward.kind !== "reflection",
    ) ?? [];
  const recordCount = collectibleRewards.length;
  const collectionTitle = isLotusStory
    ? st("secretNotes")
    : isTaipaStory
      ? st("taipaLetters")
      : st("tideWorkbook");
  const collectionProgress = isLotusStory
    ? st("petalsServer")
    : isTaipaStory
      ? st("taipaCollectionProgress", { count: recordCount })
      : st("coloaneCollectionProgress", { count: recordCount });
  const collectionCoverAsset = isLotusStory
    ? "V4-PROP-03"
    : isTaipaStory
      ? "TAI-COVER-01"
      : "CAT-COVER-01";
  const collectionPropAsset = isLotusStory
    ? petalCount === 5
      ? "V4-PROP-05"
      : "V4-PROP-04"
    : isTaipaStory
      ? "TAI-PROP-01"
      : "CAT-PROP-01";

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
    return <LoadingState label={st("loadingRoute")} />;
  }

  if (!session || !story) {
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
        eyebrow={st("routeEyebrow")}
        petals={isLotusStory ? petalCount : undefined}
        onBack={() => navigate(`/stories/${story.id}`)}
        onHome={() => navigate("/walk")}
        homeLabel={{ "zh-CN": "返回主页", "zh-TW": "返回主頁", en: "Home", pt: "Início" }[language]}
        onAskAgent={agentContext ? () => setAgentOpen(true) : undefined}
      />

      <div className="flex-1 px-4 pb-28 pt-4">
        <section className="rounded-2xl border border-sage-deep/25 bg-sage-deep/5 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-sage-deep">
            {st("currentMission")}
          </p>
          <h1 className="mt-1 font-serif text-xl font-semibold">
            {currentChapter?.title ?? st("loadingChapterTitle")}
          </h1>
          <p className="mt-2 text-base leading-7 text-ink-soft">
            {currentChapter?.location_name ??
              currentPoi?.poi_name ??
              st("unlockRoute")}
            {currentChapter?.story_time ? ` · ${currentChapter.story_time}` : ""}
          </p>
        </section>

        <section className="mt-4 rounded-2xl border border-line bg-card p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="font-serif text-lg font-semibold">
                {collectionTitle}
              </h2>
              <p className="mt-1 text-sm text-ink-soft">
                {collectionProgress}
              </p>
            </div>
            {isLotusStory && <PetalProgress collected={petalCount} />}
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <StoryImage
              assetId={collectionCoverAsset}
              alt={isLotusStory ? st("cityMaps") : story.title}
              onOpen={setViewerAssetId}
              className="rounded-xl"
            />
            <StoryImage
              assetId={collectionPropAsset}
              alt={collectionTitle}
              onOpen={setViewerAssetId}
              className="rounded-xl"
            />
          </div>
        </section>

        <section className="mt-5" aria-labelledby="story-timeline-title">
          <div className="flex items-end justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-ochre">
                {st("sixStops")}
              </p>
              <h2 id="story-timeline-title" className="font-serif text-xl font-semibold">
                {st("timeline")}
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
                      if (status === "current" || status === "completed") {
                        navigate(
                          `/story-sessions/${session.session_id}/nodes/${node.id}`,
                        );
                      } else {
                        setNotice(st("finishPrevious"));
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
                          {node.title ?? poi?.poi_name}
                      </span>
                      <span className="mt-1 block text-sm text-ink-soft">
                        {status === "current"
                          ? st("currentStop")
                          : skipped
                            ? st("skipped")
                            : status === "completed"
                              ? st("completed")
                              : st("locked")}
                      </span>
                    </span>
                    <span aria-hidden>{status === "locked" ? st("lockedShort") : "→"}</span>
                  </button>
                </li>
              );
            })}
          </ol>
        </section>

        <details className="mt-5 overflow-hidden rounded-2xl border border-line bg-card">
          <summary className="flex min-h-12 cursor-pointer items-center justify-between px-4 text-base font-medium">
            {st("viewMap")}
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
                const status = statusFor(node);
                if (status === "current" || status === "completed") {
                  navigate(`/story-sessions/${session.session_id}/nodes/${node.id}`);
                } else {
                  setNotice(st("finishPrevious"));
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
            <span>{errorStatus === 409 ? st("conflictReload") : notice}</span>
            <button
              type="button"
              onClick={() => {
                setNotice(null);
                if (errorStatus === 409) void restoreSession(session.session_id);
              }}
              className="min-h-11 shrink-0 rounded-full border border-line px-3"
            >
              {errorStatus === 409 ? st("reload") : st("gotIt")}
            </button>
          </div>
        )}
      </div>

      {currentChapter && (
        <StoryBottomAction
          label={st("enterChapter")}
          onClick={enterCurrentChapter}
        />
      )}

      <ChapterRecapDialog
        node={summaryNode}
        poiName={
          summaryNode
            ? summaryNode.title ??
              pois.find((poi) => poi.poi_id === summaryNode.poi_id)?.poi_name
            : undefined
        }
        reward={
          summaryNode
            ? collectibleRewards[
                stationNodes.findIndex((node) => node.id === summaryNode.id)
              ]
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
