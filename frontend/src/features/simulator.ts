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

const UPLOAD_TIMEOUT_MS = 12000;
const MAX_UPLOAD_ROUNDS = 3;
const RETRY_DELAY_MS = 1500;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
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
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function uploadSimulatorFile(file: File) {
  const candidates = getApiBaseCandidates();
  if (candidates.length === 0) {
    throw new Error("No API base URL configured for simulator import");
  }

  const endpointPath = "/simulator/imports/anonymous";
  let lastError: unknown = null;
  for (let round = 0; round < MAX_UPLOAD_ROUNDS; round += 1) {
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
        const detail = error instanceof Error ? error.message : String(error);
        lastError = new Error(
          `Simulator upload round ${round + 1}, attempt ${attempt + 1} to ${url} failed: ${detail}`
        );
      }
    }

    if (round < MAX_UPLOAD_ROUNDS - 1) {
      await sleep(RETRY_DELAY_MS);
    }
  }

  if (lastError instanceof Error) {
    throw new Error(
      `${lastError.message}. The local backend may still be starting. ` +
        "Wait a few seconds, confirm Settings > Server Settings shows local backend healthy, and retry."
    );
  }
  throw new Error("Simulator import upload failed");
}

export async function getImportBatch(token: string, batchId: number) {
  return apiRequest<SimImportBatch>(`/simulator/imports/${batchId}`, "GET", token);
}
