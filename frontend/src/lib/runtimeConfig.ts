const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";
const SETTINGS_KEY = "pm2_runtime_settings";

export type RuntimeSettings = {
  apiBaseUrl: string;
};

function normalizeUrl(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

function getDefaultSettings(): RuntimeSettings {
  const envValue = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? DEFAULT_API_BASE_URL;
  return {
    apiBaseUrl: normalizeUrl(envValue),
  };
}

export function loadRuntimeSettings(): RuntimeSettings {
  const defaults = getDefaultSettings();
  const raw = localStorage.getItem(SETTINGS_KEY);
  if (!raw) {
    return defaults;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<RuntimeSettings>;
    const apiBaseUrl = normalizeUrl(parsed.apiBaseUrl ?? defaults.apiBaseUrl);
    if (!apiBaseUrl) {
      return defaults;
    }
    return { apiBaseUrl };
  } catch {
    return defaults;
  }
}

export function saveRuntimeSettings(next: RuntimeSettings): RuntimeSettings {
  const normalized = {
    apiBaseUrl: normalizeUrl(next.apiBaseUrl),
  };
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(normalized));
  return normalized;
}

