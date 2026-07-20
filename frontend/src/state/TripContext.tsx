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
  createTrip,
  getCurrentTrip,
  getTrip,
  TripApiError,
} from "@/api/trips";
import type { Trip, TripProgress } from "@/types/trips";

interface TripContextValue {
  trip: Trip | null;
  progress: TripProgress | null;
  loading: boolean;
  error: string | null;
  startTrip: (userId: string, routeId: string) => Promise<void>;
  loadCurrentTrip: (userId: string) => Promise<void>;
  loadTrip: (tripId: string) => Promise<void>;
  checkIn: (poiId: string) => Promise<void>;
  clearTrip: () => void;
  clearError: () => void;
}

const TripContext = createContext<TripContextValue | null>(null);

function errorMessage(error: unknown): string {
  if (error instanceof TripApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "请求失败，请稍后重试";
}

export function TripProvider({ children }: { children: ReactNode }) {
  const [trip, setTrip] = useState<Trip | null>(null);
  const [progress, setProgress] = useState<TripProgress | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const applyResponse = useCallback(
    (response: { trip: Trip; progress: TripProgress }) => {
      setTrip(response.trip);
      setProgress(response.progress);
      setError(null);
    },
    [],
  );

  const startTrip = useCallback(
    async (userId: string, routeId: string) => {
      setLoading(true);
      setError(null);
      try {
        applyResponse(await createTrip({ user_id: userId, route_id: routeId }));
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
