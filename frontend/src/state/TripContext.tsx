import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  checkInTrip,
  checkInTripAtLocation,
  createTrip,
  getCurrentTrip,
  getTrip,
  TripApiError,
} from "@/api/trips";
import { rememberLastTripId } from "@/lib/lastTrip";
import type { Trip, TripProgress } from "@/types/trips";

interface TripContextValue {
  trip: Trip | null;
  progress: TripProgress | null;
  loading: boolean;
  error: string | null;
  startTrip: (
    userId: string,
    routeId: string,
    stopPoiIds?: string[],
  ) => Promise<void>;
  loadCurrentTrip: (userId: string) => Promise<void>;
  loadTrip: (tripId: string) => Promise<void>;
  checkIn: (poiId: string) => Promise<void>;
  /**
   * Demo/local path: ensure an active trip whose stops match the current walk,
   * then check in (no GPS). One tap rebuilds when walk nodes diverge.
   */
  simulateArrive: (
    userId: string,
    routeId: string,
    poiId: string,
    stopPoiIds?: string[],
  ) => Promise<void>;
  checkInAtLocation: (
    userId: string,
    routeId: string,
    poiId: string,
    location: { longitude: number; latitude: number; accuracy?: number },
    stopPoiIds?: string[],
  ) => Promise<void>;
  clearTrip: () => void;
  clearError: () => void;
}

const TripContext = createContext<TripContextValue | null>(null);

function friendlyTripError(message: string): string {
  if (/not part of trip/i.test(message)) {
    return "TRIP_POI_MISMATCH";
  }
  return message;
}

function errorMessage(error: unknown): string {
  if (error instanceof TripApiError) return friendlyTripError(error.message);
  if (error instanceof Error) return friendlyTripError(error.message);
  return "请求失败，请稍后重试";
}

/** Ensure the selected stop is always in the create payload (order preserved). */
export function ensureStopListIncludes(
  stopPoiIds: string[] | undefined,
  poiId: string,
): string[] {
  const cleaned = (stopPoiIds ?? [])
    .map((id) => id.trim())
    .filter(Boolean);
  const seen = new Set<string>();
  const ordered: string[] = [];
  for (const id of cleaned) {
    if (seen.has(id)) continue;
    seen.add(id);
    ordered.push(id);
  }
  if (poiId && !seen.has(poiId)) {
    ordered.unshift(poiId);
  }
  return ordered;
}

function sameStopSet(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  const setB = new Set(b);
  return a.every((id) => setB.has(id));
}

/**
 * Trip is usable for this arrive when it is active for the route and includes
 * the current POI. If walk stop lists are provided, they must match (order-insensitive
 * for membership; we recreate when the current POI is missing).
 */
function tripCoversArrive(
  trip: Trip | null,
  routeId: string,
  desiredStops: string[],
  poiId: string,
): boolean {
  if (!trip || trip.route_id !== routeId || trip.status !== "active") return false;
  if (!trip.stop_poi_ids.includes(poiId)) return false;
  if (desiredStops.length > 0 && !sameStopSet(trip.stop_poi_ids, desiredStops)) {
    return false;
  }
  return true;
}

