import { FormEvent, useEffect, useRef, useState } from "react";
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
  createExport,
  getPallet,
  listPallets,
  removePalletItem,
  type Pallet,
} from "../features/pallets";
import { getExportDownloadUrl } from "../features/exports";
import { listCustomers, type Customer } from "../features/customers";

const DEFAULT_MAX_PANELS = 25;
const TEMPLATE_OPTIONS = ["200WT", "220WT", "220M6", "330WT", "450WT", "450BT"];
const ACCESS_TOKEN_KEY = "pm2_access_token";
const PALLET_SIZES = [25, 26, 30, 35];

function getEffectiveToken(contextToken: string | null): string | null {
  return contextToken ?? localStorage.getItem(ACCESS_TOKEN_KEY);
}

/** Format date as MDYYYY (single-digit month/day, like 1.1) for B3 preview */
function formatB3Date(date: Date): string {
  const m = date.getMonth() + 1;
  const d = date.getDate();
  const y = date.getFullYear();
  return `${m}${d}${y}`;
}

export default function LiveBuilderPage() {
  const { token: contextToken } = useAuth();
  const token = getEffectiveToken(contextToken);
  const { notify } = useToast();

  const [current, setCurrent] = useState<Pallet | null>(null);
  const [serial, setSerial] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [newPalletTemplate, setNewPalletTemplate] = useState(TEMPLATE_OPTIONS[0]);
  const [newPalletSize, setNewPalletSize] = useState<number>(DEFAULT_MAX_PANELS);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState<number | "none">("none");
  const serialInputRef = useRef<HTMLInputElement | null>(null);

  const remaining = current ? current.max_panels - current.item_count : 0;

  const loadFirstActivePallet = async () => {
    const t = getEffectiveToken(contextToken);
    if (!t) return;
    const { pallets } = await listPallets(t, "active");
    if (pallets.length > 0) {
      const full = await getPallet(t, pallets[0].id);
      setCurrent(full);
    } else {
      setCurrent(null);
    }
  };

  useEffect(() => {
    void loadFirstActivePallet();
    const t = getEffectiveToken(contextToken);
    if (t) {
      void listCustomers(t, { isActive: true })
        .then((response) => {
          setCustomers(response.customers);
        })
        .catch(() => {
          // Customers are optional for pallet creation; swallow errors here and surface via explicit actions if needed.
        });
    }
  }, [contextToken]);

  const handleStartNewPallet = async () => {
    const t = getEffectiveToken(contextToken);
    if (!t) {
      notify("No session. Sign in or check connection.", "warning");
      return;
    }
    setIsBusy(true);
    try {
      const created = await createPallet(t, {
        max_panels: newPalletSize,
        template_type: newPalletTemplate,
        customer_id: selectedCustomerId === "none" ? undefined : selectedCustomerId,
      });
      setCurrent(created);
      setSerial("");
      notify(`Pallet #${created.pallet_number} started`, "success");
      serialInputRef.current?.focus();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start pallet";
      notify(message, "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleAddSerial = async (event: FormEvent) => {
    event.preventDefault();
    const t = getEffectiveToken(contextToken);
    if (!t || !current) {
      notify("Start a pallet first", "warning");
      return;
    }
    const s = serial.trim();
    if (!s) return;

    if (remaining <= 0) {
      notify("Pallet is full. Complete it first.", "warning");
      return;
    }

    setIsBusy(true);
    try {
      const updated = await addPalletItem(t, current.id, s);
      setCurrent(updated);
      setSerial("");
      notify("Added", "success");
      serialInputRef.current?.focus();
    } catch {
      notify("Failed to add serial", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleRemoveItem = async (itemId: number) => {
    if (!token || !current) return;
    setIsBusy(true);
    try {
      const updated = await removePalletItem(token, current.id, itemId);
      setCurrent(updated);
      notify("Removed", "success");
    } catch {
      notify("Failed to remove", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const handleComplete = async () => {
    if (!token || !current) return;
    if (remaining !== 0) {
      notify("Pallet must be full to complete", "warning");
      return;
    }
    const palletId = current.id;
    const palletNumber = current.pallet_number;
    const templateType = current.template_type ?? "200WT";
    setIsBusy(true);
    try {
      await completePallet(token, current.id);
      const created = await createExport(token, { pallet_id: palletId, template_type: templateType });
      const { download_url } = await getExportDownloadUrl(token, created.id, "xlsx");
      window.open(download_url, "_blank", "noopener,noreferrer");
      notify(`Pallet #${palletNumber} completed · export ready`, "success");
      setCurrent(null);
      await loadFirstActivePallet();
      serialInputRef.current?.focus();
    } catch {
      notify("Failed to complete or export pallet", "error");
    } finally {
      setIsBusy(false);
    }
  };

  return (
    <AppFrame title="Builder">
      <section className="builder-grid">
        <Card title={current ? `Pallet #${current.pallet_number}` : "No active pallet"}>
          {current ? (
            <>
              <p className="builder-meta">
                <strong>Panel type (for export):</strong> {current.template_type ?? "200WT"}
              </p>
              <p className="builder-meta">
                <strong>Cell B3 on export:</strong>{" "}
                {current.template_type ?? "200WT"}
                {formatB3Date(new Date())}-{current.pallet_number}
              </p>
              <p className="builder-meta">
                <strong>{current.item_count}</strong> / {current.max_panels} panels
                {remaining > 0 && ` · ${remaining} remaining`}
              </p>
              <form className="builder-form" onSubmit={handleAddSerial} style={{ marginTop: "12px" }}>
                <TextInput
                  label="Scan barcode"
                  ref={serialInputRef}
                  value={serial}
                  onChange={(e) => setSerial(e.target.value.toUpperCase())}
                  placeholder="Scan then press Enter"
                  autoFocus
                />
                <Button type="submit" disabled={isBusy || remaining <= 0}>
                  Add
                </Button>
              </form>
              <div style={{ marginTop: "12px" }}>
                <Button
                  variant="primary"
                  disabled={isBusy || remaining !== 0}
                  onClick={handleComplete}
                >
                  Complete pallet
                </Button>
              </div>
            </>
          ) : (
            <>
              <p style={{ marginBottom: "12px", color: "var(--color-text-secondary)" }}>
                Start a new pallet to begin scanning. Panel type and pallet size are used for export and cell B3, matching the 1.1 workflow.
              </p>
              <label className="ui-input-label" style={{ marginBottom: "8px" }}>
                <span>Customer (optional)</span>
                <select
                  className="ui-select"
                  value={selectedCustomerId === "none" ? "" : String(selectedCustomerId)}
                  onChange={(event) => {
                    const value = event.target.value;
                    if (!value) {
                      setSelectedCustomerId("none");
                    } else {
                      setSelectedCustomerId(Number(value));
                    }
                  }}
                >
                  <option value="">No customer selected</option>
                  {customers.map((customer) => (
                    <option key={customer.id} value={customer.id}>
                      {customer.display_name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="ui-input-label" style={{ marginBottom: "8px" }}>
                <span>Panel type</span>
                <select
                  className="ui-select"
                  value={newPalletTemplate}
                  onChange={(e) => setNewPalletTemplate(e.target.value)}
                >
                  {TEMPLATE_OPTIONS.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </label>
              <label className="ui-input-label" style={{ marginBottom: "8px" }}>
                <span>Pallet size</span>
                <select
                  className="ui-select"
                  value={newPalletSize}
                  onChange={(e) => setNewPalletSize(Number(e.target.value))}
                >
                  {PALLET_SIZES.map((size) => (
                    <option key={size} value={size}>
                      {size} panels
                    </option>
                  ))}
                </select>
              </label>
              <Button type="button" disabled={isBusy} onClick={() => void handleStartNewPallet()}>
                Start new pallet
              </Button>
            </>
          )}
        </Card>

        {current && current.items.length > 0 ? (
          <Card title="Items on pallet">
            <ul className="flat-list">
              {current.items
                .slice()
                .sort((a, b) => a.slot_index - b.slot_index)
                .map((item) => (
                  <li key={item.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <span className="mono">{item.serial}</span>
                    <Button variant="danger" disabled={isBusy} onClick={() => void handleRemoveItem(item.id)}>
                      Remove
                    </Button>
                  </li>
                ))}
            </ul>
          </Card>
        ) : null}
      </section>
    </AppFrame>
  );
}
