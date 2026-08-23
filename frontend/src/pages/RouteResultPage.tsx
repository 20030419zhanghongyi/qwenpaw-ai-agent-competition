import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import { Link, useNavigate } from "react-router-dom";
import { triggerGuide, type GuideTriggerResponse } from "@/api/guide-trigger";
import {
  adjustRoute,
  fetchRoutePois,
  fetchRouteWalkPath,
} from "@/api/routes";
import { MapRouteView } from "@/components/map";
import { RouteAdjustmentPanel } from "@/components/route-adjust";
import { ReasonChips } from "@/components/route/ReasonChips";
import {
  RouteNodeList,
  type DisplayNode,
  type WalkLeg,
} from "@/components/route/RouteNodeList";
import { TripControls } from "@/components/trip/TripControls";
import { t } from "@/i18n";
import { resolveTripUserId } from "@/lib/guestUser";
import { routeHasGamblingVenue } from "@/lib/gamblingEthics";
import { formatWalkMeta } from "@/lib/preference";
import { ensurePreferencePortAnchors, portLabel } from "@/lib/ports";
import { buildRouteAdjustmentDraft } from "@/lib/route-adjustment";
import { useAuth } from "@/state/AuthContext";
import { useTrip } from "@/state/TripContext";
import { useWalk } from "@/state/WalkContext";
import type { POI } from "@/types";
import type { RouteAdjustmentDraft, RoutePoi } from "@/types/routes";

type SheetSnap = "peek" | "half" | "full";

const SHEET_PEEK_PX = 176;
const SHEET_SNAPS: SheetSnap[] = ["peek", "half", "full"];

function sheetHeightPx(snap: SheetSnap, viewportH = window.innerHeight): number {
  if (snap === "full") return viewportH * 0.92;
  if (snap === "half") return viewportH * 0.56;
  return SHEET_PEEK_PX;
}

function nearestSheetSnap(height: number, viewportH = window.innerHeight): SheetSnap {
  let best: SheetSnap = "half";
  let bestDist = Number.POSITIVE_INFINITY;
  for (const snap of SHEET_SNAPS) {
    const dist = Math.abs(sheetHeightPx(snap, viewportH) - height);
    if (dist < bestDist) {
      best = snap;
      bestDist = dist;
    }
  }
  return best;
}

function nextSheetSnap(snap: SheetSnap): SheetSnap {
  if (snap === "peek") return "half";
  if (snap === "half") return "full";
  return "peek";
}

function haversineMeters(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const r = 6371000;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * r * Math.asin(Math.sqrt(a));
}

function estimateWalkLegs(poiIds: string[], poisById: Record<string, POI>): WalkLeg[] {
  const legs: WalkLeg[] = [];
  for (let i = 0; i < poiIds.length - 1; i += 1) {
    const from = poisById[poiIds[i]];
    const to = poisById[poiIds[i + 1]];
    if (!from || !to) {
      legs.push({ walkM: 0, walkMin: 0 });
      continue;
    }
    const meters = Math.round(
      haversineMeters(from.latitude, from.longitude, to.latitude, to.longitude),
    );
    // ~4.8 km/h walking pace
    const walkMin = Math.max(1, Math.ceil(meters / 80));
    const preferBus = walkMin >= 15;
    legs.push({
      walkM: meters,
      walkMin,
      ...(preferBus
        ? {
            preferredMode: "bus" as const,
            busLines: ["建议乘巴士（勿步行）"],
          }
        : {}),
    });
  }
  return legs;
}

const TRIM_NOTE_RE = /(?:\s*已按约束缩短末端节点。)+/g;

/** Strip repeated constructor notes from cached route blurbs. */
function cleanRouteBlurb(text: unknown): string {
  if (typeof text !== "string") return "";
  return text.replace(TRIM_NOTE_RE, "").replace(/\s+/g, " ").trim();
}

type TriggerMode = "gps" | "simulated";

interface NarrationState {
  poiName: string;
  text: string;
  sourceType?: string;
  audioUrl?: string;
  ttsFailed?: boolean;
}

function readGuideSessionId(): string {
  const key = "macau-storywalk-guide-session";
  try {
    const existing = sessionStorage.getItem(key);
    if (existing) return existing;
    const next = `walk-${crypto.randomUUID()}`;
    sessionStorage.setItem(key, next);
    return next;
  } catch {
    return `walk-${Date.now()}`;
  }
}

