import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import AppFrame from "../components/layout/AppFrame";
import { useToast } from "../components/notifications/ToastProvider";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import TextInput from "../components/ui/TextInput";
import { listOutboxOperations } from "../sync/outbox";
import {
  repoAddPalletItem,
  repoCompletePallet,
  repoCreatePallet,
  repoGetPallet,
  repoListPallets,
  repoRemovePalletItem,
} from "../features/palletRepo";
import { type Pallet } from "../features/pallets";

const PANEL_CAPACITY_OPTIONS = [25, 26, 30, 35] as const;
const TEMPLATE_OPTIONS = ["200WT", "220WT", "220M6", "330WT", "450WT", "450BT"] as const;

export default function LiveBuilderPage() {
  const { token } = useAuth();
  const { notify } = useToast();

  const [current, setCurrent] = useState<Pallet | null>(null);
  const [serial, setSerial] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [queuedOpsCount, setQueuedOpsCount] = useState(0);
  const [activePalletCount, setActivePalletCount] = useState(0);

  const [newMaxPanels, setNewMaxPanels] = useState<number>(25);
  const [newTemplate, setNewTemplate] = useState<(typeof TEMPLATE_OPTIONS)[number]>(TEMPLATE_OPTIONS[0]);

  const serialInputRef = useRef<HTMLInputElement | null>(null);

  const remaining = useMemo(() => {
    if (!current) {
      return 0;
    }
    return current.max_panels - current.item_count;
  }, [current]);

  const refreshActivePallets = async () => {
    const response = await repoListPallets(token, "active");
    const pallets = response.pallets.slice().sort((a, b) => b.pallet_number - a.pallet_number);
    setActivePalletCount(pallets.length);
    setQueuedOpsCount(listOutboxOperations().length);

    const currentStillActive = current ? pallets.find((pallet) => pallet.id === current.id) : null;
    const nextSelected = currentStillActive?.id ?? pallets[0]?.id ?? null;

    if (nextSelected) {
      const full = await repoGetPallet(token, nextSelected);
      setCurrent(full);
    } else {
      setCurrent(null);
    }
  };

  useEffect(() => {
    void refreshActivePallets();
  }, [token]);

  const handleCreatePallet = async (event: FormEvent) => {
    event.preventDefault();

    setIsBusy(true);
    try {
      const created = await repoCreatePallet(token, { max_panels: newMaxPanels, template_type: newTemplate });
      notify(`Created pallet #${created.pallet_number}`, "success");
      await refreshActivePallets();
      setCurrent(created);
      setSerial("");
      setQueuedOpsCount(listOutboxOperations().length);
      serialInputRef.current?.focus();
    } catch {
      notify("Failed to create pallet", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleAddSerial = async (event: FormEvent) => {
    event.preventDefault();
    if (!current) {
      notify("Create an active pallet first", "warning");
      return;
    }

    setIsBusy(true);
    try {
      const updated = await repoAddPalletItem(token, current.id, serial);
      setCurrent(updated);
      setSerial("");
      notify("Serial added", "success");
      setQueuedOpsCount(listOutboxOperations().length);
      serialInputRef.current?.focus();
    } catch {
      notify("Failed to add serial", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleRemoveItem = async (itemId: number) => {
    if (!current) {
      return;
    }

    setIsBusy(true);
    try {
      const updated = await repoRemovePalletItem(token, current.id, itemId);
      setCurrent(updated);
      notify("Serial removed", "success");
      setQueuedOpsCount(listOutboxOperations().length);
    } catch {
      notify("Failed to remove serial", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleComplete = async () => {
    if (!current) {
      return;
    }

    setIsBusy(true);
    try {
      const updated = await repoCompletePallet(token, current.id);
      notify(`Pallet #${updated.pallet_number} completed`, "success");
      await refreshActivePallets();
      setQueuedOpsCount(listOutboxOperations().length);
    } catch {
      notify("Failed to complete pallet", "error");
    } finally {
      setIsBusy(false);
    }
  };

  return (
    <AppFrame title="Live Builder">
      <section className="builder-grid">
        <Card title="Active pallet">
          {current ? (
            <div className="builder-meta">
              <p>
                <strong>Pallet:</strong> #{current.pallet_number}
              </p>
              <p>
                <strong>Status:</strong> {current.status}
              </p>
              <p>
                <strong>Template:</strong> {current.template_type ?? "-"}
              </p>
              <p>
                <strong>Capacity:</strong> {current.item_count}/{current.max_panels}
              </p>
              <p>
                <strong>Remaining:</strong> {remaining}
              </p>
              <p>
                <strong>Queued Ops:</strong> {queuedOpsCount}
              </p>
              {activePalletCount > 1 ? (
                <p>
                  <strong>Active Pallets:</strong> {activePalletCount} (using most recent)
                </p>
              ) : null}
            </div>
          ) : (
            <p>No active pallet. Create one to start scanning.</p>
          )}
        </Card>

        <Card title="Create pallet">
          <form className="builder-form" onSubmit={handleCreatePallet}>
            <label className="ui-input-label">
              <span>Panel count</span>
              <select
                className="ui-select"
                value={newMaxPanels}
                onChange={(event) => setNewMaxPanels(Number(event.target.value))}
              >
                {PANEL_CAPACITY_OPTIONS.map((count) => (
                  <option key={count} value={count}>
                    {count}
                  </option>
                ))}
              </select>
            </label>

            <label className="ui-input-label">
              <span>Template</span>
              <select
                className="ui-select"
                value={newTemplate}
                onChange={(event) => setNewTemplate(event.target.value as (typeof TEMPLATE_OPTIONS)[number])}
              >
                {TEMPLATE_OPTIONS.map((template) => (
                  <option key={template} value={template}>
                    {template}
                  </option>
                ))}
              </select>
            </label>

            <Button disabled={isBusy} type="submit">
              Create Active Pallet
            </Button>
          </form>
        </Card>
      </section>

      <section className="builder-grid">
        <Card title="Scan/Add serial">
          <form className="builder-form" onSubmit={handleAddSerial}>
            <TextInput
              label="Serial"
              ref={serialInputRef}
              value={serial}
              onChange={(event) => setSerial(event.target.value.toUpperCase())}
              placeholder="Scan barcode and press Enter"
              required
            />
            <Button disabled={isBusy || !current || remaining <= 0} type="submit">
              Add Serial
            </Button>
          </form>
        </Card>

        <Card title="Complete pallet">
          <p>Completion is enabled only when pallet is full.</p>
          <Button disabled={isBusy || !current || remaining !== 0} onClick={handleComplete}>
            Complete Current Pallet
          </Button>
        </Card>
      </section>

      <section className="card-grid">
        <Card title="Current items">
          {!current || current.items.length === 0 ? (
            <p>No serials added yet.</p>
          ) : (
            <table className="items-table">
              <thead>
                <tr>
                  <th>Slot</th>
                  <th>Serial</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {current.items
                  .slice()
                  .sort((a, b) => a.slot_index - b.slot_index)
                  .map((item) => (
                    <tr key={item.id}>
                      <td>{item.slot_index}</td>
                      <td className="mono">{item.serial}</td>
                      <td>
                        <Button variant="danger" disabled={isBusy} onClick={() => void handleRemoveItem(item.id)}>
                          Remove
                        </Button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          )}
        </Card>
      </section>
    </AppFrame>
  );
}
