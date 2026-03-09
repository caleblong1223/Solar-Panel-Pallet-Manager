const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1";
const LOOPBACK_API_BASE_URL = "http://localhost:8000/api/v1";
const SETTINGS_KEY = "pm2_runtime_settings";
const LOCK_TO_LOCAL_BACKEND = true;

export type RuntimeSettings = {
  primaryApiBaseUrl: string;
  fallbackApiBaseUrl: string;
  apiBaseUrl: string;
};

function normalizeUrl(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

function ensureApiV1Path(value: string): string {
  const normalized = normalizeUrl(value);
  if (!normalized) {
    return normalized;
  }
  // Accept either full API path or bare host base.
  if (normalized.endsWith("/api/v1")) {
    return normalized;
  }
  return `${normalized}/api/v1`;
}

function getDefaultSettings(): RuntimeSettings {
  const envValue = LOCK_TO_LOCAL_BACKEND
    ? DEFAULT_API_BASE_URL
    : (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? DEFAULT_API_BASE_URL;
  const normalized = ensureApiV1Path(envValue);
  return {
    primaryApiBaseUrl: normalized,
    fallbackApiBaseUrl: LOOPBACK_API_BASE_URL,
    apiBaseUrl: normalized,
  };
}

export function loadRuntimeSettings(): RuntimeSettings {
  const defaults = getDefaultSettings();
  if (LOCK_TO_LOCAL_BACKEND) {
    return defaults;
  }
  const raw = localStorage.getItem(SETTINGS_KEY);
  if (!raw) {
    return defaults;
  }
  try {
    const parsed = JSON.parse(raw) as Partial<RuntimeSettings> & { apiBaseUrl?: string };
    const primary = ensureApiV1Path(parsed.primaryApiBaseUrl ?? parsed.apiBaseUrl ?? defaults.primaryApiBaseUrl);
    const fallback = ensureApiV1Path(parsed.fallbackApiBaseUrl ?? "");
    return {
      primaryApiBaseUrl: primary,
      fallbackApiBaseUrl: fallback,
      // Keep apiBaseUrl for backward compatibility in existing call sites.
      apiBaseUrl: primary,
    };
  } catch {
    return defaults;
  }
}

export function saveRuntimeSettings(next: RuntimeSettings): RuntimeSettings {
  if (LOCK_TO_LOCAL_BACKEND) {
    const locked = getDefaultSettings();
    localStorage.removeItem(SETTINGS_KEY);
    return locked;
  }
  const primary = ensureApiV1Path(next.primaryApiBaseUrl || next.apiBaseUrl);
  const fallback = ensureApiV1Path(next.fallbackApiBaseUrl ?? "");
  const normalized = {
    primaryApiBaseUrl: primary,
    fallbackApiBaseUrl: fallback,
    apiBaseUrl: primary,
  };
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(normalized));
  return normalized;
}

export function getApiBaseCandidates(): string[] {
  const settings = loadRuntimeSettings();
  const candidates = [
    settings.primaryApiBaseUrl,
    settings.fallbackApiBaseUrl,
    DEFAULT_API_BASE_URL,
    LOOPBACK_API_BASE_URL,
  ].filter(Boolean);
  return [...new Set(candidates)];
}

export function isRuntimeSettingsLocked(): boolean {
  return LOCK_TO_LOCAL_BACKEND;
}
