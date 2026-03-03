import { apiRequest } from "../lib/api";

export type BarcodeSearchResult = {
  source: "pallet_item" | "sim_panel";
  serial: string;
  matched_exact: boolean;
  pallet_id?: number | null;
  pallet_number?: number | null;
  pallet_status?: string | null;
  slot_index?: number | null;
  customer_id?: number | null;
  sim_panel_id?: number | null;
  sim_batch_id?: number | null;
  sim_test_timestamp?: string | null;
  sim_panel_type?: string | null;
  sim_result?: string | null;
  created_at?: string | null;
};

type BarcodeSearchResponse = {
  query: string;
  exact: boolean;
  total: number;
  results: BarcodeSearchResult[];
};

export async function searchBarcodes(
  token: string,
  params: { q: string; exact?: boolean; limit?: number; offset?: number; sort?: string; order?: string }
) {
  const query = new URLSearchParams({
    q: params.q,
    exact: String(Boolean(params.exact)),
    limit: String(params.limit ?? 50),
    offset: String(params.offset ?? 0),
    sort: params.sort ?? "created_at",
    order: params.order ?? "desc",
  }).toString();

  return apiRequest<BarcodeSearchResponse>(`/barcodes/search?${query}`, "GET", token);
}
