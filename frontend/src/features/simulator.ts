import { API_BASE_URL } from "../lib/api";
import { apiRequest } from "../lib/api";

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

export async function uploadSimulatorFile(token: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/simulator/imports`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Upload failed with status ${response.status}`);
  }

  return (await response.json()) as SimImportBatch;
}

export async function getImportBatch(token: string, batchId: number) {
  return apiRequest<SimImportBatch>(`/simulator/imports/${batchId}`, "GET", token);
}
