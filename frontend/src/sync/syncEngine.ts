import {
  listOutboxOperations,
  markOperationNeedsReview,
  removeOutboxOperation,
  type OutboxOperation,
  updateOutboxOperation,
} from "./outbox";
import { ApiError } from "../lib/api";
import { resolvePalletId } from "./idMap";
import { repoApplyPalletIdMapping } from "../features/palletRepo";
import {
  addPalletItem,
  completePallet,
  createPallet,
  getPallet,
  removePalletItem,
} from "../features/pallets";
import { upsertLocalPallet } from "../features/localPalletStore";
import { setSyncState } from "./syncState";

let onlineListenerRegistered = false;
let syncInFlight = false;

export function getPendingSyncCount(): number {
  return listOutboxOperations().length;
}

function getAccessToken(): string | null {
  return localStorage.getItem("pm2_access_token");
}

function isRetryReady(operation: OutboxOperation): boolean {
  if (!operation.next_retry_at) {
    return true;
  }
  return new Date(operation.next_retry_at).getTime() <= Date.now();
}

function calcNextRetry(attemptCount: number): string {
  const backoffMs = Math.min(60_000, 1_000 * Math.max(1, attemptCount));
  return new Date(Date.now() + backoffMs).toISOString();
}

function isHardConflict(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 409 || error.status === 422);
}

function refreshSyncCounts(): void {
  const operations = listOutboxOperations();
  const needsReview = operations.filter((operation) => operation.state === "needs_review");
  const failed = operations.filter((operation) => operation.state === "pending" && operation.last_error);
  setSyncState({
    pending_count: operations.length,
    failed_count: failed.length,
    needs_review_count: needsReview.length,
  });
}

async function replayOperation(token: string, operation: OutboxOperation): Promise<void> {
  switch (operation.op_type) {
    case "pallet.create": {
      const localPalletId = Number(operation.payload.local_pallet_id);
      const maxPanels = Number(operation.payload.max_panels);
      const templateTypeRaw = operation.payload.template_type;
      const templateType =
        typeof templateTypeRaw === "string" && templateTypeRaw.trim().length > 0 ? templateTypeRaw : undefined;
      const created = await createPallet(
        token,
        { max_panels: maxPanels, template_type: templateType },
        operation.op_id
      );
      repoApplyPalletIdMapping(localPalletId, created);
      upsertLocalPallet(created);
      return;
    }
    case "pallet.item_add": {
      const palletId = resolvePalletId(Number(operation.payload.pallet_id));
      const serial = String(operation.payload.serial ?? "").trim().toUpperCase();
      if (!serial) {
        throw new Error("Missing serial for pallet.item_add");
      }
      if (palletId <= 0) {
        throw new Error("Pallet ID not resolved for pallet.item_add");
      }
      const updated = await addPalletItem(token, palletId, serial, operation.op_id);
      upsertLocalPallet(updated);
      return;
    }
    case "pallet.item_remove": {
      const palletId = resolvePalletId(Number(operation.payload.pallet_id));
      if (palletId <= 0) {
        throw new Error("Pallet ID not resolved for pallet.item_remove");
      }
      const rawItemId = Number(operation.payload.item_id);
      let itemId = rawItemId;
      if (itemId <= 0) {
        const serial = String(operation.payload.serial ?? "").trim().toUpperCase();
        if (!serial) {
          throw new Error("Missing serial fallback for pallet.item_remove");
        }
        const pallet = await getPallet(token, palletId);
        const matched = pallet.items.find((item) => item.serial === serial) ?? null;
        if (!matched) {
          // Already removed remotely; treat as success.
          return;
        }
        itemId = matched.id;
      }
      const updated = await removePalletItem(token, palletId, itemId, operation.op_id);
      upsertLocalPallet(updated);
      return;
    }
    case "pallet.complete": {
      const palletId = resolvePalletId(Number(operation.payload.pallet_id));
      if (palletId <= 0) {
        throw new Error("Pallet ID not resolved for pallet.complete");
      }
      const updated = await completePallet(token, palletId, operation.op_id);
      upsertLocalPallet(updated);
      return;
    }
    default:
      throw new Error(`Unsupported outbox operation: ${operation.op_type}`);
  }
}

async function syncOutbox(): Promise<void> {
  if (syncInFlight) {
    return;
  }
  syncInFlight = true;
  setSyncState({ syncing: true });
  try {
    const token = getAccessToken();
    if (!token) {
      return;
    }
    const operations = listOutboxOperations();
    for (const operation of operations) {
      if (operation.state === "needs_review") {
        continue;
      }
      if (!isRetryReady(operation)) {
        continue;
      }
      try {
        await replayOperation(token, operation);
        removeOutboxOperation(operation.op_id);
        refreshSyncCounts();
      } catch (error) {
        const message = error instanceof Error ? error.message : "Sync replay failed";
        const errorCode = error instanceof ApiError ? error.errorCode : null;
        if (isHardConflict(error)) {
          markOperationNeedsReview(operation.op_id, message, errorCode);
          refreshSyncCounts();
          continue;
        }
        const nextAttempt = operation.attempt_count + 1;
        updateOutboxOperation(operation.op_id, {
          attempt_count: nextAttempt,
          last_error: message,
          last_error_code: errorCode,
          next_retry_at: calcNextRetry(nextAttempt),
        });
        refreshSyncCounts();
      }
    }
    setSyncState({ last_sync_at: new Date().toISOString() });
  } finally {
    syncInFlight = false;
    refreshSyncCounts();
    setSyncState({ syncing: false });
  }
}

export function startSyncEngine(): void {
  if (onlineListenerRegistered) {
    return;
  }
  onlineListenerRegistered = true;
  window.addEventListener("online", () => void syncOutbox());
  window.setInterval(() => void syncOutbox(), 10_000);
  void syncOutbox();
}

export function triggerSyncNow(): Promise<void> {
  return syncOutbox();
}

export function discardOutboxOperation(opId: string): void {
  removeOutboxOperation(opId);
  refreshSyncCounts();
}

export function retryOutboxOperation(opId: string): void {
  updateOutboxOperation(opId, {
    state: "pending",
    next_retry_at: null,
    last_error: null,
    last_error_code: null,
  });
  refreshSyncCounts();
  void syncOutbox();
}
