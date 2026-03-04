export type SyncState = {
  syncing: boolean;
  last_sync_at: string | null;
  failed_count: number;
  needs_review_count: number;
  pending_count: number;
};

const SYNC_STATE_KEY = "pm2_sync_state";
export const SYNC_STATE_EVENT = "pm2-sync-state-changed";

const DEFAULT_SYNC_STATE: SyncState = {
  syncing: false,
  last_sync_at: null,
  failed_count: 0,
  needs_review_count: 0,
  pending_count: 0,
};

export function getSyncState(): SyncState {
  const raw = localStorage.getItem(SYNC_STATE_KEY);
  if (!raw) {
    return DEFAULT_SYNC_STATE;
  }
  try {
    const parsed = JSON.parse(raw) as Partial<SyncState>;
    return {
      syncing: parsed.syncing ?? false,
      last_sync_at: parsed.last_sync_at ?? null,
      failed_count: parsed.failed_count ?? 0,
      needs_review_count: parsed.needs_review_count ?? 0,
      pending_count: parsed.pending_count ?? 0,
    };
  } catch {
    return DEFAULT_SYNC_STATE;
  }
}

export function setSyncState(patch: Partial<SyncState>): SyncState {
  const current = getSyncState();
  const next: SyncState = { ...current, ...patch };
  localStorage.setItem(SYNC_STATE_KEY, JSON.stringify(next));
  window.dispatchEvent(new CustomEvent(SYNC_STATE_EVENT, { detail: next }));
  return next;
}

