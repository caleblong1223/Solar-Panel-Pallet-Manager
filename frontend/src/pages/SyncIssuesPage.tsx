import { useEffect, useMemo, useState } from "react";
import AppFrame from "../components/layout/AppFrame";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import {
  discardOutboxOperation,
  retryOutboxOperation,
  triggerSyncNow,
} from "../sync/syncEngine";
import { listOutboxOperations, type OutboxOperation } from "../sync/outbox";

function getGuidance(errorCode: string | null): string {
  switch (errorCode) {
    case "SERIAL_ALREADY_ASSIGNED_ELSEWHERE":
      return "Serial already exists on another pallet. Remove from this queue item or correct source scan.";
    case "SERIAL_ALREADY_ON_PALLET":
      return "Serial is already on the target pallet. This operation is likely duplicate.";
    case "PALLET_AT_CAPACITY":
    case "PALLET_NOT_FULL":
      return "Pallet capacity state changed. Open Builder and reconcile pallet contents.";
    case "PALLET_NOT_ACTIVE":
      return "Pallet is no longer active. Verify lifecycle state before retrying.";
    case "PALLET_NOT_FOUND":
      return "Target pallet no longer exists on server. Discard or recreate locally.";
    default:
      return "Review operation details, then retry or discard.";
  }
}

export default function SyncIssuesPage() {
  const [operations, setOperations] = useState<OutboxOperation[]>([]);
  const [isSyncingNow, setIsSyncingNow] = useState(false);

  const refresh = () => {
    setOperations(listOutboxOperations());
  };

  useEffect(() => {
    refresh();
    const id = window.setInterval(refresh, 2000);
    return () => window.clearInterval(id);
  }, []);

  const needsReview = useMemo(
    () => operations.filter((operation) => operation.state === "needs_review"),
    [operations]
  );
  const failedPending = useMemo(
    () => operations.filter((operation) => operation.state === "pending" && Boolean(operation.last_error)),
    [operations]
  );

  const handleSyncNow = async () => {
    setIsSyncingNow(true);
    try {
      await triggerSyncNow();
    } finally {
      setIsSyncingNow(false);
      refresh();
    }
  };

  return (
    <AppFrame title="Sync Issues">
      <section className="card-grid">
        <Card title="Actions">
          <p>Use this page to resolve queued operations that failed sync.</p>
          <Button variant="secondary" onClick={() => void handleSyncNow()} disabled={isSyncingNow}>
            {isSyncingNow ? "Syncing..." : "Retry Sync Now"}
          </Button>
        </Card>
      </section>

      <section className="card-grid">
        <Card title={`Needs Review (${needsReview.length})`}>
          {needsReview.length === 0 ? (
            <p>No operations need review.</p>
          ) : (
            <ul className="flat-list">
              {needsReview.map((operation) => (
                <li key={operation.op_id}>
                  <span>
                    {operation.op_type} ({operation.op_id.slice(0, 8)})<br />
                    <small>{operation.last_error ?? "Conflict requires operator review."}</small>
                    <br />
                    <small>{getGuidance(operation.last_error_code)}</small>
                  </span>
                  <span className="sync-issue-actions">
                    <Button variant="secondary" onClick={() => { retryOutboxOperation(operation.op_id); refresh(); }}>
                      Retry
                    </Button>
                    <Button variant="danger" onClick={() => { discardOutboxOperation(operation.op_id); refresh(); }}>
                      Discard
                    </Button>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title={`Pending Errors (${failedPending.length})`}>
          {failedPending.length === 0 ? (
            <p>No retryable failures.</p>
          ) : (
            <ul className="flat-list">
              {failedPending.map((operation) => (
                <li key={operation.op_id}>
                  <span>
                    {operation.op_type} ({operation.op_id.slice(0, 8)})<br />
                    <small>{operation.last_error ?? "Unknown sync error"}</small>
                  </span>
                  <span className="sync-issue-actions">
                    <Button variant="secondary" onClick={() => { retryOutboxOperation(operation.op_id); refresh(); }}>
                      Retry
                    </Button>
                    <Button variant="danger" onClick={() => { discardOutboxOperation(operation.op_id); refresh(); }}>
                      Discard
                    </Button>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </section>
    </AppFrame>
  );
}
