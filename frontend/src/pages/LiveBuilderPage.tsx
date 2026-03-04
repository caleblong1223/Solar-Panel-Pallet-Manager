import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import AppFrame from "../components/layout/AppFrame";
import { useToast } from "../components/notifications/ToastProvider";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import TextInput from "../components/ui/TextInput";
import {
  addPalletItem,
  completePallet,
  createPallet,
  getPallet,
  listPallets,
  removePalletItem,
  type Pallet,
} from "../features/pallets";

const TEMPLATE_OPTIONS = ["200WT", "220WT", "220M6", "330WT", "450WT", "450BT"];

export default function LiveBuilderPage() {
  const { token } = useAuth();
  const { notify } = useToast();

  const [activePallets, setActivePallets] = useState<Pallet[]>([]);
  const [selectedPalletId, setSelectedPalletId] = useState<number | null>(null);
  const [current, setCurrent] = useState<Pallet | null>(null);
  const [serial, setSerial] = useState("");
  const [isBusy, setIsBusy] = useState(false);

  const [newMaxPanels, setNewMaxPanels] = useState("25");
  const [newTemplate, setNewTemplate] = useState(TEMPLATE_OPTIONS[0]);

  const serialInputRef = useRef<HTMLInputElement | null>(null);

  const remaining = useMemo(() => {
    if (!current) {
      return 0;
    }
    return current.max_panels - current.item_count;
  }, [current]);

  const refreshActivePallets = async () => {
    if (!token) {
      return;
    }
    const response = await listPallets(token, "active");
    setActivePallets(response.pallets);

    const selectedStillActive = response.pallets.find((pallet) => pallet.id === selectedPalletId);
    const nextSelected = selectedStillActive?.id ?? response.pallets[0]?.id ?? null;
    setSelectedPalletId(nextSelected);

    if (nextSelected) {
      const full = await getPallet(token, nextSelected);
      setCurrent(full);
    } else {
      setCurrent(null);
    }
  };

  useEffect(() => {
    void refreshActivePallets();
  }, [token]);

  useEffect(() => {
    if (!token || !selectedPalletId) {
      return;
    }

    void getPallet(token, selectedPalletId).then(setCurrent).catch(() => {
      notify("Failed to load pallet", "error");
    });
  }, [selectedPalletId, token, notify]);

  const handleCreatePallet = async (event: FormEvent) => {
    event.preventDefault();
    if (!token) {
      return;
    }

    const parsed = Number.parseInt(newMaxPanels, 10);
    if (!Number.isFinite(parsed) || parsed < 1) {
      notify("Max panels must be a positive number", "error");
      return;
    }

    setIsBusy(true);
    try {
      const created = await createPallet(token, { max_panels: parsed, template_type: newTemplate });
      notify(`Created pallet #${created.pallet_number}`, "success");
      await refreshActivePallets();
      setSelectedPalletId(created.id);
      setCurrent(created);
      setSerial("");
      serialInputRef.current?.focus();
    } catch {
      notify("Failed to create pallet", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleAddSerial = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || !current) {
      notify("Select or create an active pallet first", "warning");
      return;
    }

    setIsBusy(true);
    try {
      const updated = await addPalletItem(token, current.id, serial);
      setCurrent(updated);
      setSerial("");
      notify("Serial added", "success");
      serialInputRef.current?.focus();
    } catch {
      notify("Failed to add serial", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleRemoveItem = async (itemId: number) => {
    if (!token || !current) {
      return;
    }

    setIsBusy(true);
    try {
      const updated = await removePalletItem(token, current.id, itemId);
      setCurrent(updated);
      notify("Serial removed", "success");
    } catch {
      notify("Failed to remove serial", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleComplete = async () => {
    if (!token || !current) {
      return;
    }

    setIsBusy(true);
    try {
      const updated = await completePallet(token, current.id);
      notify(`Pallet #${updated.pallet_number} completed`, "success");
      await refreshActivePallets();
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
          <label className="ui-input-label">
            <span>Choose active pallet</span>
            <select
              className="ui-select"
              value={selectedPalletId ?? ""}
              onChange={(event) => {
                const value = event.target.value;
                setSelectedPalletId(value ? Number(value) : null);
              }}
            >
              <option value="">None</option>
              {activePallets.map((pallet) => (
                <option key={pallet.id} value={pallet.id}>
                  #{pallet.pallet_number} ({pallet.item_count}/{pallet.max_panels})
                </option>
              ))}
            </select>
          </label>

          {current ? (
            <div className="builder-meta">
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
            </div>
          ) : (
            <p>No active pallet selected.</p>
          )}
        </Card>

        <Card title="Create pallet">
          <form className="builder-form" onSubmit={handleCreatePallet}>
            <TextInput
              label="Max panels"
              inputMode="numeric"
              value={newMaxPanels}
              onChange={(event) => setNewMaxPanels(event.target.value)}
              required
            />

            <label className="ui-input-label">
              <span>Template</span>
              <select className="ui-select" value={newTemplate} onChange={(event) => setNewTemplate(event.target.value)}>
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
