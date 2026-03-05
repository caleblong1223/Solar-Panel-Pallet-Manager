const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";
const SETTINGS_KEY = "pm2_runtime_settings";

export type RuntimeSettings = {
  primaryApiBaseUrl: string;
  fallbackApiBaseUrl: string;
  apiBaseUrl: string;
};

function normalizeUrl(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

function getDefaultSettings(): RuntimeSettings {
  const envValue = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? DEFAULT_API_BASE_URL;
  const normalized = normalizeUrl(envValue);
  return {
    primaryApiBaseUrl: normalized,
    fallbackApiBaseUrl: "",
    apiBaseUrl: normalized,
  };
}

export function loadRuntimeSettings(): RuntimeSettings {
  const defaults = getDefaultSettings();
  const raw = localStorage.getItem(SETTINGS_KEY);
  if (!raw) {
    return defaults;
  }
  try {
    const parsed = JSON.parse(raw) as Partial<RuntimeSettings> & { apiBaseUrl?: string };
    const primary = normalizeUrl(parsed.primaryApiBaseUrl ?? parsed.apiBaseUrl ?? defaults.primaryApiBaseUrl);
    const fallback = normalizeUrl(parsed.fallbackApiBaseUrl ?? "");
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
  const primary = normalizeUrl(next.primaryApiBaseUrl || next.apiBaseUrl);
  const fallback = normalizeUrl(next.fallbackApiBaseUrl ?? "");
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
  const candidates = [settings.primaryApiBaseUrl, settings.fallbackApiBaseUrl].filter(Boolean);
  return [...new Set(candidates)];
}
