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

export async function listPalletsForCustomer(
  token: string,
  customerId: number,
  options?: { includeDeleted?: boolean; status?: string | null }
) {
  const params = new URLSearchParams({
    customer_id: String(customerId),
    limit: "50",
    offset: "0",
  });
  if (options?.status) {
    params.set("status", options.status);
  }
  if (options?.includeDeleted) {
    params.set("include_deleted", "true");
  }
  return apiRequest<PalletListResponse>(`/pallets?${params.toString()}`, "GET", token);
}

export async function createPallet(
  token: string,
  payload: { max_panels: number; template_type?: string; customer_id?: number },
  clientOperationId?: string
) {
  return apiRequest<Pallet>(
    "/pallets",
    "POST",
    token,
    payload,
    clientOperationId ? { "X-Client-Operation-Id": clientOperationId } : undefined
  );
}

export async function createExport(token: string, payload: { pallet_id: number; template_type: string }) {
  return apiRequest<{ id: number }>("/exports", "POST", token, payload);
}

export async function addPalletItem(
  token: string,
  palletId: number,
  serial: string,
  clientOperationId?: string
) {
  return apiRequest<Pallet>(
    `/pallets/${palletId}/items`,
    "POST",
    token,
    { serial },
    clientOperationId ? { "X-Client-Operation-Id": clientOperationId } : undefined
  );
}

export async function removePalletItem(
  token: string,
  palletId: number,
  itemId: number,
  clientOperationId?: string
) {
  return apiRequest<Pallet>(
    `/pallets/${palletId}/items/${itemId}`,
    "DELETE",
    token,
    undefined,
    clientOperationId ? { "X-Client-Operation-Id": clientOperationId } : undefined
  );
}

export async function completePallet(token: string, palletId: number, clientOperationId?: string) {
  return apiRequest<Pallet>(
    `/pallets/${palletId}/complete`,
    "POST",
    token,
    undefined,
    clientOperationId ? { "X-Client-Operation-Id": clientOperationId } : undefined
  );
}

export async function getPallet(token: string, palletId: number) {
  return apiRequest<Pallet>(`/pallets/${palletId}`, "GET", token);
}

export async function deletePallet(token: string, palletId: number) {
  return apiRequest<void>(`/pallets/${palletId}`, "DELETE", token);
}
