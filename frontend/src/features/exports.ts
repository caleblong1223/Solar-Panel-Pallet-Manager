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
