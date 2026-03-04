import { apiRequest } from "../lib/api";

export type PalletItem = {
  id: number;
  serial: string;
  slot_index: number;
  added_by: number | null;
  added_at: string;
};

export type Pallet = {
  id: number;
  pallet_number: number;
  status: string;
  template_type: string | null;
  max_panels: number;
  customer_id: number | null;
  created_by: number | null;
  completed_by: number | null;
  created_at: string;
  completed_at: string | null;
  deleted_at: string | null;
  item_count: number;
  items: PalletItem[];
};

type PalletListResponse = {
  total: number;
  pallets: Pallet[];
};

export async function listPallets(token: string, status = "active") {
  const query = new URLSearchParams({ status, limit: "50", offset: "0" }).toString();
  return apiRequest<PalletListResponse>(`/pallets?${query}`, "GET", token);
}

export async function searchPallets(
  token: string,
  params: {
    status?: string;
    customer_id?: number;
    created_from?: string;
    created_to?: string;
    completed_from?: string;
    completed_to?: string;
    limit?: number;
    offset?: number;
  } = {},
) {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (typeof params.customer_id === "number") query.set("customer_id", String(params.customer_id));
  if (params.created_from) query.set("created_from", params.created_from);
  if (params.created_to) query.set("created_to", params.created_to);
  if (params.completed_from) query.set("completed_from", params.completed_from);
  if (params.completed_to) query.set("completed_to", params.completed_to);
  query.set("limit", String(params.limit ?? 50));
  query.set("offset", String(params.offset ?? 0));

  return apiRequest<PalletListResponse>(`/pallets?${query.toString()}`, "GET", token);
}

export async function createPallet(token: string, payload: { max_panels: number; template_type?: string }) {
  return apiRequest<Pallet>("/pallets", "POST", token, payload);
}

export async function createExport(token: string, payload: { pallet_id: number; template_type: string }) {
  return apiRequest<{ id: number }>("/exports", "POST", token, payload);
}

export async function addPalletItem(token: string, palletId: number, serial: string) {
  return apiRequest<Pallet>(`/pallets/${palletId}/items`, "POST", token, { serial });
}

export async function removePalletItem(token: string, palletId: number, itemId: number) {
  return apiRequest<Pallet>(`/pallets/${palletId}/items/${itemId}`, "DELETE", token);
}

export async function completePallet(token: string, palletId: number) {
  return apiRequest<Pallet>(`/pallets/${palletId}/complete`, "POST", token);
}

export async function getPallet(token: string, palletId: number) {
  return apiRequest<Pallet>(`/pallets/${palletId}`, "GET", token);
}

export async function deletePallet(token: string, palletId: number) {
  return apiRequest<undefined>(`/pallets/${palletId}`, "DELETE", token);
}
