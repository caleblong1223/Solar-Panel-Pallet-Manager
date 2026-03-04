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
  attempt_count: number;
  last_error: string | null;
  next_retry_at: string | null;
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
    attempt_count: 0,
    last_error: null,
    next_retry_at: null,
  };
  const existing = listOutboxOperations();
  const next = [...existing, operation];
  localStorage.setItem(OUTBOX_KEY, JSON.stringify(next));
  return operation;
}

export function removeOutboxOperation(opId: string): void {
  const next = listOutboxOperations().filter((operation) => operation.op_id !== opId);
  localStorage.setItem(OUTBOX_KEY, JSON.stringify(next));
}

export function updateOutboxOperation(opId: string, patch: Partial<OutboxOperation>): void {
  const next = listOutboxOperations().map((operation) =>
    operation.op_id === opId ? { ...operation, ...patch } : operation
  );
  localStorage.setItem(OUTBOX_KEY, JSON.stringify(next));
}

export function clearOutbox(): void {
  localStorage.removeItem(OUTBOX_KEY);
}