export function RouteResultPage() {
  const navigate = useNavigate();
  const { session, language, setSession } = useWalk();
  const { userId: authUserId } = useAuth();
  const { trip, loading: tripLoading, checkInAtLocation } = useTrip();
  const tripUserId = resolveTripUserId(authUserId);
  const [sheetOpen, setSheetOpen] = useState<SheetSnap>("half");
  const [sheetDragHeight, setSheetDragHeight] = useState<number | null>(null);
  const [walkLegs, setWalkLegs] = useState<WalkLeg[]>([]);
  const [walkLegsLoading, setWalkLegsLoading] = useState(false);
  const [dayIndex, setDayIndex] = useState(0);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [guiding, setGuiding] = useState(false);
  const [checking, setChecking] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [userLocation, setUserLocation] = useState<{
    latitude: number;
    longitude: number;
  } | null>(null);
  const [mapRecenterToken, setMapRecenterToken] = useState(0);
  const [statusNote, setStatusNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [adjustInstruction, setAdjustInstruction] = useState("");
  const [adjusting, setAdjusting] = useState(false);
  const [adjustError, setAdjustError] = useState<string | null>(null);
  const [adjustDraft, setAdjustDraft] = useState<RouteAdjustmentDraft | null>(null);
  const [adjustmentPois, setAdjustmentPois] = useState<RoutePoi[]>([]);

  const [triggerOpen, setTriggerOpen] = useState(false);
  const [triggerMode, setTriggerMode] = useState<TriggerMode>("gps");
  const [triggerPayload, setTriggerPayload] = useState<GuideTriggerResponse | null>(null);

  const [narration, setNarration] = useState<NarrationState | null>(null);
  const guideSessionId = useRef(readGuideSessionId());
  const triggerOpenRef = useRef(false);
  const generatingRef = useRef(false);
  const checkingRef = useRef(false);
  const lastGpsCheckRef = useRef(0);
  const nodesRef = useRef<DisplayNode[]>([]);
  const sheetDragRef = useRef<{
    pointerId: number;
    startY: number;
    startHeight: number;
    moved: boolean;
  } | null>(null);

  const sheetDragging = sheetDragHeight != null;
  const sheetHeight = sheetDragHeight ?? sheetHeightPx(sheetOpen);

  function onSheetHandlePointerDown(event: ReactPointerEvent<HTMLButtonElement>) {
    if (event.button !== 0) return;
    const startHeight = sheetDragHeight ?? sheetHeightPx(sheetOpen);
    sheetDragRef.current = {
      pointerId: event.pointerId,
      startY: event.clientY,
      startHeight,
      moved: false,
    };
    setSheetDragHeight(startHeight);
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function onSheetHandlePointerMove(event: ReactPointerEvent<HTMLButtonElement>) {
    const drag = sheetDragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const delta = drag.startY - event.clientY;
    if (Math.abs(delta) > 4) drag.moved = true;
    const maxH = sheetHeightPx("full");
    const minH = sheetHeightPx("peek");
    const next = Math.min(maxH, Math.max(minH, drag.startHeight + delta));
    setSheetDragHeight(next);
  }

  function endSheetHandleDrag(event: ReactPointerEvent<HTMLButtonElement>) {
    const drag = sheetDragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const height = sheetDragHeight ?? drag.startHeight;
    sheetDragRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    if (!drag.moved) {
      setSheetOpen((snap) => nextSheetSnap(snap));
    } else {
      setSheetOpen(nearestSheetSnap(height));
    }
    setSheetDragHeight(null);
  }

  const dayMatches = session?.matches?.length ? session.matches : session?.match ? [session.match] : [];
  const match = dayMatches[Math.min(dayIndex, Math.max(dayMatches.length - 1, 0))] ?? session?.match;
  const preference = session?.preference;
  const poisById = session?.poisById ?? {};
  const route = match?.route;
  const isMultiDay = (dayMatches.length > 1) || preference?.duration === "multi-day";

  useEffect(() => {
    setCurrentIndex(0);
    setTriggerOpen(false);
    setNarration(null);
    setGuiding(false);
    setAdjustDraft(null);
    setAdjustmentPois([]);
    setAdjustError(null);
  }, [dayIndex]);

  const nodes = useMemo(() => {
    if (!route) return [];
    // Stale matches (or prefs saved after match) may omit port anchors — merge from preference.
    const sorted = ensurePreferencePortAnchors(route.nodes ?? [], preference, language);
    return sorted.map((node, index): DisplayNode => {
      const poi = poisById[node.poi_id];
      const anchor =
        node.anchor === "entry" || node.anchor === "exit"
          ? node.anchor
          : node.poi_id === preference?.entry_port
            ? "entry"
            : node.poi_id === preference?.exit_port
              ? "exit"
              : null;
      const portSubtitle =
        anchor === "entry"
          ? t(language, "entryPortSubtitle")
          : anchor === "exit"
            ? t(language, "exitPortSubtitle")
            : null;
      return {
        poiId: node.poi_id,
        order: node.order,
        name: poi?.poi_name || portLabel(node.poi_id, language) || node.poi_id,
        subtitle: portSubtitle ?? poi?.alias ?? poi?.category,
        note: node.note || poi?.address || t(language, "nodeNoteFallback"),
        stayMin: node.suggested_stay_min,
        state:
          index === currentIndex ? "current" : index === currentIndex + 1 ? "next" : "upcoming",
      };
    });
  }, [route, poisById, language, currentIndex, preference]);

  useEffect(() => {
    nodesRef.current = nodes;
  }, [nodes]);

  const nodePoiIds = useMemo(() => nodes.map((n) => n.poiId), [nodes]);
  const nodePoiKey = nodePoiIds.join("|");

  useEffect(() => {
    if (nodePoiIds.length < 2) {
      setWalkLegs([]);
      setWalkLegsLoading(false);
      return;
    }
    const expectedLegs = nodePoiIds.length - 1;
    const fallback = estimateWalkLegs(nodePoiIds, poisById);
    setWalkLegs(fallback);
    setWalkLegsLoading(true);
    let active = true;
    const applyLegs = (res: Awaited<ReturnType<typeof fetchRouteWalkPath>>) => {
      const legs = (res.segments ?? []).map((seg) => ({
        walkM: seg.walk_m,
        walkMin: seg.walk_min,
        busLines: seg.bus_lines ?? [],
        busFromStop: seg.bus_from_stop ?? null,
        busToStop: seg.bus_to_stop ?? null,
        preferredMode:
          seg.preferred_mode ??
          (seg.walk_min >= 15 && (seg.bus_lines?.length ?? 0) > 0 ? "bus" : "walk"),
      }));
      if (legs.length === expectedLegs) setWalkLegs(legs);
    };
    fetchRouteWalkPath(nodePoiIds)
      .then((res) => {
        if (active) applyLegs(res);
      })
      .catch(() =>
        // one retry after transient AMap / backend 503
        new Promise((resolve) => window.setTimeout(resolve, 600)).then(() =>
          active ? fetchRouteWalkPath(nodePoiIds).then(applyLegs) : undefined,
        ),
      )
      .catch(() => {
        // keep haversine fallback
      })
      .finally(() => {
        if (active) setWalkLegsLoading(false);
      });
    return () => {
      active = false;
    };
    // poisById used for fallback only when ids change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodePoiKey]);

  useEffect(() => {
    triggerOpenRef.current = triggerOpen;
  }, [triggerOpen]);

  useEffect(() => {
    generatingRef.current = generating;
  }, [generating]);

  useEffect(() => {
    checkingRef.current = checking;
  }, [checking]);

  useEffect(() => {
    if (!guiding) return;
    if (!navigator.geolocation) {
      setStatusNote(t(language, "gpsUnsupported"));
      return;
    }

    setStatusNote(t(language, "gpsWatching"));
    setError(null);

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const { longitude, latitude } = pos.coords;
        setUserLocation({ latitude, longitude });

        if (triggerOpenRef.current || generatingRef.current || checkingRef.current) return;
        const now = Date.now();
        if (now - lastGpsCheckRef.current < 8000) return;
        lastGpsCheckRef.current = now;

        void (async () => {
          checkingRef.current = true;
          setChecking(true);
          try {
            const res = await triggerGuide({
              longitude,
              latitude,
              session_id: guideSessionId.current,
              radius_m: 100,
              language,
            });
            if (res.triggered || (res.poi && res.reason === "recently_triggered")) {
              setTriggerPayload(res);
              setTriggerMode("gps");
              setTriggerOpen(true);
              setNarration(null);
              setError(null);
              setStatusNote(null);
              if (res.poi?.poi_id) {
                const idx = nodesRef.current.findIndex((n) => n.poiId === res.poi?.poi_id);
                if (idx >= 0) setCurrentIndex(idx);
              }
            } else {
              setStatusNote(t(language, "gpsNoNearby"));
            }
          } catch (err) {
            setError(err instanceof Error ? err.message : t(language, "guideError"));
          } finally {
            checkingRef.current = false;
            setChecking(false);
          }
        })();
      },
      () => {
        setStatusNote(t(language, "locationDenied"));
      },
      {
        enableHighAccuracy: true,
        maximumAge: 5000,
        timeout: 20_000,
      },
    );

    return () => {
      navigator.geolocation.clearWatch(watchId);
    };
  }, [guiding, language]);

  const adjustmentPoiNames = useMemo(() => {
    const names: Record<string, string> = {};
    for (const [poiId, poi] of Object.entries(poisById)) {
      names[poiId] = poi.poi_name;
    }
    for (const poi of adjustmentPois) {
      names[poi.poi_id] = poi.poi_name;
    }
    return names;
  }, [poisById, adjustmentPois]);

  if (!session || !match || !route || !preference) {
    return (
      <main className="flex flex-1 flex-col items-center justify-center bg-paper px-6 py-16 text-center">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
          {t(language, "navItinerary")}
        </p>
        <h1 className="mb-3 font-display text-3xl text-ink">{t(language, "itineraryEmptyTitle")}</h1>
        <p className="mb-8 max-w-md text-sm leading-relaxed text-ink-soft">
          {t(language, "itineraryEmptyLead")}
        </p>
        <Link
          to="/preferences"
          className="rounded-full bg-sage-deep px-6 py-3.5 text-sm font-medium text-paper transition hover:bg-moss"
        >
          {t(language, "itineraryEmptyCta")}
        </Link>
      </main>
    );
  }

  const activeSession = session;
  const activePreference = preference;
  const meta = formatWalkMeta({
    stops: nodes.length,
    walkKm: route.walk_distance_km ?? 0,
    durationHours: route.duration_hours ?? 0,
    physicalLevel: route.physical_level ?? "medium",
    stopsLabel: t(language, "stops"),
    about: t(language, "aboutHours"),
    physical: {
      low: t(language, "physicalLow"),
      med: t(language, "physicalMed"),
      high: t(language, "physicalHigh"),
    },
  });
  if (routeHasGamblingVenue(nodePoiIds, poisById)) {
    meta.push(t(language, "gamblingRiskReminder"));
  }

  const explanation = cleanRouteBlurb(
    typeof match.explanation?.summary === "string"
      ? match.explanation.summary
      : route.description,
  );
  const currentNode = nodes[currentIndex] ?? nodes[0];
  const triggerPoiName =
    triggerPayload?.poi?.poi_name ??
    triggerPayload?.guide_request?.poi ??
    currentNode?.name ??
    "POI";

  async function handleAdjustRoute() {
    const instruction = adjustInstruction.trim();
    if (!instruction || adjusting) return;

    setAdjusting(true);
    setAdjustError(null);
    setAdjustDraft(null);
    setAdjustmentPois([]);
    try {
      const result = await adjustRoute({
        route_id: route.id,
        instruction,
        preference: activePreference,
      });
      setAdjustDraft(buildRouteAdjustmentDraft(route, result));

      const adjustedPoiIds = [...result.route.nodes]
        .sort((a, b) => a.order - b.order)
        .map((node) => node.poi_id);
      try {
        setAdjustmentPois(await fetchRoutePois(adjustedPoiIds));
      } catch {
        // The preview can still use POI ids; MapRouteView retries after confirmation.
      }
    } catch (reason) {
      setAdjustError(
        reason instanceof Error ? reason.message : "Route adjustment failed",
      );
    } finally {
      setAdjusting(false);
    }
  }

  function handleConfirmAdjustment() {
    if (!adjustDraft?.has_actual_changes) return;
    const previousPoiId = currentNode?.poiId;
    const acceptedMatch = {
      ...match,
      route: adjustDraft.route,
      selected_template: adjustDraft.selected_template,
      candidate_pois: adjustDraft.candidate_pois,
      applied_constraints: adjustDraft.applied_constraints,
      explanation: adjustDraft.explanation,
      reasons:
        adjustDraft.rationale.length > 0
          ? adjustDraft.rationale
          : match.reasons,
    };
    const acceptedMatches = [...dayMatches];
    acceptedMatches[dayIndex] = acceptedMatch;

    const nextPoisById = { ...activeSession.poisById };
    for (const poi of adjustmentPois) {
      nextPoisById[poi.poi_id] = poi;
    }
    setSession({
      ...activeSession,
      preference: adjustDraft.preference_after,
      match: acceptedMatches[0] ?? acceptedMatch,
      matches: acceptedMatches,
      poisById: nextPoisById,
    });

    const acceptedNodes = [...adjustDraft.route.nodes].sort((a, b) => a.order - b.order);
    const retainedIndex = previousPoiId
      ? acceptedNodes.findIndex((node) => node.poi_id === previousPoiId)
      : -1;
    setCurrentIndex(retainedIndex >= 0 ? retainedIndex : 0);
    setAdjustInstruction("");
    setAdjustDraft(null);
    setAdjustmentPois([]);
    setAdjustError(null);
    setTriggerOpen(false);
    setNarration(null);
  }

  const adjustmentPanel = (
    <RouteAdjustmentPanel
      language={language}
      instruction={adjustInstruction}
      busy={adjusting}
      error={adjustError}
      draft={adjustDraft}
      poiNames={adjustmentPoiNames}
      onInstructionChange={setAdjustInstruction}
      onSubmit={() => void handleAdjustRoute()}
      onConfirm={handleConfirmAdjustment}
      onCancel={() => {
        setAdjustDraft(null);
        setAdjustmentPois([]);
        setAdjustError(null);
      }}
    />
  );

  async function simulateNearCurrentStop() {
    if (!currentNode) return;
    const poi = poisById[currentNode.poiId];
    if (!poi) {
      setError(t(language, "guideError"));
      return;
    }

    setGuiding(true);
    setChecking(true);
    setError(null);
    setStatusNote(t(language, "checkingNear"));
    try {
      const res = await triggerGuide({
        longitude: poi.longitude,
        latitude: poi.latitude,
        session_id: guideSessionId.current,
        radius_m: 120,
        language,
      });
      if (res.triggered || (res.poi && res.reason === "recently_triggered")) {
        setTriggerPayload(res);
        setTriggerMode("simulated");
        setTriggerOpen(true);
        setNarration(null);
        setStatusNote(null);
      } else {
        setError(t(language, "guideError"));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t(language, "guideError"));
    } finally {
      setChecking(false);
    }
  }

  async function checkInCurrentStop() {
    if (!currentNode) return;
    if (!navigator.geolocation) {
      setError(t(language, "gpsUnsupported"));
      return;
    }
    setError(null);
    setStatusNote(t(language, "tripSimulateArriveBusy"));
    try {
      const position = await new Promise<GeolocationPosition>((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 12_000,
          maximumAge: 10_000,
        }),
      );
      await checkInAtLocation(
        tripUserId,
        route.id,
        currentNode.poiId,
        {
          longitude: position.coords.longitude,
          latitude: position.coords.latitude,
          accuracy: position.coords.accuracy,
        },
        nodePoiIds,
      );
      setStatusNote(t(language, "tripSimulateArriveDone"));
    } catch (err) {
      setStatusNote(null);
      const raw = err instanceof Error ? err.message : "";
      setError(
        raw === "TRIP_BACKEND_STALE"
          ? t(language, "tripBackendStale")
          : raw === "TRIP_POI_MISMATCH" || /not part of trip/i.test(raw)
            ? t(language, "tripPoiMismatch")
            : raw || t(language, "tripSimulateArriveError"),
      );
    }
  }

  function handleStartGuide() {
    setGuiding(true);
    setTriggerOpen(false);
    setNarration(null);
    setError(null);
    lastGpsCheckRef.current = 0;
    setStatusNote(t(language, "gpsWatching"));
  }

  function handleNextStop() {
    if (currentIndex >= nodes.length - 1) return;
    setCurrentIndex((i) => i + 1);
    setTriggerOpen(false);
    setNarration(null);
    setStatusNote(t(language, "gpsWatching"));
  }

  function handleSelectStop(index: number) {
    if (index < 0 || index >= nodes.length || index === currentIndex) return;
    setCurrentIndex(index);
    setTriggerOpen(false);
    setNarration(null);
    setStatusNote(guiding ? t(language, "gpsWatching") : null);
  }

  async function handleAcceptGuide() {
    const poiName =
      triggerPayload?.guide_request?.poi ??
      triggerPayload?.poi?.poi_name ??
      currentNode?.name;
    if (!poiName) return;

    const poiId = triggerPayload?.poi?.poi_id ?? currentNode?.poiId ?? "";
    const next = nodes[currentIndex + 1];
    setTriggerOpen(false);
    setGenerating(false);
    setNarration(null);
    const params = new URLSearchParams({
      poi: poiId || poiName,
      name: poiName,
      from: "walk",
    });
    if (next) {
      params.set("next", next.name);
      params.set("nextId", next.poiId);
    } else {
      params.set("next", "");
    }
    navigate(`/guide?${params.toString()}`);
  }

  const askLabel =
    triggerMode === "simulated"
      ? t(language, "triggerAskSimulated")
      : triggerPayload?.prompt || t(language, "triggerAsk");

  const currentPoiChecked = Boolean(
    currentNode?.poiId && trip?.checked_in_poi_ids.includes(currentNode.poiId),
  );

  const tripPanel = (
    <div className="mt-6">
      <TripControls
        userId={tripUserId}
        routeId={route.id}
        currentPoiId={currentNode?.poiId}
        stopPoiIds={nodePoiIds}
      />
    </div>
  );

  return (
    <main className="relative flex flex-1 flex-col bg-paper text-ink">
      <div className="sticky top-14 z-30 grid shrink-0 grid-cols-[1fr_auto_1fr] items-center border-b border-line/60 bg-paper/90 px-5 py-2.5 backdrop-blur-md lg:px-8">
        <Link to="/profile" className="justify-self-start text-sm text-ink-soft hover:text-ink">
          {t(language, "adjustPrefs")}
        </Link>
        <div className="flex items-center gap-2">
          <span className="inline-block size-1.5 rounded-full bg-sage-deep" />
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
            {guiding ? t(language, "guidingActive") : t(language, "activeRoute")}
          </span>
        </div>
      </div>

      <div className="grid lg:grid-cols-[minmax(0,1fr)_minmax(280px,420px)] lg:items-start">
        <div className="relative z-0 min-h-[50dvh] isolate overflow-hidden bg-paper-warm lg:sticky lg:top-[7.25rem] lg:h-[calc(100dvh-7.25rem)] lg:min-h-0">
          <MapRouteView
            poiIds={nodePoiIds}
            currentPoiId={currentNode?.poiId}
            userLocation={userLocation}
            recenterToken={mapRecenterToken}
            onSelectPoi={(poiId) => {
              const index = nodes.findIndex((node) => node.poiId === poiId);
              if (index >= 0) handleSelectStop(index);
            }}
          />

          <button
            type="button"
            aria-label={t(language, "locateMe")}
            disabled={checking || generating}
            onClick={() => {
              setGuiding(true);
              lastGpsCheckRef.current = 0;
              setStatusNote(t(language, "gpsWatching"));
              if (!navigator.geolocation) {
                setStatusNote(t(language, "gpsUnsupported"));
                return;
              }
              navigator.geolocation.getCurrentPosition(
                (pos) => {
                  setUserLocation({
                    latitude: pos.coords.latitude,
                    longitude: pos.coords.longitude,
                  });
                  setMapRecenterToken((token) => token + 1);
                },
                () => {
                  setStatusNote(t(language, "locationDenied"));
                },
                {
                  enableHighAccuracy: true,
                  maximumAge: 5000,
                  timeout: 15_000,
                },
              );
            }}
            className="absolute bottom-24 right-5 z-10 grid size-11 place-items-center rounded-full border border-line bg-paper text-sage-deep shadow-[var(--shadow-soft)] hover:bg-paper-warm disabled:opacity-50 lg:bottom-8 lg:right-8"
          >
            ◎
          </button>

          {(statusNote || error) && !triggerOpen && !narration ? (
            <div className="absolute left-1/2 top-6 z-10 w-[calc(100%-2.5rem)] max-w-sm -translate-x-1/2 rounded-2xl border border-line bg-paper/95 px-4 py-3 text-sm shadow-[var(--shadow-soft)] lg:left-8 lg:top-auto lg:bottom-8 lg:translate-x-0">
              {error ? (
                <p className="text-clay">{error}</p>
              ) : (
                <p className="text-ink-soft">{statusNote}</p>
              )}
            </div>
          ) : null}

          {triggerOpen ? (
            <div className="pointer-events-auto absolute left-1/2 top-6 z-20 w-[calc(100%-2.5rem)] max-w-sm -translate-x-1/2 lg:bottom-8 lg:left-8 lg:top-auto lg:w-80 lg:translate-x-0">
              <TriggerModal
                poiName={triggerPoiName}
                nearLabel={t(language, "triggerNear")}
                askLabel={askLabel}
                dismissLabel={t(language, "triggerDismiss")}
                acceptLabel={
                  generating ? t(language, "generatingGuide") : t(language, "triggerAccept")
                }
                busy={generating}
                onAccept={() => void handleAcceptGuide()}
                onDismiss={() => setTriggerOpen(false)}
              />
            </div>
          ) : null}

          {narration ? (
            <div className="pointer-events-auto absolute left-1/2 top-6 z-20 w-[calc(100%-2.5rem)] max-w-md -translate-x-1/2 lg:bottom-8 lg:left-8 lg:top-auto lg:translate-x-0">
              <NarrationCard
                title={t(language, "narrationTitle")}
                poiName={narration.poiName}
                text={narration.text || t(language, "narrationEmpty")}
                sourceType={narration.sourceType}
                audioUrl={narration.audioUrl}
                ttsHint={narration.ttsFailed ? t(language, "ttsUnavailable") : null}
                closeLabel={t(language, "narrationClose")}
                onClose={() => setNarration(null)}
              />
            </div>
          ) : null}
        </div>

        <aside className="relative z-10 hidden border-l border-line/70 bg-paper lg:sticky lg:top-[7.25rem] lg:block lg:max-h-[calc(100dvh-7.25rem)] lg:overflow-y-auto lg:overscroll-contain">
          <RouteInfoPanel
            title={route.name}
            theme={route.theme}
            meta={meta}
            reasons={match.reasons}
            explanation={explanation}
            adjustmentPanel={adjustmentPanel}
            tripPanel={tripPanel}
            nodes={nodes}
            legs={walkLegs}
            legsLoading={walkLegsLoading}
            lockScroll={false}
            chapterLabel={t(language, "chapterIII")}
            itineraryLabel={t(language, "itinerary")}
            simulateLabel={t(language, "simulateNear")}
            simulateArriveLabel={t(language, "tripSimulateArrive")}
            simulateArriveDone={currentPoiChecked}
            simulateArriveDisabled={tripLoading || !currentNode}
            startGuideLabel={
              checking
                ? t(language, "checkingNear")
                : guiding
                  ? t(language, "nextStopGuide")
                  : t(language, "startGuide")
            }
            startDisabled={checking || generating}
            onSimulate={() => void simulateNearCurrentStop()}
            onSimulateArrive={() => void checkInCurrentStop()}
            onStartGuide={() => (guiding ? handleNextStop() : handleStartGuide())}
            onSelectStop={handleSelectStop}
            curatorSuffix={t(language, "curatorSuffix")}
            stayLabel={t(language, "stayMinutes")}
            walkLegLabel={t(language, "walkLegLabel")}
            busLegLabel={t(language, "busLegLabel")}
            busStopLegLabel={t(language, "busStopLegLabel")}
            legsLoadingLabel={t(language, "walkLegsLoading")}
            multiDay={
              isMultiDay
                ? {
                    label: t(language, "dayPlanLabel"),
                    days: dayMatches.map((_, i) =>
                      t(language, "dayN").replace("{n}", String(i + 1)),
                    ),
                    activeIndex: dayIndex,
                    onSelect: setDayIndex,
                  }
                : null
            }
          />
        </aside>
      </div>

      <div
        className={`fixed inset-x-0 bottom-0 z-40 flex flex-col rounded-t-3xl border-t border-line bg-paper shadow-[0_-8px_32px_rgba(47,49,40,0.12)] lg:hidden ${
          sheetDragging ? "" : "transition-[height] duration-300 ease-out"
        }`}
        style={{ height: sheetHeight }}
      >
        <button
          type="button"
          onPointerDown={onSheetHandlePointerDown}
          onPointerMove={onSheetHandlePointerMove}
          onPointerUp={endSheetHandleDrag}
          onPointerCancel={endSheetHandleDrag}
          className="flex w-full shrink-0 cursor-grab touch-none justify-center py-3 active:cursor-grabbing"
          aria-label="sheet"
        >
          <span className="h-1 w-10 rounded-full bg-line" />
        </button>
        <div className="min-h-0 flex-1">
          <RouteInfoPanel
            title={route.name}
            theme={route.theme}
            meta={meta}
            reasons={match.reasons}
            explanation={explanation}
            adjustmentPanel={adjustmentPanel}
            tripPanel={tripPanel}
            nodes={nodes}
            legs={walkLegs}
            legsLoading={walkLegsLoading}
            compact={sheetOpen === "peek"}
            lockScroll
            chapterLabel={t(language, "chapterIII")}
            itineraryLabel={t(language, "itinerary")}
            simulateLabel={t(language, "simulateNear")}
            simulateArriveLabel={t(language, "tripSimulateArrive")}
            simulateArriveDone={currentPoiChecked}
            simulateArriveDisabled={tripLoading || !currentNode}
            startGuideLabel={
              checking
                ? t(language, "checkingNear")
                : guiding
                  ? t(language, "nextStopGuide")
                  : t(language, "startGuide")
            }
            startDisabled={checking || generating}
            onSimulate={() => void simulateNearCurrentStop()}
            onSimulateArrive={() => void checkInCurrentStop()}
            onStartGuide={() => (guiding ? handleNextStop() : handleStartGuide())}
            onSelectStop={handleSelectStop}
            curatorSuffix={t(language, "curatorSuffix")}
            stayLabel={t(language, "stayMinutes")}
            walkLegLabel={t(language, "walkLegLabel")}
            busLegLabel={t(language, "busLegLabel")}
            busStopLegLabel={t(language, "busStopLegLabel")}
            legsLoadingLabel={t(language, "walkLegsLoading")}
            multiDay={
              isMultiDay
                ? {
                    label: t(language, "dayPlanLabel"),
                    days: dayMatches.map((_, i) =>
                      t(language, "dayN").replace("{n}", String(i + 1)),
                    ),
                    activeIndex: dayIndex,
                    onSelect: setDayIndex,
                  }
                : null
            }
          />
        </div>
      </div>
    </main>
  );
}

function TriggerModal({
  poiName,
  nearLabel,
  askLabel,
  dismissLabel,
  acceptLabel,
  busy,
  onAccept,
  onDismiss,
}: {
  poiName: string;
  nearLabel: string;
  askLabel: string;
  dismissLabel: string;
  acceptLabel: string;
  busy?: boolean;
  onAccept: () => void;
  onDismiss: () => void;
}) {
  return (
    <div className="rounded-2xl border border-line bg-paper p-5 shadow-[var(--shadow-lift)]">
      <div className="mb-4 flex items-start gap-3">
        <div className="grid size-11 shrink-0 place-items-center rounded-xl bg-sage-deep/10 font-serif text-lg text-sage-deep">
          ✦
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink">
            {nearLabel} <span className="text-sage-deep">{poiName}</span>
          </p>
          <p className="mt-0.5 text-xs text-ink-soft">{askLabel}</p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={onDismiss}
          className="h-11 rounded-full border border-line bg-card text-sm font-medium text-ink hover:bg-paper-warm disabled:opacity-50"
        >
          {dismissLabel}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onAccept}
          className="h-11 rounded-full bg-sage-deep text-sm font-medium text-paper hover:bg-moss disabled:opacity-60"
        >
          {acceptLabel}
        </button>
      </div>
    </div>
  );
}

