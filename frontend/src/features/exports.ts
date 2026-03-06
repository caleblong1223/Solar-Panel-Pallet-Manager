import { apiRequest } from "../lib/api";
import { loadRuntimeSettings } from "../lib/runtimeConfig";

export type ExportRecord = {
  id: number;
  pallet_id: number;
  template_type: string;
  object_key: string;
  file_name: string;
  mime_type: string;
  size_bytes: number;
  checksum_sha256: string | null;
  created_by: number | null;
  created_at: string;
};

type ExportListResponse = {
  total: number;
  exports: ExportRecord[];
};

type ExportDownloadUrlResponse = {
  export_id: number;
  format?: string;
  file_name?: string;
  object_key: string;
  download_url: string;
  expires_in_seconds: number;
};

export async function listExportsByPallet(token: string, palletId: number) {
  return apiRequest<ExportListResponse>(`/exports?pallet_id=${palletId}&limit=50&offset=0`, "GET", token);
}

export async function listExports(token: string, options?: { palletId?: number; templateType?: string; createdFrom?: string; createdTo?: string; limit?: number; offset?: number }) {
  const params = new URLSearchParams();
  if (options?.palletId != null) {
    params.set("pallet_id", String(options.palletId));
  }
  if (options?.templateType) {
    params.set("template_type", options.templateType);
  }
  if (options?.createdFrom) {
    params.set("created_from", options.createdFrom);
  }
  if (options?.createdTo) {
    params.set("created_to", options.createdTo);
  }
  params.set("limit", String(options?.limit ?? 50));
  params.set("offset", String(options?.offset ?? 0));
  const query = params.toString();
  return apiRequest<ExportListResponse>(`/exports?${query}`, "GET", token);
}

export async function getExportDownloadUrl(
  token: string,
  exportId: number,
  format: "pdf" | "xlsx" = "pdf"
) {
  const query = new URLSearchParams({ format }).toString();
  return apiRequest<ExportDownloadUrlResponse>(
    `/exports/${exportId}/download-url?${query}`,
    "GET",
    token
  );
}

export async function downloadExportWorkbook(token: string, exportId: number) {
  const response = await getExportDownloadUrl(token, exportId, "xlsx");
  const download = await fetch(response.download_url);
  if (!download.ok) {
    throw new Error(`Failed to download workbook (${download.status})`);
  }
  return await download.arrayBuffer();
}

export async function replaceExportWorkbook(
  token: string,
  exportId: number,
  workbookBlob: Blob,
  fileName: string
) {
  const { apiBaseUrl } = loadRuntimeSettings();
  const formData = new FormData();
  formData.append("file", workbookBlob, fileName);

  const response = await fetch(`${apiBaseUrl}/exports/${exportId}/replace`, {
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
  return (await response.json()) as ExportRecord;
}