export function TripProvider({ children }: { children: ReactNode }) {
  const [trip, setTrip] = useState<Trip | null>(null);
  const [progress, setProgress] = useState<TripProgress | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const applyResponse = useCallback(
    (response: { trip: Trip; progress: TripProgress }) => {
      rememberLastTripId(response.trip.trip_id);
      setTrip(response.trip);
      setProgress(response.progress);
      setError(null);
    },
    [],
  );

  const startTrip = useCallback(
    async (userId: string, routeId: string, stopPoiIds?: string[]) => {
      setLoading(true);
      setError(null);
      try {
        applyResponse(
          await createTrip({
            user_id: userId,
            route_id: routeId,
            stop_poi_ids: stopPoiIds?.length ? stopPoiIds : undefined,
          }),
        );
      } catch (requestError) {
        setError(errorMessage(requestError));
        throw requestError;
      } finally {
        setLoading(false);
      }
    },
    [applyResponse],
  );

  const loadCurrentTrip = useCallback(
    async (userId: string) => {
      setLoading(true);
      setError(null);
      try {
        applyResponse(await getCurrentTrip(userId));
      } catch (requestError) {
        if (requestError instanceof TripApiError && requestError.status === 404) {
          setTrip(null);
          setProgress(null);
          return;
        }
        setError(errorMessage(requestError));
        throw requestError;
      } finally {
        setLoading(false);
      }
    },
    [applyResponse],
  );

  const loadTrip = useCallback(
    async (tripId: string) => {
      setLoading(true);
      setError(null);
      try {
        applyResponse(await getTrip(tripId));
      } catch (requestError) {
        setError(errorMessage(requestError));
        throw requestError;
      } finally {
        setLoading(false);
      }
    },
    [applyResponse],
  );

  const checkIn = useCallback(
    async (poiId: string) => {
      if (!trip) {
        const tripError = new Error("请先开始行程");
        setError(tripError.message);
        throw tripError;
      }
      setLoading(true);
      setError(null);
      try {
        applyResponse(await checkInTrip(trip.trip_id, { poi_id: poiId }));
      } catch (requestError) {
        setError(errorMessage(requestError));
        throw requestError;
      } finally {
        setLoading(false);
      }
    },
    [applyResponse, trip],
  );

  const simulateArrive = useCallback(
    async (
      userId: string,
      routeId: string,
      poiId: string,
      stopPoiIds?: string[],
    ) => {
      setLoading(true);
      setError(null);
      try {
        const desiredStops = ensureStopListIncludes(stopPoiIds, poiId);
        if (!desiredStops.includes(poiId)) {
          const missing = new Error("TRIP_POI_MISMATCH");
          setError(missing.message);
          throw missing;
        }

        let active = trip;
        if (!tripCoversArrive(active, routeId, desiredStops, poiId)) {
          const created = await createTrip({
            user_id: userId,
            route_id: routeId,
            stop_poi_ids: desiredStops,
          });
          applyResponse(created);
          active = created.trip;

          // Stale backends ignore stop_poi_ids and keep template stops only.
          if (!active.stop_poi_ids.includes(poiId)) {
            const stale = new Error("TRIP_BACKEND_STALE");
            setError(stale.message);
            throw stale;
          }
        }

        if (!active) {
          const missing = new Error("TRIP_POI_MISMATCH");
          setError(missing.message);
          throw missing;
        }

        if (!active.checked_in_poi_ids.includes(poiId)) {
          applyResponse(await checkInTrip(active.trip_id, { poi_id: poiId }));
        }
      } catch (requestError) {
        setError(errorMessage(requestError));
        throw requestError;
      } finally {
        setLoading(false);
      }
    },
    [applyResponse, trip],
  );

  const checkInAtLocation = useCallback(
    async (
      userId: string,
      routeId: string,
      poiId: string,
      location: { longitude: number; latitude: number; accuracy?: number },
      stopPoiIds?: string[],
    ) => {
      setLoading(true);
      setError(null);
      try {
        const desiredStops = ensureStopListIncludes(stopPoiIds, poiId);
        let active = trip;
        if (!tripCoversArrive(active, routeId, desiredStops, poiId)) {
          const created = await createTrip({
            user_id: userId,
            route_id: routeId,
            stop_poi_ids: desiredStops,
          });
          applyResponse(created);
          active = created.trip;
        }
        if (!active || !active.stop_poi_ids.includes(poiId)) {
          throw new Error("TRIP_POI_MISMATCH");
        }
        if (!active.checked_in_poi_ids.includes(poiId)) {
          applyResponse(
            await checkInTripAtLocation(active.trip_id, {
              poi_id: poiId,
              longitude: location.longitude,
              latitude: location.latitude,
              accuracy_m: location.accuracy,
              radius_m: 120,
            }),
          );
        }
      } catch (requestError) {
        setError(errorMessage(requestError));
        throw requestError;
      } finally {
        setLoading(false);
      }
    },
    [applyResponse, trip],
  );

  const clearTrip = useCallback(() => {
    setTrip(null);
    setProgress(null);
    setError(null);
  }, []);
  const clearError = useCallback(() => setError(null), []);

  const value = useMemo<TripContextValue>(
    () => ({
      trip,
      progress,
      loading,
      error,
      startTrip,
      loadCurrentTrip,
      loadTrip,
      checkIn,
      simulateArrive,
      checkInAtLocation,
      clearTrip,
      clearError,
    }),
    [
      trip,
      progress,
      loading,
      error,
      startTrip,
      loadCurrentTrip,
      loadTrip,
      checkIn,
      simulateArrive,
      checkInAtLocation,
      clearTrip,
      clearError,
    ],
  );

  return <TripContext.Provider value={value}>{children}</TripContext.Provider>;
}

export function useTrip(): TripContextValue {
  const context = useContext(TripContext);
  if (!context) throw new Error("useTrip must be used within TripProvider");
  return context;
}