function NarrationCard({
  title,
  poiName,
  text,
  sourceType,
  audioUrl,
  ttsHint,
  closeLabel,
  onClose,
}: {
  title: string;
  poiName: string;
  text: string;
  sourceType?: string;
  audioUrl?: string;
  ttsHint?: string | null;
  closeLabel: string;
  onClose: () => void;
}) {
  return (
    <div className="max-h-[70vh] overflow-y-auto rounded-2xl border border-line bg-paper p-5 shadow-[var(--shadow-lift)]">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-sage-deep">
            {title}
          </p>
          <h3 className="mt-1 font-display text-lg text-ink">{poiName}</h3>
          {sourceType ? (
            <p className="mt-1 text-[11px] text-ink-soft">source · {sourceType}</p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={onClose}
          className="shrink-0 text-xs text-ink-soft hover:text-ink"
        >
          {closeLabel}
        </button>
      </div>
      <p className="text-sm leading-relaxed text-ink">{text}</p>
      {audioUrl ? (
        <audio className="mt-4 w-full" controls src={audioUrl} preload="none">
          <track kind="captions" />
        </audio>
      ) : ttsHint ? (
        <p className="mt-3 text-xs text-ink-soft">{ttsHint}</p>
      ) : null}
    </div>
  );
}

function RouteInfoPanel({
  title,
  theme,
  meta,
  reasons,
  explanation,
  adjustmentPanel,
  tripPanel,
  nodes,
  legs = [],
  legsLoading = false,
  compact,
  lockScroll = true,
  chapterLabel,
  itineraryLabel,
  simulateLabel,
  simulateArriveLabel,
  simulateArriveDone,
  simulateArriveDisabled,
  startGuideLabel,
  startDisabled,
  onSimulate,
  onSimulateArrive,
  onStartGuide,
  onSelectStop,
  curatorSuffix,
  stayLabel,
  walkLegLabel,
  busLegLabel,
  busStopLegLabel,
  legsLoadingLabel,
  multiDay,
}: {
  title: string;
  theme: string;
  meta: string[];
  reasons: string[];
  explanation: string;
  adjustmentPanel?: ReactNode;
  tripPanel?: ReactNode;
  nodes: DisplayNode[];
  legs?: WalkLeg[];
  legsLoading?: boolean;
  compact?: boolean;
  /** When true, panel fills parent and scrolls internally (mobile sheet). */
  lockScroll?: boolean;
  chapterLabel: string;
  itineraryLabel: string;
  simulateLabel: string;
  simulateArriveLabel: string;
  simulateArriveDone?: boolean;
  simulateArriveDisabled?: boolean;
  startGuideLabel: string;
  startDisabled?: boolean;
  onSimulate: () => void;
  onSimulateArrive: () => void;
  onStartGuide: () => void;
  onSelectStop?: (index: number) => void;
  curatorSuffix: string;
  stayLabel: string;
  walkLegLabel: string;
  busLegLabel: string;
  busStopLegLabel?: string;
  legsLoadingLabel?: string;
  multiDay?: {
    label: string;
    days: string[];
    activeIndex: number;
    onSelect: (index: number) => void;
  } | null;
}) {
  return (
    <div className={lockScroll ? "flex h-full min-h-0 flex-col" : "flex flex-col"}>
      <div
        className={
          lockScroll ? "min-h-0 flex-1 overflow-y-auto overscroll-contain" : undefined
        }
      >
        <div className="px-6 pt-4 lg:px-8 lg:pt-8">
          {multiDay ? (
            <div className="mb-5">
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-ink-soft">
                {multiDay.label}
              </p>
              <div className="flex flex-wrap gap-2">
                {multiDay.days.map((label, i) => {
                  const active = i === multiDay.activeIndex;
                  return (
                    <button
                      key={label}
                      type="button"
                      onClick={() => multiDay.onSelect(i)}
                      className={`rounded-full border px-3.5 py-1.5 text-xs transition ${
                        active
                          ? "border-sage-deep bg-sage-deep text-paper"
                          : "border-line bg-card text-ink hover:border-sage"
                      }`}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>
          ) : null}
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
            {chapterLabel} · {theme}
          </p>
          <h2 className="font-display text-2xl leading-tight text-ink lg:text-3xl">{title}</h2>
          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-soft">
            {meta.map((item, i) => (
              <span key={item} className="flex items-center gap-3">
                {i > 0 ? <span className="size-1 rounded-full bg-line" /> : null}
                <span className={i === meta.length - 1 ? "text-ochre" : undefined}>{item}</span>
              </span>
            ))}
          </div>

          {!compact ? (
            <>
              <div className="mt-5">
                <ReasonChips reasons={reasons} />
              </div>
              {explanation ? (
                <p className="mt-6 text-xs italic leading-relaxed text-ink-soft">
                  「{explanation}」{curatorSuffix}
                </p>
              ) : null}
              {adjustmentPanel}
              {tripPanel}
            </>
          ) : null}
        </div>

        {!compact ? (
          <div className="mt-8 px-6 pb-6 lg:px-8">
            <p className="mb-4 text-[10px] font-semibold uppercase tracking-[0.22em] text-ink-soft">
              {itineraryLabel}
            </p>
            <RouteNodeList
              nodes={nodes}
              legs={legs}
              legsLoading={legsLoading}
              stayLabel={stayLabel}
              walkLegLabel={walkLegLabel}
              busLegLabel={busLegLabel}
              busStopLegLabel={busStopLegLabel}
              legsLoadingLabel={legsLoadingLabel}
              onSelectIndex={onSelectStop}
            />
          </div>
        ) : null}
      </div>

      <div
        className={
          lockScroll
            ? "relative z-20 shrink-0 border-t border-line bg-paper px-6 py-4 lg:px-8 lg:py-5"
            : "sticky bottom-0 z-20 border-t border-line bg-paper/95 px-6 py-4 backdrop-blur-md lg:px-8 lg:py-5"
        }
      >
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 sm:gap-3">
            <button
              type="button"
              disabled={simulateArriveDisabled || simulateArriveDone}
              onClick={onSimulateArrive}
              className="h-11 min-w-0 flex-1 rounded-full border border-sage-deep bg-sage-deep/10 px-3 text-xs font-medium text-sage-deep hover:bg-sage-deep hover:text-paper disabled:pointer-events-none disabled:opacity-50 sm:h-12 sm:px-4 sm:text-sm"
            >
              {simulateArriveDone ? "✓ " : ""}
              {simulateArriveLabel}
            </button>
            <button
              type="button"
              disabled={startDisabled}
              onClick={onSimulate}
              className="h-11 min-w-0 flex-1 rounded-full border border-line bg-paper px-3 text-xs text-ink hover:bg-paper-warm disabled:pointer-events-none disabled:opacity-50 sm:h-12 sm:px-4 sm:text-sm"
            >
              {simulateLabel}
            </button>
          </div>
          <button
            type="button"
            disabled={startDisabled}
            onClick={onStartGuide}
            className="h-12 w-full rounded-full bg-sage-deep text-center font-medium text-paper shadow-[var(--shadow-soft)] hover:bg-moss disabled:pointer-events-none disabled:opacity-60"
          >
            {startGuideLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
