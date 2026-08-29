import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  getCookie,
  readCookieJson,
  readExpiringLocal,
  removeCookie,
  setCookie,
  writeCookieJson,
  writeExpiringLocal,
} from "@/lib/persist";
import type { LanguageCode, MatchResult, POI, Preference, WalkSession } from "@/types";

const SESSION_KEY = "macau-storywalk-session";
const LANG_KEY = "macau-storywalk-lang";
const PREF_KEY = "macau-storywalk-preference";

interface WalkContextValue {
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
  activeItineraryDay: number;
  setActiveItineraryDay: (day: number) => void;
  preference: Preference | null;
  session: WalkSession | null;
  setSession: (session: WalkSession) => void;
  clearSession: () => void;
  updatePreference: (preference: Preference) => void;
  saveMatch: (args: {
    preference: Preference;
    match: MatchResult;
    matches?: MatchResult[];
    pois: POI[];
  }) => void;
}

const WalkContext = createContext<WalkContextValue | null>(null);

function isLanguage(value: string | null): value is LanguageCode {
  return value === "zh-CN" || value === "zh-TW" || value === "en" || value === "pt";
}

function migrateLegacyStorage() {
  try {
    const legacyLang = localStorage.getItem(LANG_KEY);
    if (legacyLang && !getCookie(LANG_KEY)) {
      setCookie(LANG_KEY, legacyLang);
      localStorage.removeItem(LANG_KEY);
    }
  } catch {
    // ignore
  }
  try {
    const legacyPref = localStorage.getItem(PREF_KEY);
    if (legacyPref && !getCookie(PREF_KEY)) {
      setCookie(PREF_KEY, legacyPref);
      localStorage.removeItem(PREF_KEY);
    }
  } catch {
    // ignore
  }
  try {
    const legacySession = sessionStorage.getItem(SESSION_KEY);
    if (legacySession && !readExpiringLocal(SESSION_KEY)) {
      const parsed = JSON.parse(legacySession) as WalkSession;
      writeExpiringLocal(SESSION_KEY, parsed);
      sessionStorage.removeItem(SESSION_KEY);
    }
  } catch {
    // ignore
  }
}

function readLanguage(): LanguageCode {
  migrateLegacyStorage();
  const fromCookie = getCookie(LANG_KEY);
  if (isLanguage(fromCookie)) return fromCookie;
  try {
    const session = readSession();
    if (session?.language && isLanguage(session.language)) return session.language;
  } catch {
    // ignore
  }
  return "zh-CN";
}

function writeLanguage(lang: LanguageCode) {
  setCookie(LANG_KEY, lang);
}

function readSession(): WalkSession | null {
  migrateLegacyStorage();
  return readExpiringLocal<WalkSession>(SESSION_KEY);
}

function writeSession(session: WalkSession | null) {
  writeExpiringLocal(SESSION_KEY, session);
  if (!session) {
    try {
      sessionStorage.removeItem(SESSION_KEY);
    } catch {
      // ignore
    }
  }
}

function readPreference(): Preference | null {
  migrateLegacyStorage();
  return readCookieJson<Preference>(PREF_KEY);
}

function writePreference(preference: Preference | null) {
  writeCookieJson(PREF_KEY, preference);
  if (!preference) removeCookie(PREF_KEY);
}

export function WalkProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<LanguageCode>(() => readLanguage());
  const [activeItineraryDay, setActiveItineraryDayState] = useState(1);
  const [session, setSessionState] = useState<WalkSession | null>(() => readSession());
  const [preference, setPreferenceState] = useState<Preference | null>(() => {
    return readPreference() ?? readSession()?.preference ?? null;
  });

  const setLanguage = useCallback((lang: LanguageCode) => {
    setLanguageState(lang);
    writeLanguage(lang);
    document.documentElement.lang = lang;
  }, []);

  const setActiveItineraryDay = useCallback((day: number) => {
    setActiveItineraryDayState(Math.max(1, Math.round(day)));
  }, []);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const setSession = useCallback(
    (next: WalkSession) => {
      setSessionState(next);
      writeSession(next);
      setPreferenceState(next.preference);
      writePreference(next.preference);
      setLanguage(next.language);
    },
    [setLanguage],
  );

  const clearSession = useCallback(() => {
    setSessionState(null);
    writeSession(null);
  }, []);

  const updatePreference = useCallback(
    (nextPref: Preference) => {
      const lang = isLanguage(nextPref.language) ? nextPref.language : language;
      const normalized = { ...nextPref, language: lang };
      setPreferenceState(normalized);
      writePreference(normalized);
      setLanguage(lang);
      setSessionState((prev) => {
        if (!prev) return prev;
        const next: WalkSession = { ...prev, preference: normalized, language: lang };
        writeSession(next);
        return next;
      });
    },
    [language, setLanguage],
  );

  const saveMatch = useCallback(
    (args: {
      preference: Preference;
      match: MatchResult;
      matches?: MatchResult[];
      pois: POI[];
    }) => {
      const poisById: Record<string, POI> = {};
      for (const poi of args.pois) {
        poisById[poi.poi_id] = poi;
      }
      const next: WalkSession = {
        language: (args.preference.language as LanguageCode) || language,
        preference: args.preference,
        match: args.match,
        matches: args.matches?.length ? args.matches : [args.match],
        poisById,
      };
      setActiveItineraryDayState(1);
      setSession(next);
    },
    [language, setSession],
  );

  const value = useMemo(
    () => ({
      language,
      setLanguage,
      activeItineraryDay,
      setActiveItineraryDay,
      preference,
      session,
      setSession,
      clearSession,
      updatePreference,
      saveMatch,
    }),
    [
      language,
      setLanguage,
      activeItineraryDay,
      setActiveItineraryDay,
      preference,
      session,
      setSession,
      clearSession,
      updatePreference,
      saveMatch,
    ],
  );

  return <WalkContext.Provider value={value}>{children}</WalkContext.Provider>;
}

export function useWalk(): WalkContextValue {
  const ctx = useContext(WalkContext);
  if (!ctx) {
    throw new Error("useWalk must be used within WalkProvider");
  }
  return ctx;
}
