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

export async function uploadSimulatorFile(file: File) {
  const candidates = getApiBaseCandidates();
  if (candidates.length === 0) {
    throw new Error("No API base URL configured for simulator import");
  }

  const endpointPath = "/simulator/imports/anonymous";
  let lastError: unknown = null;
  for (let attempt = 0; attempt < candidates.length; attempt += 1) {
    const baseUrl = candidates[attempt];
    const url = `${baseUrl}${endpointPath}`;
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(url, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const text = await response.text();
        const statusMessage = text || response.statusText || `status ${response.status}`;
      throw new Error(`Upload failed (${statusMessage}) at ${url}`);
    }
    return (await response.json()) as SimImportBatch;
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    lastError = new Error(`Simulator upload attempt ${attempt + 1} to ${url} failed: ${detail}`);
    if (attempt === candidates.length - 1) {
      break;
    }
      continue;
    }
  }

  if (lastError instanceof Error) {
    throw lastError;
  }
  throw new Error("Simulator import upload failed");
}

export async function getImportBatch(token: string, batchId: number) {
  return apiRequest<SimImportBatch>(`/simulator/imports/${batchId}`, "GET", token);
}
