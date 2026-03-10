import { invoke } from "@tauri-apps/api/core";
import { apiRequest } from "../lib/api";
import { getApiBaseCandidates } from "../lib/runtimeConfig";

export type SimImportBatch = {
  id: number;
  source_filename: string;
  source_object_key: string | null;
  source_checksum: string | null;
  status: string;
  rows_total: number | null;
  rows_imported: number | null;
  rows_rejected: number | null;
  error_summary: string | null;
  imported_by: number | null;
  created_at: string;
  completed_at: string | null;
};

const UPLOAD_TIMEOUT_MS = 300000;
const HEALTH_TIMEOUT_MS = 2500;
const LOCAL_BACKEND_WARMUP_MS = 20000;
const LOCAL_BACKEND_POLL_MS = 1000;

function extractErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function isNetworkStyleFailure(message: string): boolean {
  const normalized = message.toLowerCase();
  return normalized.includes("failed to fetch") || normalized.includes("networkerror") || normalized.includes("abort");
}

async function uploadWithTimeout(url: string, formData: FormData): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS);
  try {
    return await fetch(url, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(`Upload timed out after ${UPLOAD_TIMEOUT_MS}ms`);
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function normalizeSimulatorBaseUrl(baseUrl: string): string {
  return baseUrl.replace("localhost:8010", "127.0.0.1:8010");
}

async function isBackendReachable(baseUrl: string): Promise<boolean> {
  const healthUrl = baseUrl.replace(/\/api\/v1\/?$/, "") + "/health/live";
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
  try {
    const response = await fetch(healthUrl, { method: "GET", signal: controller.signal });
    return response.ok;
  } catch {
    return false;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function isLocalBackendBase(baseUrl: string): boolean {
  return baseUrl.includes("127.0.0.1:8010") || baseUrl.includes("localhost:8010");
}

async function waitForLocalBackend(baseUrl: string): Promise<boolean> {
  const deadline = Date.now() + LOCAL_BACKEND_WARMUP_MS;
  while (Date.now() < deadline) {
    if (await isBackendReachable(baseUrl)) {
      return true;
    }
    await new Promise((resolve) => window.setTimeout(resolve, LOCAL_BACKEND_POLL_MS));
  }
  return false;
}

async function ensureLocalBackend(candidates: string[]): Promise<void> {
  const hasLocal = candidates.some((base) => isLocalBackendBase(base));
  if (!hasLocal) {
    return;
  }
  try {
    await invoke<boolean>("ensure_local_backend");
  } catch {
    // Non-tauri or command unavailable; fallback to existing warm-up checks.
  }
}

export async function uploadSimulatorFile(file: File) {
  const candidates = [...new Set(getApiBaseCandidates().map(normalizeSimulatorBaseUrl))];
  if (candidates.length === 0) {
    throw new Error("No API base URL configured for simulator import");
  }
  await ensureLocalBackend(candidates);

  const endpointPath = "/simulator/imports/anonymous";
  let lastError: unknown = null;
  for (let attempt = 0; attempt < candidates.length; attempt += 1) {
    const baseUrl = candidates[attempt];
    const url = `${baseUrl}${endpointPath}`;
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await uploadWithTimeout(url, formData);
      if (!response.ok) {
        const text = await response.text();
        const statusMessage = text || response.statusText || `status ${response.status}`;
        throw new Error(`Upload failed (${statusMessage}) at ${url}`);
      }
      return (await response.json()) as SimImportBatch;
    } catch (error) {
      const detail = extractErrorMessage(error);
      const networkFailure = isNetworkStyleFailure(detail);

      if (isLocalBackendBase(baseUrl) && networkFailure) {
        await ensureLocalBackend([baseUrl]);
        const ready = await waitForLocalBackend(baseUrl);
        if (ready) {
          const retryFormData = new FormData();
          retryFormData.append("file", file);
          try {
            const retryResponse = await uploadWithTimeout(url, retryFormData);
            if (!retryResponse.ok) {
              const text = await retryResponse.text();
              const statusMessage = text || retryResponse.statusText || `status ${retryResponse.status}`;
              throw new Error(`Upload failed (${statusMessage}) at ${url}`);
            }
            return (await retryResponse.json()) as SimImportBatch;
          } catch (retryError) {
            const retryDetail = extractErrorMessage(retryError);
            lastError = new Error(`Simulator upload retry to ${url} failed: ${retryDetail}`);
            continue;
          }
        }
      }

      if (!networkFailure) {
        throw new Error(
          `Simulator upload to ${url} failed: ${detail}. The request reached the backend, so local fallback was not used.`
        );
      }

      lastError = new Error(`Simulator upload attempt ${attempt + 1} to ${url} failed: ${detail}`);
    }
  }

  if (lastError instanceof Error) {
    throw new Error(
      `${lastError.message}. If import is still running in the backend, wait for completion before retrying.`
    );
  }
  throw new Error("Simulator import upload failed");
}

export async function getImportBatch(token: string, batchId: number) {
  return apiRequest<SimImportBatch>(`/simulator/imports/${batchId}`, "GET", token);
}
