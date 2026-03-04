import { apiRequest } from "../lib/api";

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
  object_key: string;
  download_url: string;
  expires_in_seconds: number;
};

export async function listExportsByPallet(token: string, palletId: number) {
  return apiRequest<ExportListResponse>(`/exports?pallet_id=${palletId}&limit=50&offset=0`, "GET", token);
}

export async function getExportDownloadUrl(token: string, exportId: number) {
  return apiRequest<ExportDownloadUrlResponse>(`/exports/${exportId}/download-url`, "GET", token);
}
