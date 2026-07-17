/** 测试期持久化：Cookie Max-Age = 3 天；大体积行程走 localStorage + 同期过期。 */

export const PERSIST_MAX_AGE_SEC = 3 * 24 * 60 * 60;
export const PERSIST_TTL_MS = PERSIST_MAX_AGE_SEC * 1000;

interface ExpiringEnvelope<T> {
  expiresAt: number;
  data: T;
}

export function setCookie(name: string, value: string, maxAgeSec = PERSIST_MAX_AGE_SEC) {
  try {
    document.cookie = [
      `${encodeURIComponent(name)}=${encodeURIComponent(value)}`,
      `Max-Age=${maxAgeSec}`,
      "Path=/",
      "SameSite=Lax",
    ].join("; ");
  } catch {
    // ignore
  }
}

export function getCookie(name: string): string | null {
  try {
    const prefix = `${encodeURIComponent(name)}=`;
    for (const part of document.cookie.split(";")) {
      const trimmed = part.trim();
      if (trimmed.startsWith(prefix)) {
        return decodeURIComponent(trimmed.slice(prefix.length));
      }
    }
  } catch {
    // ignore
  }
  return null;
}

export function removeCookie(name: string) {
  try {
    document.cookie = `${encodeURIComponent(name)}=; Max-Age=0; Path=/; SameSite=Lax`;
  } catch {
    // ignore
  }
}

/** 小数据：语言 / 偏好 → Cookie（3 天）。 */
export function writeCookieJson(name: string, value: unknown | null) {
  if (value == null) {
    removeCookie(name);
    return;
  }
  setCookie(name, JSON.stringify(value));
}

export function readCookieJson<T>(name: string): T | null {
  const raw = getCookie(name);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    removeCookie(name);
    return null;
  }
}

/**
 * 大数据（行程含 POI）：localStorage + expiresAt，TTL 与 Cookie 一致 3 天。
 * Cookie 单条约 4KB，放不下完整 session。
 */
export function writeExpiringLocal<T>(key: string, value: T | null) {
  try {
    if (value == null) {
      localStorage.removeItem(key);
      removeCookie(`${key}-flag`);
      return;
    }
    const envelope: ExpiringEnvelope<T> = {
      expiresAt: Date.now() + PERSIST_TTL_MS,
      data: value,
    };
    localStorage.setItem(key, JSON.stringify(envelope));
    setCookie(`${key}-flag`, "1");
  } catch {
    // ignore quota / private mode
  }
}

export function readExpiringLocal<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ExpiringEnvelope<T> | T;
    if (
      parsed &&
      typeof parsed === "object" &&
      "expiresAt" in parsed &&
      "data" in parsed
    ) {
      if (Date.now() > (parsed as ExpiringEnvelope<T>).expiresAt) {
        localStorage.removeItem(key);
        removeCookie(`${key}-flag`);
        return null;
      }
      return (parsed as ExpiringEnvelope<T>).data;
    }
    // 旧版无过期信封：写入信封并沿用 3 天
    writeExpiringLocal(key, parsed as T);
    return parsed as T;
  } catch {
    return null;
  }
}
