import {
  addPalletItem as apiAddPalletItem,
  completePallet as apiCompletePallet,
  createPallet as apiCreatePallet,
  getPallet as apiGetPallet,
  listPallets as apiListPallets,
  removePalletItem as apiRemovePalletItem,
  type Pallet,
  type PalletItem,
} from "./pallets";
import {
  findLocalPalletById,
  getAllLocalPallets,
  listLocalPalletsByStatus,
  replaceAllLocalPallets,
  upsertLocalPallet,
} from "./localPalletStore";
import { enqueueOutboxOperation } from "../sync/outbox";

type CreatePalletPayload = { max_panels: number; template_type?: string };

type ListPalletsResponse = {
  total: number;
  pallets: Pallet[];
};

function nowIso(): string {
  return new Date().toISOString();
}

function nextLocalId(pallets: Pallet[]): number {
  const minId = pallets.reduce((acc, pallet) => (pallet.id < acc ? pallet.id : acc), 0);
  return minId <= 0 ? minId - 1 : -1;
}

function nextPalletNumber(pallets: Pallet[]): number {
  return pallets.reduce((acc, pallet) => Math.max(acc, pallet.pallet_number), 0) + 1;
}

function nextItemId(pallet: Pallet): number {
  const minId = pallet.items.reduce((acc, item) => (item.id < acc ? item.id : acc), 0);
  return minId <= 0 ? minId - 1 : -1;
}

function nextSlotIndex(pallet: Pallet): number {
  const taken = new Set(pallet.items.map((item) => item.slot_index));
  let slot = 1;
  while (taken.has(slot)) {
    slot += 1;
  }
  return slot;
}

function normalizeSerial(serial: string): string {
  return serial.trim().toUpperCase();
}

export async function repoListPallets(token: string | null, status = "active"): Promise<ListPalletsResponse> {
  if (token) {
    try {
      const response = await apiListPallets(token, status);
      replaceAllLocalPallets(response.pallets);
      return response;
    } catch {
      // Fall back to local cache.
    }
  }

  const pallets = listLocalPalletsByStatus(status);
  return { total: pallets.length, pallets };
}

export async function repoGetPallet(token: string | null, palletId: number): Promise<Pallet> {
  if (token && palletId > 0) {
    try {
      const pallet = await apiGetPallet(token, palletId);
      upsertLocalPallet(pallet);
      return pallet;
    } catch {
      // Fall through to local.
    }
  }

  const local = findLocalPalletById(palletId);
  if (!local) {
    throw new Error("Pallet not found");
  }
  return local;
}

export async function repoCreatePallet(token: string | null, payload: CreatePalletPayload): Promise<Pallet> {
  if (token) {
    try {
      const created = await apiCreatePallet(token, payload);
      upsertLocalPallet(created);
      return created;
    } catch {
      // Fall back to local and queue op.
    }
  }

  const all = getAllLocalPallets();
  const created: Pallet = {
    id: nextLocalId(all),
    pallet_number: nextPalletNumber(all),
    status: "active",
    template_type: payload.template_type ?? null,
    max_panels: payload.max_panels,
    customer_id: null,
    created_by: null,
    completed_by: null,
    created_at: nowIso(),
    completed_at: null,
    deleted_at: null,
    item_count: 0,
    items: [],
  };
  upsertLocalPallet(created);
  enqueueOutboxOperation("pallet.create", payload as Record<string, unknown>);
  return created;
}

export async function repoAddPalletItem(token: string | null, palletId: number, serialInput: string): Promise<Pallet> {
  const serial = normalizeSerial(serialInput);
  if (!serial) {
    throw new Error("Serial cannot be empty");
  }

  if (token && palletId > 0) {
    try {
      const updated = await apiAddPalletItem(token, palletId, serial);
      upsertLocalPallet(updated);
      return updated;
    } catch {
      // Fall back to local and queue op.
    }
  }

  const local = findLocalPalletById(palletId);
  if (!local) {
    throw new Error("Pallet not found");
  }
  if (local.status !== "active") {
    throw new Error("Pallet is not active");
  }
  if (local.item_count >= local.max_panels) {
    throw new Error("Pallet is at capacity");
  }
  if (local.items.some((item) => item.serial === serial)) {
    throw new Error("Serial already on pallet");
  }

  const newItem: PalletItem = {
    id: nextItemId(local),
    serial,
    slot_index: nextSlotIndex(local),
    added_by: null,
    added_at: nowIso(),
  };
  const updated: Pallet = {
    ...local,
    item_count: local.item_count + 1,
    items: [...local.items, newItem],
  };
  upsertLocalPallet(updated);
  enqueueOutboxOperation("pallet.item_add", { pallet_id: palletId, serial });
  return updated;
}

export async function repoRemovePalletItem(token: string | null, palletId: number, itemId: number): Promise<Pallet> {
  if (token && palletId > 0 && itemId > 0) {
    try {
      const updated = await apiRemovePalletItem(token, palletId, itemId);
      upsertLocalPallet(updated);
      return updated;
    } catch {
      // Fall back to local and queue op.
    }
  }

  const local = findLocalPalletById(palletId);
  if (!local) {
    throw new Error("Pallet not found");
  }
  const remainingItems = local.items.filter((item) => item.id !== itemId);
  if (remainingItems.length === local.items.length) {
    throw new Error("Pallet item not found");
  }
  const updated: Pallet = {
    ...local,
    item_count: remainingItems.length,
    items: remainingItems,
  };
  upsertLocalPallet(updated);
  enqueueOutboxOperation("pallet.item_remove", { pallet_id: palletId, item_id: itemId });
  return updated;
}

export async function repoCompletePallet(token: string | null, palletId: number): Promise<Pallet> {
  if (token && palletId > 0) {
    try {
      const updated = await apiCompletePallet(token, palletId);
      upsertLocalPallet(updated);
      return updated;
    } catch {
      // Fall back to local and queue op.
    }
  }

  const local = findLocalPalletById(palletId);
  if (!local) {
    throw new Error("Pallet not found");
  }
  if (local.item_count !== local.max_panels) {
    throw new Error("Pallet must be full before completion");
  }
  const updated: Pallet = {
    ...local,
    status: "completed",
    completed_at: nowIso(),
    completed_by: null,
  };
  upsertLocalPallet(updated);
  enqueueOutboxOperation("pallet.complete", { pallet_id: palletId });
  return updated;
}

