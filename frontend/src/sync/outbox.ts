export type OutboxOperationType =
  | "pallet.create"
  | "pallet.item_add"
  | "pallet.item_remove"
  | "pallet.complete";

export type OutboxOperation = {
  op_id: string;
  op_type: OutboxOperationType;
  payload: Record<string, unknown>;
  created_at: string;
};

const OUTBOX_KEY = "pm2_sync_outbox";

function parseOutbox(raw: string | null): OutboxOperation[] {
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw) as OutboxOperation[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function listOutboxOperations(): OutboxOperation[] {
  return parseOutbox(localStorage.getItem(OUTBOX_KEY));
}

export function enqueueOutboxOperation(
  op_type: OutboxOperationType,
  payload: Record<string, unknown>
): OutboxOperation {
  const operation: OutboxOperation = {
    op_id: crypto.randomUUID(),
    op_type,
    payload,
    created_at: new Date().toISOString(),
  };
  const existing = listOutboxOperations();
  const next = [...existing, operation];
  localStorage.setItem(OUTBOX_KEY, JSON.stringify(next));
  return operation;
}

export function clearOutbox(): void {
  localStorage.removeItem(OUTBOX_KEY);
}

