import { apiRequest } from "../lib/api";
import { loadRuntimeSettings } from "../lib/runtimeConfig";

type HealthResponse = {
  status: string;
};

function normalizeUrl(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

export async function testServerConnection(apiBaseUrl?: string): Promise<{ ok: boolean; message: string }> {
  const targetUrl = normalizeUrl(apiBaseUrl ?? loadRuntimeSettings().apiBaseUrl);
  if (!targetUrl) {
    return { ok: false, message: "API base URL is required." };
  }

  try {
    const response = await apiRequest<HealthResponse>(`${targetUrl}/health/live`, "GET");
    if (response.status !== "ok") {
      return { ok: false, message: "Server responded but status was not OK." };
    }
    return { ok: true, message: "Connection successful." };
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown error";
    return { ok: false, message: `Connection failed: ${detail}` };
  }
}

