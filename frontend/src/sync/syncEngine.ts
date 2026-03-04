import { listOutboxOperations } from "./outbox";

let onlineListenerRegistered = false;

export function getPendingSyncCount(): number {
  return listOutboxOperations().length;
}

// Scaffold for Sprint B/C: this will replay queued local ops to the backend.
export function startSyncEngine(): void {
  if (onlineListenerRegistered) {
    return;
  }
  onlineListenerRegistered = true;
  window.addEventListener("online", () => {
    // Placeholder: real replay logic lands in next step.
    // eslint-disable-next-line no-console
    console.info("Network restored. Pending queued operations:", getPendingSyncCount());
  });
}

